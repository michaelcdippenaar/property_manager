"""
VaultQueryService — hybrid graph + vector query engine for The Volt.

Graph traversal is done via Django ORM (EntityRelationship FK graph).
Vector search is done via ChromaDB with optional entity_id scoping.

Hybrid pattern (graph-first, then vector):
  1. traverse() → list of entity IDs from graph
  2. query_vault(..., entity_ids=...) → semantic search scoped to those IDs

Example: "addresses of all directors of Acme Ltd"
  entities = service.traverse(acme_entity_id, relationship_types=["director_of"])
  results  = service.vector_search("address", entity_ids=[e.id for e in entities])
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db.models import Q

from apps.the_volt.entities.models import VaultEntity, EntityRelationship
from apps.the_volt.owners.models import VaultOwner

logger = logging.getLogger(__name__)


class VaultQueryService:
    def __init__(self, vault_owner: VaultOwner):
        self.vault = vault_owner

    # -----------------------------------------------------------------------
    # Graph traversal
    # -----------------------------------------------------------------------

    def traverse(
        self,
        from_entity_id: int,
        relationship_types: Optional[list[str]] = None,
        hops: int = 1,
        direction: str = "outgoing",
    ) -> list[VaultEntity]:
        """ORM graph traversal — returns reachable entity nodes.

        Args:
            from_entity_id:     Starting node ID.
            relationship_types: Filter edges by type. None = all types.
            hops:               How many hops to traverse (1 = direct neighbours).
            direction:          "outgoing" (from→to), "incoming" (to←from), "both".

        Returns:
            Flat list of unique VaultEntity objects reachable from the start node.
        """
        if hops < 1:
            return []

        visited_ids: set[int] = set()
        current_frontier: set[int] = {from_entity_id}
        result: list[VaultEntity] = []

        for _ in range(hops):
            if not current_frontier:
                break

            qs = EntityRelationship.objects.filter(vault=self.vault)
            if relationship_types:
                qs = qs.filter(relationship_type__in=relationship_types)

            if direction == "outgoing":
                qs = qs.filter(from_entity_id__in=current_frontier)
                neighbour_ids = set(qs.values_list("to_entity_id", flat=True))
            elif direction == "incoming":
                qs = qs.filter(to_entity_id__in=current_frontier)
                neighbour_ids = set(qs.values_list("from_entity_id", flat=True))
            else:  # both
                out_qs = qs.filter(from_entity_id__in=current_frontier)
                in_qs = qs.filter(to_entity_id__in=current_frontier)
                neighbour_ids = (
                    set(out_qs.values_list("to_entity_id", flat=True))
                    | set(in_qs.values_list("from_entity_id", flat=True))
                )

            new_ids = neighbour_ids - visited_ids - {from_entity_id}
            if not new_ids:
                break

            entities = VaultEntity.objects.filter(
                vault=self.vault,
                pk__in=new_ids,
                is_active=True,
            )
            result.extend(entities)
            visited_ids.update(new_ids)
            current_frontier = new_ids

        return result

    # -----------------------------------------------------------------------
    # Vector search
    # -----------------------------------------------------------------------

    def vector_search(
        self,
        query: str,
        entity_ids: Optional[list[int]] = None,
        collection: str = "documents",
        n_results: int = 5,
    ) -> list[dict]:
        """ChromaDB semantic search, optionally scoped to a set of entity IDs.

        Pass entity_ids from a graph traversal to restrict search to a subgraph.
        """
        from core.volt_rag import query_vault
        return query_vault(
            owner_id=self.vault.id,
            query=query,
            entity_ids=entity_ids,
            collection=collection,
            n_results=n_results,
        )

    # -----------------------------------------------------------------------
    # Hybrid: graph then vector
    # -----------------------------------------------------------------------

    def graph_then_vector(
        self,
        from_entity_id: int,
        relationship_types: Optional[list[str]] = None,
        query: str = "",
        hops: int = 1,
        direction: str = "outgoing",
        collection: str = "documents",
        n_results: int = 5,
    ) -> dict:
        """Chain: graph traversal → scoped vector search.

        Returns:
            {
                "graph_entities": [...],     # entities found by traversal
                "vector_results": [...],     # semantic search results scoped to those entities
            }
        Example:
            service.graph_then_vector(
                acme_id,
                relationship_types=["director_of"],
                query="residential address",
            )
            → finds all directors of Acme, then searches their docs for "residential address"
        """
        entities = self.traverse(
            from_entity_id=from_entity_id,
            relationship_types=relationship_types,
            hops=hops,
            direction=direction,
        )
        entity_ids = [e.id for e in entities]

        vector_results = []
        if entity_ids and query:
            vector_results = self.vector_search(
                query=query,
                entity_ids=entity_ids,
                collection=collection,
                n_results=n_results,
            )
        elif query and not entity_ids:
            # No graph results — fall back to vault-wide vector search
            logger.info(
                "VaultQueryService: graph traversal returned 0 entities for entity_id=%s; "
                "falling back to vault-wide vector search",
                from_entity_id,
            )
            vector_results = self.vector_search(
                query=query,
                collection=collection,
                n_results=n_results,
            )

        return {
            "graph_entities": [
                {"id": e.id, "name": e.name, "entity_type": e.entity_type}
                for e in entities
            ],
            "vector_results": vector_results,
        }
