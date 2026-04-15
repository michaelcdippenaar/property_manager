from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import EntitySchema, ZA_DEFAULT_SCHEMAS
from .serializers import EntitySchemaSerializer


class EntitySchemaViewSet(viewsets.ModelViewSet):
    """CRUD for entity schemas.

    - GET  /schemas/                          — list all schemas
    - GET  /schemas/?entity_type=personal&country_code=ZA  — filter
    - GET  /schemas/{id}/                     — retrieve one
    - POST /schemas/                          — create (admin only)
    - PUT/PATCH /schemas/{id}/               — update (admin only)
    - DELETE /schemas/{id}/                  — delete (admin only)
    - GET  /schemas/active/                  — return active schemas per entity_type for a country
    """

    serializer_class = EntitySchemaSerializer
    filterset_fields = ["entity_type", "country_code", "is_active"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return EntitySchema.objects.all()

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """Return the active schema for each entity type in a given country.

        Query param: ?country_code=ZA (default ZA)
        Returns: {entity_type: EntitySchema}
        """
        country_code = request.query_params.get("country_code", "ZA").upper()
        schemas = EntitySchema.objects.filter(country_code=country_code, is_active=True)
        result = {}
        for schema in schemas:
            result[schema.entity_type] = EntitySchemaSerializer(schema).data
        return Response(result)

    @action(detail=False, methods=["post"], url_path="seed-defaults", permission_classes=[IsAdminUser])
    def seed_defaults(self, request):
        """Seed the default ZA schemas from ZA_DEFAULT_SCHEMAS.

        Idempotent — only creates schemas that don't yet have an active version.
        """
        country_code = request.data.get("country_code", "ZA")
        created = []
        for entity_type, schema_def in ZA_DEFAULT_SCHEMAS.items():
            exists = EntitySchema.objects.filter(
                entity_type=entity_type,
                country_code=country_code,
                is_active=True,
            ).exists()
            if not exists:
                EntitySchema.objects.create(
                    entity_type=entity_type,
                    country_code=country_code,
                    version=1,
                    label=schema_def["label"],
                    description=schema_def.get("description", ""),
                    fields=schema_def["fields"],
                    is_active=True,
                )
                created.append(entity_type)
        return Response({"created": created, "country_code": country_code})
