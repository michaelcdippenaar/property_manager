"""Unit tests for properties models — no DB required."""
import pytest
from unittest.mock import Mock, PropertyMock

pytestmark = pytest.mark.unit


class TestPropertyModel:

    @pytest.mark.green
    def test_str_returns_name(self):
        from apps.properties.models import Property
        prop = Property(name="Sunset Apartments")
        assert str(prop) == "Sunset Apartments"

    @pytest.mark.green
    def test_property_type_choices_include_expected_values(self):
        from apps.properties.models import Property
        types = [t[0] for t in Property.PropertyType.choices]
        assert "apartment" in types
        assert "house" in types
        assert "townhouse" in types
        assert "commercial" in types

    @pytest.mark.green
    def test_property_type_values_match_labels(self):
        from apps.properties.models import Property
        choices_dict = dict(Property.PropertyType.choices)
        assert choices_dict["apartment"] == "Apartment"
        assert choices_dict["house"] == "House"


class TestUnitModel:

    @pytest.mark.green
    def test_str_includes_property_name_and_unit_number(self):
        from apps.properties.models import Unit, Property
        prop = Property(name="Greenview Estate")
        unit = Unit(property=prop, unit_number="3B")
        assert "Greenview Estate" in str(unit)
        assert "3B" in str(unit)

    @pytest.mark.green
    def test_default_status_is_available(self):
        from apps.properties.models import Unit
        unit = Unit()
        assert unit.status == Unit.Status.AVAILABLE

    @pytest.mark.green
    def test_status_choices_include_expected_values(self):
        from apps.properties.models import Unit
        statuses = [s[0] for s in Unit.Status.choices]
        assert "available" in statuses
        assert "occupied" in statuses
        assert "maintenance" in statuses

    @pytest.mark.green
    def test_default_bedrooms_is_1(self):
        from apps.properties.models import Unit
        unit = Unit()
        assert unit.bedrooms == 1

    @pytest.mark.green
    def test_default_bathrooms_is_1(self):
        from apps.properties.models import Unit
        unit = Unit()
        assert unit.bathrooms == 1

    @pytest.mark.green
    def test_rent_amount_has_no_positive_validator(self):
        """
        Documents vuln #21: rent_amount is DecimalField with no min_value validator.
        A negative value would pass model-level validation.
        Marked red — verify that a min_value=0 validator has NOT been added yet.
        """
        from apps.properties.models import Unit
        field = Unit._meta.get_field("rent_amount")
        # If validators are empty, the vuln is still open
        positive_validators = [v for v in field.validators if hasattr(v, "limit_value") and v.limit_value == 0]
        # Document: no positive constraint is currently enforced
        assert len(positive_validators) == 0  # flip to != 0 when fixed

    @pytest.mark.green
    def test_unit_number_and_property_no_unique_together(self):
        """
        Documents vuln #22: no unique_together constraint on (property, unit_number).
        Marked red — verify that this constraint has NOT been added yet.
        """
        from apps.properties.models import Unit
        unique_together = Unit._meta.unique_together
        has_constraint = any(
            set(combo) == {"property", "unit_number"}
            for combo in unique_together
        )
        # Document: constraint is missing — flip assertion when fixed
        assert has_constraint is False


class TestUnitInfoModel:

    @pytest.mark.green
    def test_str_includes_label_and_value_preview(self):
        from apps.properties.models import UnitInfo
        info = UnitInfo(label="WiFi", value="SSID: TestNet, Password: secret123")
        result = str(info)
        assert "WiFi" in result
        assert "SSID: TestNet" in result

    @pytest.mark.green
    def test_str_truncates_value_at_50_chars(self):
        from apps.properties.models import UnitInfo
        long_value = "x" * 100
        info = UnitInfo(label="Test", value=long_value)
        result = str(info)
        # The model does [:50] on value in __str__
        assert len(result) < len("Test: ") + 100

    @pytest.mark.green
    def test_icon_type_choices_include_wifi_and_alarm(self):
        from apps.properties.models import UnitInfo
        types = [t[0] for t in UnitInfo.IconType.choices]
        assert "wifi" in types
        assert "alarm" in types
        assert "parking" in types

    @pytest.mark.green
    def test_default_icon_type_is_other(self):
        from apps.properties.models import UnitInfo
        info = UnitInfo()
        assert info.icon_type == UnitInfo.IconType.OTHER


class TestPropertyAgentConfigModel:

    @pytest.mark.green
    def test_str_includes_property_name(self):
        from apps.properties.models import PropertyAgentConfig, Property
        prop = Property(name="Harbour View")
        config = PropertyAgentConfig(property=prop)
        assert "Harbour View" in str(config)

    @pytest.mark.green
    def test_is_active_defaults_to_true(self):
        from apps.properties.models import PropertyAgentConfig
        config = PropertyAgentConfig()
        assert config.is_active is True


class TestPropertyGroupModel:

    @pytest.mark.green
    def test_str_returns_name(self):
        from apps.properties.models import PropertyGroup
        group = PropertyGroup(name="Northern Suburbs Portfolio")
        assert str(group) == "Northern Suburbs Portfolio"


class TestLandlordModel:

    @pytest.mark.green
    def test_str_returns_name(self):
        from apps.properties.models import Landlord
        landlord = Landlord(name="Acme Properties Ltd")
        assert str(landlord) == "Acme Properties Ltd"

    @pytest.mark.green
    def test_landlord_type_choices_include_individual_company_trust(self):
        from apps.properties.models import Landlord
        types = [t[0] for t in Landlord.LandlordType.choices]
        assert "individual" in types
        assert "company" in types
        assert "trust" in types


class TestBankAccountModel:

    @pytest.mark.green
    def test_str_shows_last_4_digits_of_account_number(self):
        from apps.properties.models import BankAccount, Landlord
        landlord = Landlord(name="Test Landlord")
        account = BankAccount(bank_name="FNB", account_number="123456789012", landlord=landlord)
        result = str(account)
        assert "9012" in result

    @pytest.mark.green
    def test_str_falls_back_to_bank_name_when_no_account_number(self):
        from apps.properties.models import BankAccount, Landlord
        landlord = Landlord(name="Test Landlord")
        account = BankAccount(bank_name="ABSA", account_number="", landlord=landlord)
        assert str(account) == "ABSA"
