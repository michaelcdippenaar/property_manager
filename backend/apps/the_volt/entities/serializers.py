from rest_framework import serializers

from .models import VaultEntity, EntityRelationship, RelationshipTypeCatalogue


class VaultEntitySerializer(serializers.ModelSerializer):
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)
    vault_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = VaultEntity
        fields = [
            "id",
            "vault_id",
            "entity_type",
            "entity_type_display",
            "name",
            "data",
            "chroma_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "vault_id", "chroma_id", "created_at", "updated_at"]

    def validate(self, attrs):
        # Soft-validate data keys against schema (warn unknown keys but don't block)
        entity_type = attrs.get("entity_type") or (self.instance.entity_type if self.instance else None)
        data = attrs.get("data", {})
        if entity_type and data:
            known_keys = set(VaultEntity.DATA_SCHEMAS.get(entity_type, {}).keys())
            unknown = set(data.keys()) - known_keys
            if unknown:
                # Log warning but don't raise — schema may have been extended
                import logging
                logging.getLogger(__name__).warning(
                    "VaultEntity data contains keys not in DATA_SCHEMAS[%s]: %s", entity_type, unknown
                )
        return attrs


class EntityRelationshipSerializer(serializers.ModelSerializer):
    from_entity_name = serializers.CharField(source="from_entity.name", read_only=True)
    to_entity_name = serializers.CharField(source="to_entity.name", read_only=True)
    from_entity_type = serializers.CharField(source="from_entity.entity_type", read_only=True)
    to_entity_type = serializers.CharField(source="to_entity.entity_type", read_only=True)
    relationship_type = serializers.PrimaryKeyRelatedField(
        queryset=RelationshipTypeCatalogue.objects.filter(is_active=True)
    )
    relationship_type_code = serializers.CharField(source="relationship_type.code", read_only=True)
    relationship_type_label = serializers.CharField(source="relationship_type.label", read_only=True)
    relationship_type_inverse = serializers.CharField(source="relationship_type.inverse_label", read_only=True)

    class Meta:
        model = EntityRelationship
        fields = [
            "id",
            "vault_id",
            "from_entity",
            "from_entity_name",
            "from_entity_type",
            "to_entity",
            "to_entity_name",
            "to_entity_type",
            "relationship_type",
            "relationship_type_code",
            "relationship_type_label",
            "relationship_type_inverse",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "vault_id", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            from_entity = attrs.get("from_entity") or (self.instance.from_entity if self.instance else None)
            to_entity = attrs.get("to_entity") or (self.instance.to_entity if self.instance else None)
            if from_entity and to_entity:
                user_vault_id = getattr(getattr(request.user, "vault", None), "id", None)
                if from_entity.vault_id != to_entity.vault_id:
                    raise serializers.ValidationError("Both entities must belong to the same vault.")
                if user_vault_id and from_entity.vault_id != user_vault_id:
                    raise serializers.ValidationError("Entities do not belong to your vault.")

        rel_type = attrs.get("relationship_type")
        if rel_type:
            from_entity = attrs.get("from_entity") or (self.instance.from_entity if self.instance else None)
            to_entity = attrs.get("to_entity") or (self.instance.to_entity if self.instance else None)
            from_type = from_entity.entity_type if from_entity else None
            to_type = to_entity.entity_type if to_entity else None
            if rel_type.valid_from_entity_types and from_type not in rel_type.valid_from_entity_types:
                raise serializers.ValidationError(
                    f"'{rel_type.code}' is not valid from entity type '{from_type}'. "
                    f"Valid from: {rel_type.valid_from_entity_types}"
                )
            if rel_type.valid_to_entity_types and to_type not in rel_type.valid_to_entity_types:
                raise serializers.ValidationError(
                    f"'{rel_type.code}' is not valid to entity type '{to_type}'. "
                    f"Valid to: {rel_type.valid_to_entity_types}"
                )

        return attrs


class RelationshipTypeCatalogueSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipTypeCatalogue
        fields = [
            "id", "code", "label", "inverse_label", "description",
            "valid_from_entity_types", "valid_to_entity_types",
            "metadata_schema", "regulatory_reference",
            "is_system", "is_active", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]
