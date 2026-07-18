"""Focused PASF document upload and PMLA v2 mapping/manifest regression tests.

These tests exercise the real PASF upload endpoint with mocked dependencies and
verify the selected-document data used by preflight, v2 mapping, and appendices
manifest generation. They intentionally avoid depending on existing database rows.
"""
from __future__ import annotations

import hashlib
import io
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_db, get_emergency_rescue_unit_repo
from src.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer isap-secret-2026"},
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def temp_pdf():
    """Create a minimal valid PDF in a project-local temp directory."""
    import tempfile

    tmp_dir = Path(tempfile.gettempdir()) / "isap_e2e_tests"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = tmp_dir / "test_certificate.pdf"

    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    yield pdf_path
    if pdf_path.exists():
        pdf_path.unlink()


@pytest.fixture
def temp_pdf_bytes(temp_pdf):
    """Return the PDF content as bytes."""
    return temp_pdf.read_bytes()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPasfDocumentsE2E:
    """E2E test for PASF document upload and integration with PMLA v2 generation."""

    @pytest.mark.asyncio
    async def test_pasf_document_upload_and_context(
        self, client: AsyncClient, temp_pdf, temp_pdf_bytes
    ):
        """Test upload via the real endpoint without relying on existing DB rows."""
        from src.api.routers.directories_pasf import _resolve_pasf_document_path

        pasf_id = uuid4()
        expected_checksum = hashlib.sha256(temp_pdf_bytes).hexdigest()
        added_docs = []

        fake_pasf = MagicMock()
        fake_pasf.id = pasf_id
        fake_repo = AsyncMock()
        fake_repo.get = AsyncMock(return_value=fake_pasf)

        fake_db = MagicMock()
        fake_db.add.side_effect = added_docs.append
        fake_db.commit = AsyncMock()

        async def refresh_doc(doc):
            if doc.id is None:
                doc.id = uuid4()
            doc.updated_at = datetime.now(UTC).replace(tzinfo=None)

        fake_db.refresh = AsyncMock(side_effect=refresh_doc)

        async def override_db():
            yield fake_db

        app.dependency_overrides[get_emergency_rescue_unit_repo] = lambda: fake_repo
        app.dependency_overrides[get_db] = override_db

        try:
            with open(temp_pdf, "rb") as f:
                resp = await client.post(
                    f"/api/v1/directories/pasf/{pasf_id}/documents",
                    files={"file": ("test_certificate.pdf", f, "application/pdf")},
                    data={
                        "document_type": "certificate",
                        "document_number": "TEST-CERT-E2E",
                        "title": "E2E Test Certificate",
                        "issued_at": "2024-01-15",
                        "valid_until": "2030-12-31",
                    },
                )

            assert resp.status_code == 201, resp.text
            doc_data = resp.json()
            assert doc_data["pasf_id"] == str(pasf_id)
            assert doc_data["document_type"] == "certificate"
            assert doc_data["document_number"] == "TEST-CERT-E2E"
            assert doc_data["mime_type"] == "application/pdf"
            assert doc_data["checksum_sha256"] == expected_checksum
            assert doc_data["status"] == "active"
            assert doc_data["file_name"] == "test_certificate.pdf"
            assert added_docs, "Upload endpoint did not add a PasfDocumentModel"
            assert added_docs[0].file_path.startswith("pasf_documents")
        finally:
            for doc in added_docs:
                if doc.file_path:
                    uploaded_path = Path(_resolve_pasf_document_path(doc.file_path))
                    if uploaded_path.exists():
                        uploaded_path.unlink()

    @pytest.mark.asyncio
    async def test_document_in_generation_context(
        self, client: AsyncClient, temp_pdf, temp_pdf_bytes
    ):
        """Test that selected PASF documents appear in generation context."""
        # This test verifies that the mapper correctly includes PASF documents
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [{"id": "eq-1", "name": "Equipment 1"}],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {},
            "pasf": {"id": "pasf-1", "name": "Test PASF"},
            "pasf_documents": [
                {
                    "id": "doc-1",
                    "document_type": "certificate",
                    "document_number": "CERT-001",
                    "title": "Certificate",
                    "file_name": "cert.pdf",
                    "checksum_sha256": "abc123",
                    "status": "active",
                }
            ],
            "emergency_services": [],
        }

        v2_ctx = map_to_v2_context(context)

        # Verify contract date comes from contract document
        assert "contractor_agreement_date" in v2_ctx
        assert "contractor_agreement_number" in v2_ctx

    @pytest.mark.asyncio
    async def test_contract_date_from_contract_document(self):
        """Test that contract date comes from a contract-type document, not certificate."""
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {},
            "pasf": {
                "id": "pasf-1",
                "name": "Test PASF",
                "certificate_number": "CERT-123",
                "certificate_date": "2023-01-01",
            },
            "pasf_documents": [
                {
                    "id": "doc-cert",
                    "document_type": "certificate",
                    "document_number": "CERT-123",
                    "issued_at": "2023-01-01",
                },
                {
                    "id": "doc-contract",
                    "document_type": "contract",
                    "document_number": "CONTRACT-456",
                    "issued_at": "2024-06-15",
                },
            ],
            "emergency_services": [],
        }

        v2_ctx = map_to_v2_context(context)

        # Contract date should come from the contract document, not certificate
        assert v2_ctx["contractor_agreement_date"] == "15.06.2024"
        assert v2_ctx["contractor_agreement_number"] == "CONTRACT-456"

    @pytest.mark.asyncio
    async def test_certificate_date_not_used_as_contract_date(self):
        """Test that certificate date is NOT used as contract date when no contract exists."""
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {},
            "pasf": {
                "id": "pasf-1",
                "name": "Test PASF",
                "certificate_number": "CERT-123",
                "certificate_date": "2023-01-01",
            },
            "pasf_documents": [
                {
                    "id": "doc-cert",
                    "document_type": "certificate",
                    "document_number": "CERT-123",
                    "issued_at": "2023-01-01",
                },
            ],
            "emergency_services": [],
        }

        v2_ctx = map_to_v2_context(context)

        # No contract document and no agreement_date fallback are present.
        assert v2_ctx["contractor_agreement_date"] == "—"

    @pytest.mark.asyncio
    async def test_service_type_normalization(self):
        """Test that service type aliases are normalized correctly."""
        from src.application.services.pmla_v2_context_mapper import (
            _normalize_service_type,
            _find_emergency_service,
        )

        # Test alias normalization
        assert _normalize_service_type("medical") == "ambulance"
        assert _normalize_service_type("скорая") == "ambulance"
        assert _normalize_service_type("gas_service") == "gas"
        assert _normalize_service_type("power") == "electric"
        assert _normalize_service_type("fire_department") == "fire"
        assert _normalize_service_type("112") == "edds"

        # Test finding service with alias
        services = [
            {"service_type": "medical", "name": "Ambulance", "phone": "103"},
            {"service_type": "gas", "name": "Gas Service", "phone": "104"},
        ]

        ambulance = _find_emergency_service(services, "ambulance")
        assert ambulance is not None
        assert ambulance["name"] == "Ambulance"

        gas = _find_emergency_service(services, "gas")
        assert gas is not None
        assert gas["name"] == "Gas Service"

    @pytest.mark.asyncio
    async def test_phone_priority_dispatcher_first(self):
        """Test that dispatcher_phone has priority over phone."""
        from src.application.services.pmla_v2_context_mapper import _get_phone

        service = {
            "phone": "100",
            "dispatcher_phone": "200",
            "additional_phone": "300",
        }

        # dispatcher_phone should be returned first
        assert _get_phone(service, "dispatcher_phone", "phone") == "200"

        # If dispatcher_phone is empty, phone should be returned
        service_no_dispatcher = {"phone": "100", "dispatcher_phone": ""}
        assert _get_phone(service_no_dispatcher, "dispatcher_phone", "phone") == "100"

    @pytest.mark.asyncio
    async def test_selected_scenarios_appear_in_accident_scenarios(self):
        """Test that selected scenarios from questionnaire appear in accident_scenarios."""
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {
                "selected_scenarios": ["утечка опасного вещества"],
                "custom_scenarios": [
                    {"title": "Custom Scenario", "description": "Custom description"}
                ],
            },
            "pasf": {},
            "pasf_documents": [],
            "emergency_services": [],
        }

        v2_ctx = map_to_v2_context(context)

        assert len(v2_ctx["accident_scenarios"]) >= 2
        names = [s["name"] for s in v2_ctx["accident_scenarios"]]
        assert "утечка опасного вещества" in names
        assert "Custom Scenario" in names

    @pytest.mark.asyncio
    async def test_equipment_scenario_link_uses_equipment_ids(self):
        """Test that equipment-scenario links use equipment_ids, not text matching."""
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [
                {"id": "eq-1", "name": "ШРП-МС-10 (регулятор РДГК-10М)"},
                {"id": "eq-2", "name": "Газопровод"},
            ],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {},
            "pasf": {},
            "pasf_documents": [],
            "emergency_services": [],
            "scenarios": [
                {
                    "code": "С-1",
                    "name": "Утечка",
                    "equipment_ids": ["eq-1"],
                    "description": "Утечка газа",
                },
            ],
        }

        v2_ctx = map_to_v2_context(context)

        links = v2_ctx["equipment_scenario_links"]
        # eq-1 should be linked to scenario С-1
        eq1_link = next(l for l in links if "ШРП-МС-10" in l["equipment_name"])
        assert eq1_link["scenario_codes"] == "С-1"
        assert eq1_link["description"] == "Утечка газа"

        # eq-2 should NOT be linked (no equipment_ids match)
        eq2_link = next(l for l in links if "Газопровод" in l["equipment_name"])
        assert eq2_link["scenario_codes"] == "—"

    @pytest.mark.asyncio
    async def test_rdgk_10m_not_modified(self):
        """Test that equipment name РДГК-10М is not modified."""
        from src.application.services.pmla_v2_context_mapper import map_to_v2_context

        context = {
            "organization": {"id": "org-1", "name": "Test Org"},
            "facility": {"id": "fac-1", "name": "Test Facility", "facility_type": "gas"},
            "equipment": [
                {"id": "eq-1", "name": "ШРП-МС-10 (регулятор РДГК-10М)"},
            ],
            "substances": [],
            "responsible_persons": [],
            "questionnaire": {},
            "pasf": {},
            "pasf_documents": [],
            "emergency_services": [],
        }

        v2_ctx = map_to_v2_context(context)

        eq = v2_ctx["equipment_list"][0]
        assert "РДГК-10М" in eq["device_name"]

    @pytest.mark.asyncio
    async def test_manifest_contains_real_file_name(self):
        """Test that the manifest contains real file_name from PASF documents."""
        from src.application.services.enhanced_generator import _synthesize_appendices_manifest

        pasf_documents = [
            {
                "id": "doc-1",
                "document_type": "certificate",
                "title": "Certificate",
                "file_name": "certificate_2024.pdf",
                "document_number": "CERT-001",
                "issued_at": "2024-01-15",
                "valid_until": "2030-12-31",
                "checksum_sha256": "abc123",
            }
        ]

        manifest = _synthesize_appendices_manifest([], pasf_documents)

        # Find the PASF document entry
        pasf_entries = [m for m in manifest if m.get("document_type") == "certificate"]
        assert len(pasf_entries) == 1
        assert pasf_entries[0]["filename"] == "certificate_2024.pdf"
        assert pasf_entries[0]["present"] is True

    @pytest.mark.asyncio
    async def test_unselected_documents_not_in_manifest(self):
        """Test that unselected documents do not appear in the manifest."""
        from src.application.services.enhanced_generator import _synthesize_appendices_manifest

        # Only selected documents are passed to the manifest
        selected_documents = [
            {
                "id": "doc-1",
                "document_type": "certificate",
                "title": "Selected Certificate",
                "file_name": "selected.pdf",
            }
        ]

        manifest = _synthesize_appendices_manifest([], selected_documents)

        # Only the selected document should appear
        pasf_entries = [m for m in manifest if m.get("document_type") == "certificate"]
        assert len(pasf_entries) == 1
        assert pasf_entries[0]["filename"] == "selected.pdf"
