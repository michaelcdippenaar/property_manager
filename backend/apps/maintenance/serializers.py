from rest_framework import serializers
from .models import MaintenanceRequest, Supplier, SupplierTrade


class SupplierTradeSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_trade_display", read_only=True)

    class Meta:
        model = SupplierTrade
        fields = ["id", "trade", "label"]
        read_only_fields = ["id"]


class SupplierListSerializer(serializers.ModelSerializer):
    trades = SupplierTradeSerializer(many=True, read_only=True)
    active_jobs_count = serializers.IntegerField(read_only=True, default=0)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id", "name", "company_name", "display_name", "phone", "email",
            "city", "province", "is_active", "rating", "trades",
            "active_jobs_count", "created_at",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    trades = SupplierTradeSerializer(many=True, read_only=True)
    trade_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=Supplier.Trade.choices),
        write_only=True, required=False,
    )
    active_jobs_count = serializers.IntegerField(read_only=True, default=0)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        trade_codes = validated_data.pop("trade_codes", [])
        supplier = super().create(validated_data)
        for code in trade_codes:
            SupplierTrade.objects.create(supplier=supplier, trade=code)
        return supplier

    def update(self, instance, validated_data):
        trade_codes = validated_data.pop("trade_codes", None)
        supplier = super().update(instance, validated_data)
        if trade_codes is not None:
            supplier.trades.all().delete()
            for code in trade_codes:
                SupplierTrade.objects.create(supplier=supplier, trade=code)
        return supplier


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.display_name", read_only=True, default=None,
    )

    class Meta:
        model = MaintenanceRequest
        fields = "__all__"
        read_only_fields = ["tenant", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user
        return super().create(validated_data)
