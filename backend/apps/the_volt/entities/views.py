import logging

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.the_volt.owners.models import VaultOwner
from .models import VaultEntity, EntityRelationship, RelationshipTypeCatalogue
from .query_service import VaultQueryService
from .serializers import VaultEntitySerializer, EntityRelationshipSerializer, RelationshipTypeCatalogueSerializer

logger = logging.getLogger(__name__)


class VaultEntityViewSet(viewsets.ModelViewSet):
    """CRUD for vault entities.

    All queries are scoped to request.user's vault.
    Destroy is a soft-delete (is_active=False) + ChromaDB chunk removal.
    Create/update re-indexes entity data in ChromaDB.
    """

    serializer_class = VaultEntitySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["entity_type", "is_active"]

    def get_queryset(self):
        return VaultEntity.objects.filter(
            vault__user=self.request.user,
        ).select_related("vault")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        owner = VaultOwner.get_or_create_for_user(self.request.user)
        instance = serializer.save(vault=owner)
        self._index_entity(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._index_entity(instance)

    def perform_destroy(self, instance):
        # Soft delete + remove from ChromaDB
        try:
            from core.volt_rag import delete_entity_chunks
            delete_entity_chunks(owner_id=instance.vault_id, entity_id=instance.pk)
        except Exception:
            logger.exception("Volt: failed to delete ChromaDB chunks for entity_id=%s", instance.pk)
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    def _index_entity(self, instance: VaultEntity):
        """Index entity data into ChromaDB (non-blocking, logs failures)."""
        try:
            from core.volt_rag import ingest_entity_data
            chroma_id = ingest_entity_data(
                owner_id=instance.vault_id,
                entity_id=instance.pk,
                entity_type=instance.entity_type,
                entity_name=instance.name,
                data=instance.data,
            )
            if chroma_id:
                VaultEntity.objects.filter(pk=instance.pk).update(chroma_id=chroma_id)
        except Exception:
            logger.exception("Volt: failed to index entity_id=%s in ChromaDB", instance.pk)

    # -----------------------------------------------------------------------
    # Extra actions
    # -----------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="schemas")
    def schemas(self, request):
        """Return DATA_SCHEMAS dict for all entity types (static, from code)."""
        return Response(VaultEntity.DATA_SCHEMAS)

    @action(detail=True, methods=["get", "post"], url_path="relationships")
    def relationships(self, request, pk=None):
        """List (GET) or create (POST) relationships for this entity."""
        entity = self.get_object()
        if request.method == "GET":
            qs = EntityRelationship.objects.filter(
                Q(from_entity=entity) | Q(to_entity=entity)
            ).select_related("from_entity", "to_entity")

            results = []
            for rel in qs:
                data = EntityRelationshipSerializer(rel).data
                data["direction"] = "outgoing" if rel.from_entity_id == entity.pk else "incoming"
                results.append(data)
            return Response(results)

        # POST — create edge from this entity
        data = request.data.copy()
        data["from_entity"] = entity.pk
        serializer = EntityRelationshipSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        owner = VaultOwner.get_or_create_for_user(request.user)
        serializer.save(vault=owner)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="query")
    def query(self, request):
        """Hybrid graph+vector query.

        Body:
        {
            "from_entity_id": 1,
            "relationship_types": ["director_of"],   // optional
            "query": "residential address",
            "hops": 1,                               // optional, default 1
            "direction": "outgoing",                 // optional
            "collection": "documents"                // optional: documents | entities
        }
        """
        owner = VaultOwner.get_or_create_for_user(request.user)
        service = VaultQueryService(owner)

        from_entity_id = request.data.get("from_entity_id")
        if not from_entity_id:
            return Response({"detail": "from_entity_id is required."}, status=400)

        results = service.graph_then_vector(
            from_entity_id=int(from_entity_id),
            relationship_types=request.data.get("relationship_types"),
            query=request.data.get("query", ""),
            hops=int(request.data.get("hops", 1)),
            direction=request.data.get("direction", "outgoing"),
            collection=request.data.get("collection", "documents"),
            n_results=int(request.data.get("n_results", 5)),
        )
        return Response(results)


class EntityRelationshipViewSet(viewsets.ModelViewSet):
    """List, create, and destroy entity relationships (graph edges)."""

    serializer_class = EntityRelationshipSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return EntityRelationship.objects.filter(
            vault__user=self.request.user
        ).select_related("from_entity", "to_entity", "vault", "relationship_type")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        owner = VaultOwner.get_or_create_for_user(self.request.user)
        serializer.save(vault=owner)


class RelationshipTypeCatalogueViewSet(viewsets.ModelViewSet):
    """CRUD for relationship types.

    System types (is_system=True) cannot be deleted — returns 403.
    All authenticated users can read; create/update/delete requires auth.
    AI agents use POST to create new types when they encounter an unlisted relationship.
    """
    serializer_class = RelationshipTypeCatalogueSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = RelationshipTypeCatalogue.objects.all()
        if self.request.query_params.get("active_only", "true").lower() != "false":
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("System relationship types cannot be deleted.")
        instance.delete()
