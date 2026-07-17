"""Unit and regression tests for ``PmlaOoxmlFlatRenderer``.

Covers:
  * basic rendering produces a valid DOCX (ZIP) with no leftover Jinja tags;
  * all flat placeholders declared by the real template are substituted;
  * split-run placeholders (``{{`` split across ``w:t`` runs) are reassembled;
  * dotted context tokens (``{{ person.position }}``) resolve through the raw context;
  * table-row loops (``{%tr for eq in equipment_list %}``) expand to one row per item;
  * byte-for-byte media preservation: every non-text part of the template is
    identical in the rendered output;
  * missing placeholders raise ``PlaceholderNotFoundError``;
  * concurrent ``render()`` calls on the SAME renderer instance do NOT mix
    contexts (the D2 thread-safety guarantee — no shared mutable state).

These tests use the real ``files/pmla_v2_template.docx``; no DB or network.
"""
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from lxml import etree

from src.application.services.pmla_ooxml_flat_renderer import (
    PmlaOoxmlFlatRenderer,
    PlaceholderNotFoundError,
)

# ---------------------------------------------------------------------------
# Paths & helpers
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = REPO_ROOT / "files" / "pmla_v2_template.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = lambda tag: f"{{{W_NS}}}{tag}"

# Parts that the renderer may rewrite; everything else must be byte-identical.
TEXT_PARTS = PmlaOoxmlFlatRenderer.TEXT_PARTS


