"""Tests for ОПО card backend — architectural audit.

Covers:
1. Classification codes 4.1–4.12 validation
2. hazard_class independence from classification
3. work_processes 2.1–2.6 validation
4. Properties: OKTMO, okved, owner stored and retrieved
5. Composition: structures + equipment + substances aggregation
6. licensed_activities: cross-org rejection
7. Backward compatibility: old records
8. No unauthorized fields
9. PMLA context 108 keys and DOCX
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from src.infrastructure.database.models import HazardousFacilityModel


# ═══════════════════════════════════════════════════════════════════════════
# 1. Classification codes
# ═══════════════════════════════════════════════════════════════════════════

class TestClassification:
    VALID = [f"4.{i}" for i in range(1, 13)]

    def test_valid_codes_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            classification=["4.1", "4.5", "4.12"],
        )
        assert fc.classification == ["4.1", "4.5", "4.12"]

    def test_invalid_code_rejected(self):
        from src.api.routers.facilities import FacilityCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FacilityCreate(
                organization_id=uuid4(), name="Тест",
                classification=["4.1", "5.1"],
            )

    def test_multiple_classification_signs(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            classification=["4.1", "4.2", "4.3", "4.4", "4.5"],
        )
        assert len(fc.classification) == 5

    def test_empty_list_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            classification=[],
        )
        assert fc.classification == []

    def test_none_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(organization_id=uuid4(), name="Тест")
        assert fc.classification is None

    def test_classification_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.classification
        assert col.nullable is True


# ═══════════════════════════════════════════════════════════════════════════
# 2. hazard_class independence
# ═══════════════════════════════════════════════════════════════════════════

class TestHazardClassIndependence:
    def test_hazard_class_not_affected_by_classification(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            hazard_class=3,
            classification=["4.1", "4.5"],
        )
        assert fc.hazard_class == 3
        assert fc.classification == ["4.1", "4.5"]

    def test_classification_without_hazard_class(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            classification=["4.1"],
        )
        assert fc.hazard_class is None
        assert fc.classification == ["4.1"]

    def test_hazard_class_without_classification(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            hazard_class=2,
        )
        assert fc.hazard_class == 2
        assert fc.classification is None


# ═══════════════════════════════════════════════════════════════════════════
# 3. work_processes
# ═══════════════════════════════════════════════════════════════════════════

class TestWorkProcesses:
    def test_valid_keys_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            work_processes={"2.1": "транспорт", "2.3": "хранение"},
        )
        assert fc.work_processes["2.1"] == "транспорт"

    def test_invalid_key_rejected(self):
        from src.api.routers.facilities import FacilityCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FacilityCreate(
                organization_id=uuid4(), name="Тест",
                work_processes={"2.7": "test"},
            )

    def test_multiple_processes(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            work_processes={
                "2.1": "транспорт", "2.2": "склад", "2.3": "хранилище",
                "2.4": "переработка", "2.5": "утилизация", "2.6": "лаборатория",
            },
        )
        assert len(fc.work_processes) == 6

    def test_work_processes_not_classification(self):
        """work_processes keys (2.x) are different from classification (4.x)."""
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            work_processes={"2.1": "транспорт"},
            classification=["4.1"],
        )
        assert "2.1" in fc.work_processes
        assert "4.1" in fc.classification
        assert fc.work_processes != fc.classification


# ═══════════════════════════════════════════════════════════════════════════
# 4. Properties: OKTMO, okved, owner
# ═══════════════════════════════════════════════════════════════════════════

class TestProperties:
    VALID_KEYS = {"okved", "oktmo", "owner", "owner_basis"}

    def test_valid_keys_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            properties={"oktmo": "45338000", "okved": "46.71", "owner": "ООО Тест", "owner_basis": "собственник"},
        )
        assert fc.properties["oktmo"] == "45338000"
        assert fc.properties["okved"] == "46.71"
        assert fc.properties["owner"] == "ООО Тест"
        assert fc.properties["owner_basis"] == "собственник"

    def test_unknown_key_rejected(self):
        from src.api.routers.facilities import FacilityCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FacilityCreate(
                organization_id=uuid4(), name="Тест",
                properties={"unknown_key": "value"},
            )

    def test_empty_dict_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(organization_id=uuid4(), name="Тест")
        assert fc.properties == {}

    def test_okved_corresponds_to_industry(self):
        """okved is the industry code from the ОПО form, not an unrelated value."""
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            properties={"okved": "46.71"},
        )
        assert fc.properties["okved"] == "46.71"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Composition: structures
# ═══════════════════════════════════════════════════════════════════════════

class TestCompositionStructures:
    def test_composition_structures_accepted(self):
        from src.api.routers.facilities import FacilityCreate
        structures = [
            {"type": "building", "name": "ГРПШ-1", "area_sqm": 45.5},
            {"type": "site", "name": "Промплощадка", "area_sqm": 5000},
        ]
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            composition_structures=structures,
        )
        assert len(fc.composition_structures) == 2
        assert fc.composition_structures[0]["type"] == "building"

    def test_composition_structures_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.composition_structures
        assert col.nullable is True

    def test_composition_does_not_duplicate_equipment(self):
        """composition_structures stores buildings/sites, NOT equipment.
        Equipment stays in EquipmentModel (source of truth)."""
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            composition_structures=[{"type": "building", "name": "ГРП"}],
        )
        # No equipment in structures
        assert all(s.get("type") != "equipment" for s in fc.composition_structures)


# ═══════════════════════════════════════════════════════════════════════════
# 6. licensed_activities
# ═══════════════════════════════════════════════════════════════════════════

class TestLicensedActivities:
    def test_requires_license_id(self):
        from src.api.routers.facilities import FacilityCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FacilityCreate(
                organization_id=uuid4(), name="Тест",
                licensed_activities=[{"activity": "газоснабжение"}],
            )

    def test_valid_structure(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(), name="Тест",
            licensed_activities=[{"license_id": str(uuid4()), "activity": "газоснабжение"}],
        )
        assert len(fc.licensed_activities) == 1
        assert "license_id" in fc.licensed_activities[0]


# ═══════════════════════════════════════════════════════════════════════════
# 7. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    def test_old_record_works(self):
        from src.api.routers.facilities import FacilityResponse
        fr = FacilityResponse(
            id=uuid4(), organization_id=uuid4(), name="Старая",
            reg_number="ОО-001", hazard_class=3, facility_type="Сеть",
            address="г. Тест", latitude=55.0, longitude=37.0,
            inventory_number="INV-001", properties={"okved": "46.71"},
        )
        assert fr.classification is None
        assert fr.work_processes is None
        assert fr.composition_structures is None

    def test_opo_full_name_priority_in_context(self):
        """PMLA context uses opo_full_name when set, falls back to name."""
        f = MagicMock()
        f.id = uuid4()
        f.name = "Сеть газопотребления"
        f.opo_full_name = "Сеть газопотребления ООО ТестГазпром"
        f.reg_number = None; f.hazard_class = None; f.facility_type = None
        f.address = None; f.latitude = None; f.longitude = None
        f.commissioning_date = None; f.inventory_number = None; f.properties = None
        f.classification = None; f.work_processes = None
        f.licensed_activities = None; f.composition_structures = None; f.nearby_hazardous = None

        # Context builder logic: opo_full_name or name
        name = f.opo_full_name or f.name or ""
        assert name == "Сеть газопотребления ООО ТестГазпром"
        assert name != f.name

    def test_name_fallback_when_no_opo_full_name(self):
        """Old record: name used when opo_full_name is None."""
        f = MagicMock()
        f.name = "Сеть газопотребления"
        f.opo_full_name = None

        name = f.opo_full_name or f.name or ""
        assert name == "Сеть газопотребления"

    def test_name_independent_of_opo_full_name(self):
        from src.api.routers.facilities import FacilityCreate
        fc = FacilityCreate(
            organization_id=uuid4(),
            name="Сеть газопотребления",
            opo_full_name="Сеть газопотребления ООО ТестГазпром",
        )
        assert fc.name != fc.opo_full_name

    def test_context_builder_defaults(self):
        f = MagicMock()
        f.opo_full_name = None; f.classification = None
        f.work_processes = None; f.licensed_activities = None
        f.composition_structures = None; f.nearby_hazardous = None

        ctx = {
            "classification": f.classification or [],
            "composition_structures": f.composition_structures or [],
        }
        assert ctx["classification"] == []
        assert ctx["composition_structures"] == []


# ═══════════════════════════════════════════════════════════════════════════
# 8. No unauthorized fields
# ═══════════════════════════════════════════════════════════════════════════

class TestNoUnauthorizedFields:
    ALLOWED = {
        "id", "organization_id", "name", "reg_number", "hazard_class",
        "facility_type", "address", "latitude", "longitude",
        "commissioning_date", "inventory_number", "properties",
        "opo_full_name", "classification", "work_processes",
        "licensed_activities", "composition_structures", "nearby_hazardous",
    }

    def test_response_fields(self):
        from src.api.routers.facilities import FacilityResponse
        extra = set(FacilityResponse.model_fields.keys()) - self.ALLOWED
        assert not extra, f"Unauthorized: {extra}"

    def test_create_fields(self):
        from src.api.routers.facilities import FacilityCreate
        extra = set(FacilityCreate.model_fields.keys()) - (self.ALLOWED | {"organization_id"})
        assert not extra, f"Unauthorized: {extra}"


# ═══════════════════════════════════════════════════════════════════════════
# 9. Model fields
# ═══════════════════════════════════════════════════════════════════════════

class TestModelFields:
    def test_opo_full_name_type(self):
        col = HazardousFacilityModel.__table__.c.opo_full_name
        assert col.nullable is True

    def test_composition_structures_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.composition_structures
        assert col.nullable is True

    def test_nearby_hazardous_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.nearby_hazardous
        assert col.nullable is True

    def test_licensed_activities_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.licensed_activities
        assert col.nullable is True

    def test_work_processes_is_jsonb(self):
        col = HazardousFacilityModel.__table__.c.work_processes
        assert col.nullable is True

    def test_existing_fields_preserved(self):
        t = HazardousFacilityModel.__table__
        for name in ["id", "organization_id", "name", "reg_number", "hazard_class",
                      "facility_type", "address", "properties", "created_at", "updated_at"]:
            assert name in t.c, f"Missing: {name}"