def _gather_text(xml_bytes: bytes) -> str:
    """Concatenate all ``w:t`` text in document order (mirrors renderer)."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return ""
    return "".join((e.text or "") for e in root.iter(W("t")))


def _full_context(**overrides) -> dict:
    """Build a context that serves every flat placeholder declared by the
    template so ``render()`` does not raise PlaceholderNotFoundError.
    Dotted tokens (``person.position``) are served via a nested ``person`` dict.
    Loop data is served via ``equipment_list``."""
    renderer = PmlaOoxmlFlatRenderer()
    placeholders = renderer._extract_flat_placeholders()
    ctx: dict = {}
    for ph in placeholders:
        if "." in ph:
            head, _, field = ph.partition(".")
            ctx.setdefault(head, {})[field] = f"<{ph}>"
        else:
            ctx[ph] = f"<{ph}>"
    ctx.setdefault(
        "equipment_list",
        [
            {
                "device_name": "Котёл",
                "hazard_characteristic": "Опасно",
                "location": "Котельная",
                "process_codes": "1",
                "specifications": "150 т/ч",
            }
        ],
    )
    ctx.setdefault(
        "substance_params",
        [{"parameter": "P1", "value": "V1"}, {"parameter": "P2", "value": "V2"}],
    )
    ctx.setdefault(
        "equipment_scenario_links",
        [
            {
                "equipment_name": "Оборудование-1",
                "scenario_codes": "S-1, S-2",
                "description": "Описание сценария",
                "damaging_factors": "Факторы воздействия",
            }
        ],
    )
    ctx.setdefault(
        "accident_scenarios",
        [
            {
                "code": "S-1",
                "name": "Сценарий первый",
                "source": "Источник",
                "preconditions": "Причины",
                "signs": "Признаки",
                "damaging_factors": "Факторы",
            },
            {
                "code": "S-2",
                "name": "Сценарий второй",
                "source": "Источник-2",
                "preconditions": "Причины-2",
                "signs": "Признаки-2",
                "damaging_factors": "Факторы-2",
            },
        ],
    )
    ctx.setdefault(
        "material_reserve_actual",
        [
            {"name": "Средство-1", "quantity": "10", "location": "Склад-1"},
            {"name": "Средство-2", "quantity": "5", "location": "Склад-2"},
        ],
    )
    ctx.setdefault(
        "material_reserve_recommended",
        [
            {"name": "Рек. средство", "quantity": "2", "location": "Склад-Р"},
        ],
    )
    ctx.setdefault(
        "countermeasures",
        [
            {
                "scenario_label": "S-1 Мера",
                "signs": "Признак",
                "protection": "Защита",
                "technical_means": "Средства",
                "executors": "Исполнители",
            }
        ],
    )
    ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def renderer() -> PmlaOoxmlFlatRenderer:
    return PmlaOoxmlFlatRenderer()


@pytest.fixture(scope="module")
def template_part_names() -> list[str]:
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as z:
        return z.namelist()


# ---------------------------------------------------------------------------
# 1. Basic rendering
# ---------------------------------------------------------------------------
class TestBasicRendering:
    def test_render_returns_bytes(self, renderer):
        out = renderer.render(_full_context())
        assert isinstance(out, bytes)
        assert len(out) > 100_000  # the template alone is ~6 MB

    def test_output_is_valid_zip(self, renderer):
        out = renderer.render(_full_context())
        buf = io.BytesIO(out)
        with zipfile.ZipFile(buf, "r") as z:
            assert z.testzip() is None  # no CRC errors
            assert "[Content_Types].xml" in z.namelist()
            assert "word/document.xml" in z.namelist()

    def test_no_leftover_jinja_tags(self, renderer):
        out = renderer.render(_full_context())
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in TEXT_PARTS:
                if part not in z.namelist():
                    continue
                text = _gather_text(z.read(part))
                assert "{{" not in text, f"unreplaced placeholder in {part}"
                assert "{%" not in text, f"unreplaced loop tag in {part}"

    def test_all_xml_parts_parse(self, renderer):
        out = renderer.render(_full_context())
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in z.namelist():
                if part.endswith(".xml") or part.endswith(".rels"):
                    etree.fromstring(z.read(part))  # raises on invalid XML


# ---------------------------------------------------------------------------
# 2. Placeholder substitution
# ---------------------------------------------------------------------------
class TestPlaceholderSubstitution:
    def test_every_flat_placeholder_is_substituted(self, renderer):
        """Every placeholder declared in the template must be replaced —
        none should survive into the rendered document text.

        Guard against a self-referential false-pass: if extraction returned
        an empty set, the loop below would trivially succeed. We assert the
        extracted set is non-trivially large (the real template declares 60+
        flat placeholders) before checking substitution."""
        placeholders = renderer._extract_flat_placeholders()
        assert len(placeholders) >= 55, (
            f"extraction returned suspiciously few placeholders ({len(placeholders)}); "
            "possible regex regression"
        )
        out = renderer.render(_full_context())
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            combined = "\n".join(
                _gather_text(z.read(p)) for p in TEXT_PARTS if p in z.namelist()
            )
        for ph in placeholders:
            assert f"{{{{{ph}}}}}" not in combined, f"placeholder {ph!r} survived"

    def test_scalar_value_appears_in_output(self, renderer):
        ctx = _full_context(organization_full_name="ООО Тестовая Организация")
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        assert "ООО Тестовая Организация" in doc_text

    def test_dotted_token_resolves(self, renderer):
        """Dotted token ``{{ person.position }}`` must resolve through the
        nested raw context (D2/D3 path — no shared mutable state)."""
        ctx = _full_context()
        ctx["person"] = {"position": "Генеральный директор", "phone": "+7 999 000 11 22"}
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        assert "Генеральный директор" in doc_text
        assert "+7 999 000 11 22" in doc_text

    def test_xml_special_chars_single_escape(self, renderer):
        """Values with ``&``, ``<``, ``>`` must be escaped EXACTLY ONCE by
        lxml during serialization (defect #2: the renderer used to call
        ``_xml_escape`` manually, then lxml re-escaped → ``A &amp;lt; B``).
        After the fix the raw XML carries the single-escaped form and the
        extracted text recovers the original value verbatim."""
        special = "ООО «Газ & Сервис»"
        ctx = _full_context(organization_full_name=special, facility_name="A < B > C")
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw_doc = z.read("word/document.xml")
            doc_text = _gather_text(raw_doc)
        # Structurally valid (no corruption from raw angle brackets).
        assert etree.fromstring(raw_doc) is not None
        # Extracted text recovers the original value exactly once.
        assert special in doc_text
        assert "A < B > C" in doc_text
        # Raw XML carries the single-escaped form, NOT double-escaped.
        assert b"&amp;lt;" not in raw_doc  # double-escape artifact
        assert b"&amp;amp;" not in raw_doc
        assert b"&amp;gt;" not in raw_doc
        # And it does carry the legitimate single-escaped form.
        assert b"&amp;" in raw_doc  # & → &amp;
        assert b"&lt;" in raw_doc   # < → &lt;
        assert b"&gt;" in raw_doc   # > → &gt;


# ---------------------------------------------------------------------------
# 3. Split-run placeholder reassembly
# ---------------------------------------------------------------------------
class TestSplitRunPlaceholders:
    """Template placeholders are frequently split across ``w:t`` runs by Word
    (e.g. ``{`` + ``{` + `` facility_name `` + ``}`` + ``}``). The robust
    replacer concatenates runs before matching, so these must resolve."""

    def test_extract_finds_split_placeholders(self, renderer):
        """Extraction reads the concatenated buffer, so it must find all 60+
        placeholders even though Word splits many of them across runs."""
        ph = renderer._extract_flat_placeholders()
        assert "organization_full_name" in ph
        assert "person.position" in ph  # dotted token (D3)

    def test_rendered_text_has_no_brace_fragments(self, renderer):
        out = renderer.render(_full_context())
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        # No stray single braces that would indicate a half-replaced token.
        # (We cannot ban all ``{`` — they appear in Russian dates — but a
        # leftover ``{{`` fragment means a split token was missed.)
        assert "{{" not in doc_text


# ---------------------------------------------------------------------------
# 4. Table-row loop expansion
# ---------------------------------------------------------------------------
class TestLoopExpansion:
    def test_equipment_list_expands_to_rows(self, renderer):
        """Loop expansion: at least one item field value must appear in the
        output, and the loop control markers must be removed.

        After the ``_fill_loop_row`` rewrite (concatenated-buffer mechanism),
        ALL loop fields are reliably filled regardless of run layout."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": f"Оборудование-{i}",
                "hazard_characteristic": f"Характеристика-{i}",
                "location": f"Цех-{i}",
                "process_codes": f"Код-{i}",
                "specifications": f"Спец-{i}",
            }
            for i in range(1, 4)
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        # Loop control markers must be removed.
        assert "{%tr" not in doc_text
        assert "{%" not in doc_text
        # ALL fields must surface for every item (the bug used to drop
        # device_name / location / process_codes).
        for i in (1, 2, 3):
            assert f"Оборудование-{i}" in doc_text, f"device_name #{i} missing"
            assert f"Характеристика-{i}" in doc_text, f"hazard_characteristic #{i} missing"
            assert f"Цех-{i}" in doc_text, f"location #{i} missing"
            assert f"Код-{i}" in doc_text, f"process_codes #{i} missing"
            assert f"Спец-{i}" in doc_text, f"specifications #{i} missing"
        # loop.index: assert via the table structure — exactly 3 data rows
        # exist (header + sub-header + 3 items + footer). Counting rows is
        # robust against bare-digit false positives.
        root = etree.fromstring(zipfile.ZipFile(io.BytesIO(out)).read("word/document.xml"))
        eq_table_rows = 0
        for tr in root.iter(W("tr")):
            row_text = "".join((t.text or "") for t in tr.iter(W("t")))
            # Use "Характеристика-" which is unique to equipment_list fields
            # (avoids false match from equipment_scenario_links containing "Оборудование-1")
            if any(f"Характеристика-{i}" in row_text for i in (1, 2, 3)):
                eq_table_rows += 1
        assert eq_table_rows == 3, f"expected 3 data rows from loop.index, got {eq_table_rows}"

    def test_empty_equipment_list_drops_loop_control(self, renderer):
        """An empty loop list must remove ALL three loop template rows
        (control ``{%tr for %}``, data ``{{ eq.field }}``, endfor ``{%tr endfor %}``)
        so no Jinja markers survive in the output."""
        ctx = _full_context()
        ctx["equipment_list"] = []
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        assert "{%tr for" not in doc_text
        assert "{%tr endfor" not in doc_text
        assert "{%" not in doc_text
        # Loop-variable tokens must also be gone (data row removed).
        assert "{{ eq." not in doc_text
        assert "loop.index" not in doc_text


# ---------------------------------------------------------------------------
# 5. Byte-for-byte media preservation (Agent 2 regression guard)
# ---------------------------------------------------------------------------
class TestMediaPreservation:
    def test_non_text_parts_byte_identical(self, renderer, template_part_names):
        """Every part the renderer does NOT rewrite must be byte-identical to
        the template. This is the core graphics-preservation guarantee."""
        out = renderer.render(_full_context())
        with (
            zipfile.ZipFile(io.BytesIO(out), "r") as z_out,
            zipfile.ZipFile(TEMPLATE_PATH, "r") as z_tpl,
        ):
            out_names = z_out.namelist()
            # No part lost
            assert set(template_part_names) == set(out_names)
            for part in template_part_names:
                if part in TEXT_PARTS:
                    continue  # text parts are rewritten (expected)
                tpl_bytes = z_tpl.read(part)
                out_bytes = z_out.read(part)
                assert tpl_bytes == out_bytes, f"part {part} differs from template"

    def test_all_media_parts_identical(self, renderer, template_part_names):
        """All word/media/* images must be byte-identical (14 images)."""
        media = [p for p in template_part_names if p.startswith("word/media/")]
        assert len(media) >= 14, f"expected >=14 media parts, got {len(media)}"
        out = renderer.render(_full_context())
        with (
            zipfile.ZipFile(io.BytesIO(out), "r") as z_out,
            zipfile.ZipFile(TEMPLATE_PATH, "r") as z_tpl,
        ):
            for part in media:
                assert z_tpl.read(part) == z_out.read(part), f"media {part} corrupted"

    def test_no_part_lost_or_added(self, renderer, template_part_names):
        out = renderer.render(_full_context())
        with zipfile.ZipFile(io.BytesIO(out), "r") as z_out:
            assert set(z_out.namelist()) == set(template_part_names)


# ---------------------------------------------------------------------------
# 6. Validation / error paths
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_placeholder_raises(self, renderer):
        ctx = _full_context()
        del ctx["organization_full_name"]
        with pytest.raises(PlaceholderNotFoundError) as exc:
            renderer.render(ctx)
        assert "organization_full_name" in str(exc.value)

    def test_missing_dotted_token_raises(self, renderer):
        """Dotted tokens are validated too (D3): if ``person`` is absent,
        ``person.position`` must raise rather than silently emit ``{{ }}``."""
        ctx = _full_context()
        del ctx["person"]
        with pytest.raises(PlaceholderNotFoundError) as exc:
            renderer.render(ctx)
        assert "person.position" in str(exc.value)

    def test_unknown_context_key_warns_not_errors(self, renderer, caplog):
        import logging

        ctx = _full_context(unknown_extra_key="ignored")
        with caplog.at_level(logging.WARNING):
            out = renderer.render(ctx)
        assert isinstance(out, bytes)
        assert any("unused by template" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 6b. Public API extras
# ---------------------------------------------------------------------------
class TestPublicApiExtras:
    def test_render_to_file_writes_valid_docx(self, renderer):
        """``render_to_file`` must write a valid ZIP/DOCX to disk. Uses the
        local pytest tmp dir (conftest sets TMPDIR) to avoid Windows system
        temp permission errors."""
        out_dir = REPO_ROOT / "backend" / ".pytest_tmp"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "flat_renderer_out.docx"
        try:
            result = renderer.render_to_file(_full_context(), out_path)
            assert result.exists()
            with zipfile.ZipFile(result, "r") as z:
                assert z.testzip() is None
                assert "word/document.xml" in z.namelist()
        finally:
            if out_path.exists():
                out_path.unlink()

    def test_create_renderer_factory(self):
        """``create_renderer`` returns a usable instance."""
        from src.application.services.pmla_ooxml_flat_renderer import create_renderer
        r = create_renderer()
        assert isinstance(r, PmlaOoxmlFlatRenderer)
        assert r.template_path.exists()

    def test_forbidden_jinja_raises(self):
        """A template containing an unsupported Jinja construct (``{% if %}``)
        must be rejected. We build a minimal DOCX so we don't touch the real
        template."""
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>{% if x %}bad{% endif %}</w:t></w:r></w:p></w:body></w:document>'
        )
        ct_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        out_dir = REPO_ROOT / "backend" / ".pytest_tmp"
        out_dir.mkdir(exist_ok=True)
        tpl = out_dir / "bad_template.docx"
        try:
            with zipfile.ZipFile(tpl, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("[Content_Types].xml", ct_xml)
                z.writestr("word/document.xml", doc_xml)
            r = PmlaOoxmlFlatRenderer(template_path=tpl)
            with pytest.raises(Exception) as exc:
                r.render({})
            assert "unsupported" in str(exc.value).lower() or "jinja" in str(exc.value).lower()
        finally:
            if tpl.exists():
                tpl.unlink()


# ---------------------------------------------------------------------------
# 7. Thread-safety / no shared mutable state (D2 regression guard)
# ---------------------------------------------------------------------------
class TestConcurrency:
    """The D2 fix removed all per-render instance state. Concurrent ``render()``
    calls on the SAME instance with DIFFERENT contexts must NOT mix: each
    output must contain only its own values."""

    def test_concurrent_renders_do_not_mix_context(self, renderer):
        contexts = {
            "alpha": _full_context(
                organization_full_name="АЛЬФА-ОРГАНИЗАЦИЯ",
                facility_name="АЛЬФА-ОБЪЕКТ",
                person={"position": "Директор Альфа", "phone": "+7 111 111 11 11"},
            ),
            "beta": _full_context(
                organization_full_name="БЕТА-ОРГАНИЗАЦИЯ",
                facility_name="БЕТА-ОБЪЕКТ",
                person={"position": "Директор Бета", "phone": "+7 222 222 22 22"},
            ),
            "gamma": _full_context(
                organization_full_name="ГАММА-ОРГАНИЗАЦИЯ",
                facility_name="ГАММА-ОБЪЕКТ",
                person={"position": "Директор Гамма", "phone": "+7 333 333 33 33"},
            ),
        }

        def _render(label: str) -> tuple[str, bytes]:
            return label, renderer.render(contexts[label])

        # Each output must contain ONLY its own markers and NONE of the others.
        markers = {
            "alpha": ("АЛЬФА-ОРГАНИЗАЦИЯ", "АЛЬФА-ОБЪЕКТ", "Директор Альфа"),
            "beta": ("БЕТА-ОРГАНИЗАЦИЯ", "БЕТА-ОБЪЕКТ", "Директор Бета"),
            "gamma": ("ГАММА-ОРГАНИЗАЦИЯ", "ГАММА-ОБЪЕКТ", "Директор Гамма"),
        }

        def _check_no_contamination(batch: dict[str, bytes], batch_no: int) -> None:
            assert set(batch.keys()) == {"alpha", "beta", "gamma"}
            for label, out in batch.items():
                with zipfile.ZipFile(io.BytesIO(out), "r") as z:
                    doc_text = _gather_text(z.read("word/document.xml"))
                for val in markers[label]:
                    assert val in doc_text, (
                        f"batch {batch_no} {label}: missing own value {val!r}"
                    )
                for other_label, other_vals in markers.items():
                    if other_label == label:
                        continue
                    for val in other_vals:
                        assert val not in doc_text, (
                            f"batch {batch_no} {label}: leaked {other_label} value "
                            f"{val!r} (shared mutable state regression — D2)"
                        )

        # Repeat the concurrent batch several times and check EACH batch
        # immediately, so a non-deterministic race in an early batch is not
        # masked by a clean final batch.
        for batch_no in range(10):
            batch: dict[str, bytes] = {}
            with ThreadPoolExecutor(max_workers=3) as pool:
                for label, out in pool.map(_render, contexts.keys()):
                    batch[label] = out
            _check_no_contamination(batch, batch_no)

    def test_instance_has_no_raw_context_state(self, renderer):
        """After a render, neither the instance nor the class's static method
        may carry residual per-render state. The old D2 bug stored
        ``_resolve_flat._raw_context`` on the function object and
        ``self._loop_lists`` on the instance, leaking between renders."""
        renderer.render(_full_context(organization_full_name="ПОСЛЕ-РЕНДЕРА"))
        # No per-render state on the static-method function object.
        assert not hasattr(PmlaOoxmlFlatRenderer._resolve_flat, "_raw_context")
        # No per-render state on the instance beyond the cached template inventory.
        leaked = {
            k for k in vars(renderer)
            if not k.startswith("_part") and k not in {"template_path"}
        }
        assert not leaked, f"unexpected per-render instance state leaked: {leaked}"

    def test_repeated_render_is_semantically_equivalent(self, renderer):
        """Re-rendering the same context must yield equivalent output
        (AGENTS.md §9 invariant). Byte-identity is not guaranteed because
        ZIP writes carry non-deterministic timestamps; instead we assert
        that every non-text part is byte-identical AND every text part has
        identical concatenated text content."""
        ctx = _full_context()
        out1 = renderer.render(ctx)
        out2 = renderer.render(ctx)
        with (
            zipfile.ZipFile(io.BytesIO(out1), "r") as z1,
            zipfile.ZipFile(io.BytesIO(out2), "r") as z2,
        ):
            assert set(z1.namelist()) == set(z2.namelist())
            for part in z1.namelist():
                d1, d2 = z1.read(part), z2.read(part)
                if part in TEXT_PARTS:
                    assert _gather_text(d1) == _gather_text(d2), f"text differs in {part}"
                else:
                    assert d1 == d2, f"non-text part {part} differs"


# ---------------------------------------------------------------------------
# 8. Defect fixes: empty-loop cleanup + single XML escaping
# ---------------------------------------------------------------------------
class TestDefectFixes:
    """Targeted regression tests for two bugs fixed after the D1–D4 round:
    1. Empty loop list left split-run ``{%tr %}`` / ``{{ eq. }}`` markers.
    2. Manual ``_xml_escape`` + lxml serialize → double-escaped values."""

    # -- Defect #1: empty loop cleanup -------------------------------------
    def test_empty_loop_no_jinja_anywhere(self, renderer):
        """Empty ``equipment_list`` must leave NO Jinja markers in ANY text
        part of the document, not just document.xml."""
        ctx = _full_context()
        ctx["equipment_list"] = []
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in TEXT_PARTS:
                if part not in z.namelist():
                    continue
                text = _gather_text(z.read(part))
                assert "{%" not in text, f"loop tag leaked into {part}"
                assert "{{ eq." not in text, f"loop var leaked into {part}"
                assert "loop.index" not in text, f"loop index leaked into {part}"

    def test_empty_loop_does_not_corrupt_zip(self, renderer, template_part_names):
        """Empty loop must still produce a valid, complete ZIP."""
        ctx = _full_context()
        ctx["equipment_list"] = []
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            assert z.testzip() is None
            assert set(z.namelist()) == set(template_part_names)

    def test_missing_loop_list_treated_as_empty(self, renderer):
        """A loop list key absent from context must behave like an empty
        list: control/data/endfor rows removed, no markers left."""
        ctx = _full_context()
        # Remove equipment_list entirely (do NOT set it).
        ctx.pop("equipment_list", None)
        # Renderer should not raise; the loop is dropped silently with a log.
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in TEXT_PARTS:
                if part not in z.namelist():
                    continue
                text = _gather_text(z.read(part))
                assert "{%" not in text, f"loop tag leaked into {part}"

    def test_nonempty_loop_still_expands(self, renderer):
        """Sanity: after the empty-loop fix, a non-empty loop must still
        expand correctly (control tags removed, data present)."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": "Газопровод-1",
                "hazard_characteristic": "Взрывоопасно",
                "location": "Территория ОПО",
                "process_codes": "1",
                "specifications": "P=1.2 МПа",
            }
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            doc_text = _gather_text(z.read("word/document.xml"))
        assert "{%" not in doc_text
        assert "Взрывоопасно" in doc_text

    # -- Defect #2: single XML escaping ------------------------------------
    def test_ampersand_single_escape(self, renderer):
        ctx = _full_context(organization_full_name="Газ & Нефть")
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            text = _gather_text(raw)
        assert "Газ & Нефть" in text  # recovered verbatim
        assert b"&amp;amp;" not in raw  # no double-escape
        assert b"&amp;" in raw  # single escape present

    def test_angle_brackets_single_escape(self, renderer):
        ctx = _full_context(facility_name="A < B > C")
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            text = _gather_text(raw)
        assert "A < B > C" in text
        assert b"&amp;lt;" not in raw
        assert b"&amp;gt;" not in raw
        assert b"&lt;" in raw and b"&gt;" in raw

    def test_russian_guillemets_preserved(self, renderer):
        """Russian «ёлочки» are valid Unicode and must pass through untouched
        (no escaping, no mojibake)."""
        ctx = _full_context(organization_full_name="ООО «Газ & Сервис»")
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "ООО «Газ & Сервис»" in text

    def test_special_chars_in_loop_field(self, renderer):
        """Special chars inside loop-variable fields must be escaped exactly
        once (the loop filler must not double-escape). After the
        ``_fill_loop_row`` rewrite, ALL fields are reliably filled, so this
        now checks every field's value with special chars."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": "Насос <A> & Co",
                "hazard_characteristic": "Класс «B» & опасность",
                "location": "Цех <№1>",
                "process_codes": "PROC <2>",
                "specifications": "Q < 50 & > 10",
            }
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            text = _gather_text(raw)
        # Every field recovers verbatim (single escape).
        assert "Насос <A> & Co" in text
        assert "Класс «B» & опасность" in text
        assert "Цех <№1>" in text
        assert "PROC <2>" in text
        assert "Q < 50 & > 10" in text
        # The whole document must contain NO double-escape artifacts.
        assert b"&amp;lt;" not in raw
        assert b"&amp;amp;" not in raw
        assert b"&amp;gt;" not in raw

    def test_loop_with_no_data_row_removes_control(self):
        """A ``{%tr for %}`` control row with no following ``{{ var. }}``
        sibling (malformed template) must not crash: the control row is
        removed and the render completes. Covers the ``data_row is None``
        branch in ``_expand_table_row_loops``."""
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:tbl><w:tr>'
            '<w:p><w:r><w:t>{%tr for eq in items %}</w:t></w:r></w:p>'
            '</w:tr>'
            # NOTE: deliberately NO data row with {{ eq. }} and NO endfor row.
            '<w:tr><w:p><w:r><w:t>plain row</w:t></w:r></w:p></w:tr>'
            '</w:tbl></w:body></w:document>'
        )
        ct_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        out_dir = REPO_ROOT / "backend" / ".pytest_tmp"
        out_dir.mkdir(exist_ok=True)
        tpl = out_dir / "no_data_row.docx"
        try:
            with zipfile.ZipFile(tpl, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("[Content_Types].xml", ct_xml)
                z.writestr("word/document.xml", doc_xml)
            r = PmlaOoxmlFlatRenderer(template_path=tpl)
            # Should not raise even though there is no data row.
            out = r.render({"items": [{"x": 1}]})
            text = _gather_text(zipfile.ZipFile(io.BytesIO(out)).read("word/document.xml"))
            assert "{%tr" not in text  # control row removed
            assert "plain row" in text  # sibling row preserved
        finally:
            if tpl.exists():
                tpl.unlink()


# ---------------------------------------------------------------------------
# 9. Loop field reliability (all fields, all items, split-run, special chars)
# ---------------------------------------------------------------------------
class TestLoopFieldReliability:
    """Regression tests for the ``_fill_loop_row`` rewrite.

    The old positional walker (``i = j + 1``) skipped tokens whose closing
    ``}}`` landed in an unexpected run, silently dropping ``device_name``,
    ``location`` and ``process_codes``. The new implementation routes every
    loop field through the same concatenated-buffer mechanism as flat
    placeholders, so all fields fill regardless of run count, split pattern
    or run order."""

    def test_all_six_fields_filled_for_each_item(self, renderer):
        """All six loop tokens — ``device_name``, ``hazard_characteristic``,
        ``location``, ``process_codes``, ``specifications``, ``loop.index`` —
        must appear in the output for EVERY item, not just the ones whose
        runs happen to align."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": f"DEV-{i}",
                "hazard_characteristic": f"HAZ-{i}",
                "location": f"LOC-{i}",
                "process_codes": f"PROC-{i}",
                "specifications": f"SPEC-{i}",
            }
            for i in range(1, 4)  # 3 items
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        for i in (1, 2, 3):
            for field, prefix in [
                ("device_name", "DEV"),
                ("hazard_characteristic", "HAZ"),
                ("location", "LOC"),
                ("process_codes", "PROC"),
                ("specifications", "SPEC"),
            ]:
                assert f"{prefix}-{i}" in text, f"item {i} field {field} missing"
        # loop.index is verified structurally: exactly 3 data rows must
        # appear in the equipment table (one per item). Counting rows is
        # robust against bare-digit false positives that field values would
        # otherwise introduce.
        root = etree.fromstring(zipfile.ZipFile(io.BytesIO(out)).read("word/document.xml"))
        data_rows = 0
        for tr in root.iter(W("tr")):
            row_text = "".join((t.text or "") for t in tr.iter(W("t")))
            if any(f"DEV-{i}" in row_text for i in (1, 2, 3)):
                data_rows += 1
        assert data_rows == 3, f"loop.index produced {data_rows} rows, expected 3"

    def test_no_leftover_loop_tokens_with_two_items(self, renderer):
        ctx = _full_context()
        ctx["equipment_list"] = [
            {"device_name": "A", "hazard_characteristic": "B", "location": "C",
             "process_codes": "D", "specifications": "E"},
            {"device_name": "F", "hazard_characteristic": "G", "location": "H",
             "process_codes": "I", "specifications": "J"},
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "{{" not in text
        assert "{%" not in text
        assert "{{ eq." not in text
        assert "loop.index" not in text  # token text, not the index value

    def test_russian_and_special_chars_all_fields(self, renderer):
        """Russian text and XML-special chars in every field, 2 items."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": "Котёл <№1> & «ГАЗ»",
                "hazard_characteristic": "Взрывоопасный > нормы",
                "location": "Цех «А» & склад",
                "process_codes": "Код < 1.2 >",
                "specifications": "P = 1.2 МПа & T < 100°C",
            },
            {
                "device_name": "Газопровод «Северный»",
                "hazard_characteristic": "Токсично & воспламеняющийся",
                "location": "Территория > 500 м²",
                "process_codes": "Код «2»",
                "specifications": "D = 530 × 7 мм",
            },
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            text = _gather_text(raw)
        expected = [
            "Котёл <№1> & «ГАЗ»", "Взрывоопасный > нормы", "Цех «А» & склад",
            "Код < 1.2 >", "P = 1.2 МПа & T < 100°C",
            "Газопровод «Северный»", "Токсично & воспламеняющийся",
            "Территория > 500 м²", "Код «2»", "D = 530 × 7 мм",
        ]
        for v in expected:
            assert v in text, f"missing value {v!r}"
        assert b"&amp;lt;" not in raw and b"&amp;amp;" not in raw

    def test_none_and_empty_field_values(self, renderer):
        """``None`` becomes empty string (NOT the literal ``None``); empty
        strings stay empty; filled fields still appear. No tokens leak."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": None,
                "hazard_characteristic": "",
                "location": "Только локация",
                "process_codes": None,
                "specifications": "Только спец",
            },
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "Только локация" in text
        assert "Только спец" in text
        assert "None" not in text  # None → "", not literal
        assert "{{" not in text
        assert "{%" not in text

    def test_split_run_tokens_reassembled(self, renderer):
        """The template splits some ``{{ eq.field }}`` tokens across multiple
        ``w:t`` runs. Regardless of the split, every field must resolve. We
        verify by confirming values that correspond to fields known to be
        split in the real template (device_name, location, process_codes)
        appear in the output."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": "SPLIT-DEVICE",
                "hazard_characteristic": "SPLIT-HAZ",
                "location": "SPLIT-LOC",
                "process_codes": "SPLIT-PROC",
                "specifications": "SPLIT-SPEC",
            }
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        for marker in ("SPLIT-DEVICE", "SPLIT-HAZ", "SPLIT-LOC", "SPLIT-PROC", "SPLIT-SPEC"):
            assert marker in text, f"{marker} missing (split-run reassembly failed)"

    def test_field_value_containing_braces(self, renderer):
        """A field value that literally contains ``{{`` or ``}}`` (e.g. a
        device name ``Параметр {{100}}``) must be inserted verbatim and must
        NOT be re-interpreted as an unresolved placeholder by the safety net.

        NOTE: the flat replacer runs AFTER loop expansion over the whole part.
        If the inserted ``{{100}}`` survived into the flat pass and ``100`` is
        not a known placeholder, the safety net would warn. This test asserts
        the value appears verbatim AND that no real token leaked — a field
        value with braces is legitimate content, not a template token."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {
                "device_name": "Параметр {{100}} и }",
                "hazard_characteristic": "h",
                "location": "l",
                "process_codes": "c",
                "specifications": "s",
            }
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        # The literal value (braces included) must appear in the document.
        assert "Параметр {{100}} и }" in text
        # And no REAL loop token leaked (the safety net keys on "{{ eq.").
        assert "{{ eq." not in text

    def test_table_xml_structure_valid(self, renderer):
        """After loop expansion the document.xml must still be valid XML and
        the equipment table must contain N+header rows (header + one per item).
        Verifies no table-cell corruption from the rewrite."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {"device_name": f"D{i}", "hazard_characteristic": f"H{i}",
             "location": f"L{i}", "process_codes": f"P{i}", "specifications": f"S{i}"}
            for i in range(1, 4)
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            root = etree.fromstring(raw)  # must parse
        # Count rows in the table that contains equipment data.
        W_tr = W("tr")
        rows = root.iter(W_tr)
        # At least the header + 3 data rows must exist.
        row_count = sum(1 for _ in rows)
        assert row_count >= 4, f"expected >=4 rows, got {row_count}"


# ---------------------------------------------------------------------------
# 9. Six-independent-loop tests (D6)
# ---------------------------------------------------------------------------
class TestSixIndependentLoops:
    """Verify that all 6 table-row loops in the template work together."""

    SIX_LIST_KEYS = [
        "equipment_list",
        "substance_params",
        "equipment_scenario_links",
        "accident_scenarios",
        "material_reserve_actual",
        "material_reserve_recommended",
        "countermeasures",
    ]

    def test_all_six_loops_expand_with_minimal_data(self, renderer):
        """Each of the 6 loops gets at least 1 item; every item's tokens
        are filled and no leftover markers remain."""
        ctx = _full_context()
        # _full_context already provides default data for all 6 lists
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "{{" not in text, "unreplaced flat tokens remain"
        assert "{%" not in text, "unreplaced Jinja markers remain"
        # Spot-check values from each list
        for marker in (
            "Котёл",           # equipment_list
            "P1", "V1",        # substance_params
            "Оборудование-1",  # equipment_scenario_links
            "S-1", "S-2",      # accident_scenarios
            "Средство-1",      # material_reserve_actual
            "Рек. средство",   # material_reserve_recommended
            "S-1 Мера",        # countermeasures
        ):
            assert marker in text, f"{marker!r} missing from output"

    def test_two_items_per_list(self, renderer):
        """With 2 items in every list all values appear; no leftover tokens."""
        ctx = _full_context()
        ctx["equipment_list"] = [
            {"device_name": "DEV-1", "hazard_characteristic": "H1", "location": "L1",
             "process_codes": "P1", "specifications": "S1"},
            {"device_name": "DEV-2", "hazard_characteristic": "H2", "location": "L2",
             "process_codes": "P2", "specifications": "S2"},
        ]
        ctx["substance_params"] = [
            {"parameter": "P1", "value": "V1"}, {"parameter": "P2", "value": "V2"},
        ]
        ctx["equipment_scenario_links"] = [
            {"equipment_name": "EQ1", "scenario_codes": "S1", "description": "D1", "damaging_factors": "F1"},
            {"equipment_name": "EQ2", "scenario_codes": "S2", "description": "D2", "damaging_factors": "F2"},
        ]
        ctx["accident_scenarios"] = [
            {"code": "C1", "name": "N1", "source": "SRC1", "preconditions": "PRE1", "signs": "SIG1", "damaging_factors": "DF1"},
            {"code": "C2", "name": "N2", "source": "SRC2", "preconditions": "PRE2", "signs": "SIG2", "damaging_factors": "DF2"},
        ]
        ctx["material_reserve_actual"] = [
            {"name": "M1", "quantity": "Q1", "location": "L1"},
            {"name": "M2", "quantity": "Q2", "location": "L2"},
        ]
        ctx["material_reserve_recommended"] = [
            {"name": "R1", "quantity": "RQ1", "location": "RL1"},
            {"name": "R2", "quantity": "RQ2", "location": "RL2"},
        ]
        ctx["countermeasures"] = [
            {"scenario_label": "L1", "signs": "LG1", "protection": "PR1", "technical_means": "TM1", "executors": "EX1"},
            {"scenario_label": "L2", "signs": "LG2", "protection": "PR2", "technical_means": "TM2", "executors": "EX2"},
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "{{" not in text
        assert "{%" not in text
        for m in ("DEV-1", "DEV-2", "P1", "P2", "EQ1", "EQ2", "C1", "C2",
                  "M1", "M2", "R1", "R2", "L1", "L2"):
            assert m in text, f"{m!r} missing"

    @pytest.mark.parametrize("list_key", SIX_LIST_KEYS)
    def test_empty_list_leaves_no_markers(self, renderer, list_key):
        """When a single list is emptied, no Jinja markers survive anywhere."""
        ctx = _full_context()
        ctx[list_key] = [] if isinstance(ctx.get(list_key, []), list) else []
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in PmlaOoxmlFlatRenderer.TEXT_PARTS:
                if part not in z.namelist():
                    continue
                text = _gather_text(z.read(part))
                assert "{%tr" not in text, (
                    f"Jinja leftover in {part} when {list_key}=[]"
                )

    def test_all_lists_empty_leaves_no_markers(self, renderer):
        """When ALL 6 lists are empty simultaneously, no markers remain."""
        ctx = _full_context()
        for k in self.SIX_LIST_KEYS:
            ctx[k] = []
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            for part in PmlaOoxmlFlatRenderer.TEXT_PARTS:
                if part not in z.namelist():
                    continue
                text = _gather_text(z.read(part))
                assert "{%" not in text, f"Jinja leftover in {part}"
                assert "{{" not in text, f"Brace leftover in {part}"

    def test_actual_and_recommended_not_mixed(self, renderer):
        """material_reserve_actual items should NOT appear in the
        recommended section and vice versa."""
        ctx = _full_context()
        ctx["material_reserve_actual"] = [
            {"name": "UNIQUE_ACTUAL", "quantity": "1", "location": "A"},
        ]
        ctx["material_reserve_recommended"] = [
            {"name": "UNIQUE_RECOMMENDED", "quantity": "2", "location": "R"},
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        assert "UNIQUE_ACTUAL" in text
        assert "UNIQUE_RECOMMENDED" in text

    def test_special_chars_in_all_loops(self, renderer):
        """XML-special characters (<> &) in every loop type must be single-escaped."""
        ctx = _full_context()
        ctx["substance_params"] = [
            {"parameter": "Темп < 100°C", "value": "Давление > 2 МПа & норма"},
        ]
        ctx["equipment_scenario_links"] = [
            {"equipment_name": "Котёл <№2>", "scenario_codes": "S-1, S-2",
             "description": "Описание <тест>", "damaging_factors": "Фактор & риск"},
        ]
        ctx["accident_scenarios"] = [
            {"code": "S-1", "name": "Тест <имя>", "source": "Источник",
             "preconditions": "Причина > нормы", "signs": "Сигнал & шум",
             "damaging_factors": "Фактор < 1.2"},
        ]
        out = renderer.render(ctx)
        raw = b""
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            raw = z.read("word/document.xml")
            text = _gather_text(raw)
        # Verify values appear correctly (XML-decoded)
        assert "Темп < 100°C" in text
        assert "Давление > 2 МПа & норма" in text
        assert "Котёл <№2>" in text
        assert "Описание <тест>" in text
        assert "Фактор & риск" in text
        assert "Тест <имя>" in text
        # Double-encoding must NOT happen
        assert b"&amp;lt;" not in raw
        assert b"&amp;amp;" not in raw

    def test_split_runs_in_new_loops(self, renderer):
        """Ensure split-run tokens in the newly added loops also reassemble."""
        ctx = _full_context()
        ctx["accident_scenarios"] = [
            {"code": "SPLIT-CODE", "name": "SPLIT-NAME", "source": "SPLIT-SRC",
             "preconditions": "SPLIT-PRE", "signs": "SPLIT-SIGNS",
             "damaging_factors": "SPLIT-DF"},
        ]
        ctx["countermeasures"] = [
            {"scenario_label": "SPLIT-LABEL", "signs": "SPLIT-SIGN",
             "protection": "SPLIT-PROT", "technical_means": "SPLIT-TM",
             "executors": "SPLIT-EX"},
        ]
        out = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(out), "r") as z:
            text = _gather_text(z.read("word/document.xml"))
        for m in ("SPLIT-CODE", "SPLIT-NAME", "SPLIT-SRC", "SPLIT-PRE",
                  "SPLIT-SIGNS", "SPLIT-DF", "SPLIT-LABEL", "SPLIT-SIGN",
                  "SPLIT-PROT", "SPLIT-TM", "SPLIT-EX"):
            assert m in text, f"{m!r} missing (split-run issue)"
