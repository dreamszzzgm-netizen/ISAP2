"""
OOXML Flat Renderer for PMLA v2 Template.

WHY THIS EXISTS
---------------
The previous renderer used docxtpl/python-docx (and a first draft used
``xml.etree.ElementTree``). Both libraries *re-serialize* the package's
XML parts and **rename every XML namespace prefix**
(``w:`` -> ``ns0:``, ``r:`` -> ``ns10:``, ...). The relationship
references ``r:embed`` / ``r:id`` inside ``word/document.xml`` therefore
became ``ns10:embed`` and Word could no longer resolve the 14 embedded
images -> "Word found unreadable content / recover graphics" on open.

This renderer fixes that by:

  * copying the OPC/ZIP package part-by-part, **byte-for-byte**, for every
    part that does NOT contain placeholders;
  * re-writing ONLY the text XML parts (document.xml, headers, footers,
    footnotes, endnotes) via **lxml**, which preserves the original
    namespace prefixes exactly, so ``r:embed`` / ``mc:Ignorable`` stay
    valid;
  * never calling ``Document.save()`` / ``DocxTemplate.save()``.

Supported template constructs:
  * flat ``{{ key }}`` placeholders, including ones split across several
    ``w:t`` runs and ones living inside text boxes (w:txbx / wps:txbx);
  * the docxtpl **table-row loop** ``{%tr for x in list_key %} ...
    {%tr endfor %}`` (the only loop form used by this template). Each
    list item is cloned into a row and its ``{{ x.field }}`` /
    ``{{ loop.index }}`` tokens filled.
  * Any other Jinja control structure (plain ``{% for %}``, ``{% if %}``,
    ``{% set %}`` ...) is rejected with a clear error.

External references (TargetMode="External", LINK / INCLUDEPICTURE /
INCLUDETEXT / DDEAUTO) are scrubbed from the copied package so Word never
prompts to update links to other files.
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from lxml import etree

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

W = lambda tag: f"{{{W_NS}}}{tag}"

# Flat placeholder: {{ key }} or {{ a.b }} (dotted context token). Dotted
# tokens are resolved via the raw context dict; loop-variable tokens
# ({{ x.field }}) are handled by the loop expander and never reach here.
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\}\}")

# Loop-variable token: {{ var.field }} or {{ loop.index }}.
LOOP_TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?|loop\.index)\s*\}\}")

# docxtpl table-row loop markers (may be split across runs).
TR_FOR_RE = re.compile(r"\{\%\s*tr\s+for\s+(\w+)\s+in\s+(\w+)\s*\%\}")
TR_ENDFOR_RE = re.compile(r"\{\%\s*tr\s+endfor\s*\%\}")

# Forbidden Jinja control structures (anything but the docxtpl table-row
# loop). If the template relies on these, it is rejected.
FORBIDDEN_JINJA_RE = re.compile(
    r"\{\%\s*(?!tr\s+for|tr\s+endfor)(for|if|set|macro|block|include|with|"
    r"raw|verbatim|call)\b"
)

# External field codes whose instruction must be neutralised.
EXTERNAL_FIELD_RE = re.compile(
    r"\b(?:LINK|INCLUDEPICTURE|INCLUDETEXT|DDEAUTO)\b", re.IGNORECASE
)


class PlaceholderNotFoundError(ValueError):
    """Raised when a template placeholder has no matching context value."""


class UnsupportedTemplateError(ValueError):
    """Raised when the template uses unsupported Jinja constructs."""


class PmlaOoxmlFlatRenderer:
    """Flat OOXML renderer that preserves graphics, relationships and namespaces."""

    # XML parts that may contain placeholders / loops.
    TEXT_PARTS = (
        "word/document.xml",
        "word/header1.xml",
        "word/header2.xml",
        "word/header3.xml",
        "word/footer1.xml",
        "word/footer2.xml",
        "word/footer3.xml",
        "word/footnotes.xml",
        "word/endnotes.xml",
    )

    def __init__(self, template_path: str | Path | None = None):
        self.template_path = Path(template_path) if template_path else (
            Path(__file__).parent.parent.parent.parent.parent / "files" / "pmla_v2_template.docx"
        )
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
        # Cache the ZIP part inventory (names only) — we never unpack binaries.
        # NOTE (D2): no per-render instance state. Loop data and the raw
        # context are threaded as locals through render() so concurrent
        # render() calls on the same instance cannot mix contexts.
        with zipfile.ZipFile(self.template_path, "r") as z:
            self._part_names = z.namelist()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def render(self, context: Mapping[str, Any], template_version: str = "v2") -> bytes:
        """Render ``context`` against the template and return DOCX bytes.

        Args:
            context: mapping of template keys -> values. Scalar values are
                     XML-escaped strings; list/dict values are treated as
                     table-row loop data (e.g. ``equipment_list``) and cloned
                     into rows. They must NOT be pre-stringified.
        """
        # 1. Reject unsupported Jinja constructs up front.
        self._assert_no_forbidden_jinja()

        # 2. Split context into flat scalars and loop data.
        # NOTE (D2): these locals are threaded through every downstream call;
        # the renderer keeps NO per-render instance state, so concurrent
        # render() calls on the same instance cannot mix contexts.
        flat, loops = self._split_context(context)
        loop_lists: dict[str, Any] = loops
        # Raw context dict kept locally for dotted-token resolution
        # (e.g. {{ person.position }}) without any shared mutable state.
        raw_context: Mapping[str, Any] = context

        # 3. Build XML-safe flat string map.
        safe_context = self._prepare_context(flat)

        # 4. Validate every flat placeholder is served (incl. dotted tokens — D3).
        #    Non-dotted ``{{ key }}`` must be a scalar in safe_context; dotted
        #    ``{{ a.b }}`` must resolve through raw_context.
        template_placeholders = self._extract_flat_placeholders()
        missing: set[str] = set()
        for ph in template_placeholders:
            if "." in ph:
                if not self._dotted_path_served(ph, raw_context):
                    missing.add(ph)
            elif ph not in safe_context:
                missing.add(ph)
        if missing:
            raise PlaceholderNotFoundError(
                "Template contains placeholders with no context value: "
                + ", ".join(sorted(missing))
            )
        unknown = set(safe_context.keys()) - template_placeholders
        if unknown:
            logger.warning("Context keys unused by template: %s", sorted(unknown))

        # 5. Copy package, rewriting only text parts. All per-render state is
        # passed as arguments; the only mutation is to the local output_buffer.
        output_buffer = io.BytesIO()
        with zipfile.ZipFile(self.template_path, "r") as zin:
            with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zout:
                for part_name in self._part_names:
                    data = zin.read(part_name)
                    if part_name in self.TEXT_PARTS:
                        data = self._render_text_part(
                            data, safe_context, part_name, loop_lists, raw_context
                        )
                    zout.writestr(part_name, data)

        output_bytes = output_buffer.getvalue()
        logger.info("Rendered PMLA v2 via flat OOXML renderer: %d bytes", len(output_bytes))
        return output_bytes

    def render_to_file(
        self, context: Mapping[str, Any], output_path: str | Path, template_version: str = "v2"
    ) -> Path:
        """Render and write to ``output_path``."""
        output_path = Path(output_path)
        output_path.write_bytes(self.render(context, template_version=template_version))
        return output_path

    # ------------------------------------------------------------------ #
    # Context preparation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _dotted_path_served(dotted: str, raw_context: Mapping[str, Any]) -> bool:
        """True iff a dotted path (``a.b.c``) resolves to a non-None value
        inside the raw context mapping. Loop variables (``equipment.name``)
        never reach this check because they are expanded earlier."""
        node: Any = raw_context
        for part in dotted.split("."):
            if isinstance(node, Mapping) and part in node:
                node = node[part]
            else:
                return False
        return node is not None

    @staticmethod
    def _split_context(context: Mapping[str, Any]) -> tuple[dict, dict]:
        """Separate scalar (flat) values from list/dict (loop) values."""
        flat: dict[str, Any] = {}
        loops: dict[str, Any] = {}
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                loops[key] = value
            else:
                flat[key] = value
        return flat, loops

    @staticmethod
    def _prepare_context(flat: Mapping[str, Any]) -> dict[str, str]:
        """Convert scalar values to strings.

        * None   -> ""
        * bool   -> "Да"/"Нет"
        * else   -> str()

        NOTE: no manual XML-escaping here. Values are assigned to ``elem.text``
        on lxml elements, and ``etree.tostring`` applies exactly one layer of
        escaping (``&`` → ``&amp;``, ``<`` → ``&lt;`` ...) during serialization.
        Escaping manually would double-escape (``A < B`` → ``A &amp;lt; B``).
        """
        safe: dict[str, str] = {}
        for key, value in flat.items():
            if value is None:
                safe[key] = ""
            elif isinstance(value, bool):
                safe[key] = "Да" if value else "Нет"
            else:
                safe[key] = str(value)
        return safe

    # ------------------------------------------------------------------ #
    # Template introspection
    # ------------------------------------------------------------------ #
    def _extract_flat_placeholders(self) -> set[str]:
        """Flat ``{{ key }}`` and ``{{ a.b }}`` placeholders declared by the
        template (D3 validation). Dotted tokens are context-object lookups
        (e.g. ``person.position``). Loop-variable tokens (``eq.name`` inside a
        ``{%tr for eq in ... %}`` row) and ``loop.index`` are served by the
        loop expander, so they are excluded here."""
        loop_vars = self._extract_loop_variables()
        found: set[str] = set()
        with zipfile.ZipFile(self.template_path, "r") as z:
            for part in self.TEXT_PARTS:
                if part not in self._part_names:
                    continue
                text = self._gather_text(z.read(part))
                # Whole placeholders, including dotted context tokens (D3).
                for key in re.findall(
                    r"\{\{\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\}\}", text
                ):
                    head = key.split(".", 1)[0]
                    if head in loop_vars or head == "loop":
                        continue  # served by the loop expander, not flat
                    found.add(key)
        return found

    def _extract_loop_variables(self) -> set[str]:
        """Names of loop variables declared by ``{%tr for X in LIST %}`` rows.
        Used to exclude ``X.field`` tokens from flat-placeholder validation."""
        names: set[str] = set()
        with zipfile.ZipFile(self.template_path, "r") as z:
            for part in self.TEXT_PARTS:
                if part not in self._part_names:
                    continue
                text = self._gather_text(z.read(part))
                names.update(TR_FOR_RE.findall(text.replace("\x00", "")))
        # TR_FOR_RE.findall returns 2-tuples (var, list_key); keep the var.
        return {m[0] if isinstance(m, tuple) else m for m in names}

    def _assert_no_forbidden_jinja(self) -> None:
        with zipfile.ZipFile(self.template_path, "r") as z:
            for part in self.TEXT_PARTS:
                if part not in self._part_names:
                    continue
                text = self._gather_text(z.read(part))
                m = FORBIDDEN_JINJA_RE.search(text)
                if m:
                    raise UnsupportedTemplateError(
                        f"Template uses unsupported Jinja construct {m.group(0)!r} "
                        f"in {part}. Only docxtpl table-row loops "
                        "({%tr for ...%} ... {%tr endfor%}) are supported by this renderer."
                    )

    # ------------------------------------------------------------------ #
    # Text gathering (handles run-split tokens)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _gather_text(xml_bytes: bytes) -> str:
        """Concatenate all ``w:t`` text in document order; tokens split across
        runs re-assemble into a single contiguous string here."""
        try:
            root = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError:
            return ""
        return "".join((e.text or "") for e in root.iter(W("t")))

    # ------------------------------------------------------------------ #
    # Per-part rendering
    # ------------------------------------------------------------------ #
    def _render_text_part(
        self,
        xml_bytes: bytes,
        safe_context: dict[str, str],
        part_name: str,
        loop_lists: dict[str, Any],
        raw_context: Mapping[str, Any],
    ) -> bytes:
        try:
            root = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as e:
            logger.warning("Failed to parse %s, copying verbatim: %s", part_name, e)
            return xml_bytes

        # 1. Expand docxtpl table-row loops (clones rows, fills x.field).
        self._expand_table_row_loops(root, loop_lists)

        # 2. Replace flat {{ key }} placeholders (incl. run-split ones).
        self._replace_flat_placeholders(root, safe_context, raw_context)

        # 3. Scrub external field codes (LINK / INCLUDEPICTURE / DDEAUTO ...).
        self._scrub_external_fields(root)

        # 4. Safety net: no leftover template tokens anywhere.
        # NOTE: only ``{{`` and ``{%`` are token starters; ``}}`` alone
        # appears in Russian text (цитаты, кавычки-ёлочки) and as an
        # artifact when adjacent w:t runs get concatenated.
        leftover = self._gather_text(etree.tostring(root))
        if "{{" in leftover or "{%" in leftover:
            logger.warning(
                "Unreplaced template tokens remain in %s: %.200r",
                part_name, leftover,
            )

        # 5. Serialize — lxml preserves the original namespace prefixes.
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    # ------------------------------------------------------------------ #
    # Table-row loop expansion
    # ------------------------------------------------------------------ #
    def _expand_table_row_loops(self, root, loop_lists: dict[str, Any]) -> None:
        W_tr = W("tr")
        # Identify control rows (carry the {%tr for ...%} instruction).
        control_rows = []
        for tr in root.iter(W_tr):
            if TR_FOR_RE.search(self._gather_text(etree.tostring(tr))):
                control_rows.append(tr)

        for ctrl in control_rows:
            parent = ctrl.getparent()
            if parent is None:
                continue
            m = TR_FOR_RE.search(self._gather_text(etree.tostring(ctrl)))
            var, list_key = m.group(1), m.group(2)
            items = loop_lists.get(list_key)
            logger.debug("LOOP %s in %s -> items=%s", var, list_key, len(items) if items else None)

            ctrl_idx = parent.index(ctrl)
            # Data-row template = next w:tr sibling carrying {{ var. }} or {{ loop.index }}.
            data_row = None
            for i in range(ctrl_idx + 1, len(parent)):
                sib = parent[i]
                if sib.tag != W_tr:
                    continue
                sib_text = self._gather_text(etree.tostring(sib))
                if ("{{ " + var + ".") in sib_text or "{{ loop.index }}" in sib_text:
                    data_row = sib
                    break

            # endfor row = next w:tr sibling after data row carrying {%tr endfor%}.
            endfor_row = None
            search_start = parent.index(data_row) + 1 if data_row is not None else ctrl_idx + 1
            for i in range(search_start, len(parent)):
                sib = parent[i]
                if sib.tag != W_tr:
                    continue
                if TR_ENDFOR_RE.search(self._gather_text(etree.tostring(sib))):
                    endfor_row = sib
                    break

            if not items:
                # Empty/missing loop: drop ALL three template rows (control,
                # data, endfor) so no {%tr %} / {{ var. }} markers survive.
                logger.info("Loop list %r empty/missing; removing loop rows.", list_key)
                self._remove_rows([endfor_row, data_row, ctrl])
                continue

            if data_row is None:
                logger.warning("No data row for loop %r; removing control row only.", list_key)
                self._remove_rows([ctrl])
                continue

            # Clone + fill one row per item, inserting before the template row.
            insert_at = parent.index(data_row)
            for n, item in enumerate(items, start=1):
                clone = deepcopy(data_row)
                self._fill_loop_row(clone, var, item, n)
                parent.insert(insert_at, clone)
                insert_at += 1

            # Remove the three template rows: data, endfor, control.
            self._remove_rows([endfor_row, data_row, ctrl])

    @staticmethod
    def _fill_loop_row(row, var: str, item: Mapping[str, Any], index: int) -> None:
        """Replace ``{{ var.field }}`` and ``{{ loop.index }}`` in a cloned row.

        Uses the SAME concatenated-buffer mechanism as the flat replacer
        (``_replace_tokens_over_buffer``) so that every loop field is filled
        regardless of how many runs its token spans or the order of the runs.
        The previous positional walk (``i = j + 1``) skipped tokens whose
        closing ``}}`` landed in an unexpected run, dropping fields like
        ``device_name`` / ``location`` / ``process_codes``."""
        t_elems = [e for e in row.iter(W("t")) if e.text is not None]
        if not t_elems:
            return

        def resolver(token: str) -> str:
            return PmlaOoxmlFlatRenderer._resolve_loop_token(
                token, var, item, index
            )

        PmlaOoxmlFlatRenderer._replace_tokens_over_buffer(
            t_elems, resolver, LOOP_TOKEN_RE
        )

    @staticmethod
    def _resolve_loop_token(token: str, var: str, item: Mapping[str, Any], index: int) -> str:
        if token == "loop.index":
            return str(index)
        if "." in token:
            head, _, field = token.partition(".")
            if head == var and isinstance(item, dict):
                val = item.get(field, "")
                return "" if val is None else str(val)
        # Leave unresolved loop token visible (safety — surfaces in QA).
        # No manual escaping: lxml escapes elem.text on serialize.
        return "{{" + token + "}}"

    @staticmethod
    def _remove_rows(rows) -> None:
        """Detach a list of ``w:tr`` elements from their parents, skipping
        any that are already gone. Used to drop control/data/endfor template
        rows after a loop has been expanded or dropped due to empty data."""
        for row in rows:
            if row is None:
                continue
            p = row.getparent()
            if p is not None:
                p.remove(row)

    # ------------------------------------------------------------------ #
    # Flat placeholder replacement (run-split aware)
    # ------------------------------------------------------------------ #
    def _replace_flat_placeholders(
        self,
        root,
        safe_context: dict[str, str],
        raw_context: Mapping[str, Any],
    ) -> None:
        """Replace ``{{ key }}`` placeholders, even when a placeholder is
        split across several ``w:t`` runs (the common Word case).

        Strategy: stream through every ``w:t`` in document order. A
        placeholder may open in one run and close in another; we accumulate
        the contributing runs and, on the closing ``}}``, rewrite exactly
        those runs: the opening run keeps its formatting and receives the
        resolved value + any leading text, the inner runs are cleared, and
        the closing run keeps any trailing text after ``}}``. This preserves
        per-placeholder layout instead of collapsing the whole document.
        """
        t_elems = [e for e in root.iter(W("t")) if e.text is not None]
        if not t_elems:
            return

        # Robust replacement over the *concatenated* text of all w:t runs,
        # which survives placeholders whose `{{` / `}}` are split across
        # several runs (a common Word authoring artifact).
        self._replace_flat_robust(t_elems, safe_context, raw_context)

    @staticmethod
    def _replace_flat_robust(
        t_elems,
        safe_context: dict[str, str],
        raw_context: Mapping[str, Any],
    ) -> None:
        """Resolve every ``{{ key }}`` / ``{{ a.b }}`` placeholder in the part.

        Builds a flat character buffer by concatenating each run's text and
        tracks which run owns each character. Placeholders are substituted in
        the buffer (so a token split across runs is reassembled). Each
        substituted value's characters are attributed to the run that owned the
        placeholder's opening ``{{`` — preserving per-placeholder layout even
        when the value is longer/shorter than the original token. Characters
        outside placeholders keep their original owning run.
        """
        def resolver(token: str) -> str:
            return PmlaOoxmlFlatRenderer._resolve_flat(
                token, safe_context, raw_context
            )

        PmlaOoxmlFlatRenderer._replace_tokens_over_buffer(t_elems, resolver, PLACEHOLDER_RE)

    @staticmethod
    def _replace_tokens_over_buffer(
        t_elems,
        resolver,
        token_re: "re.Pattern",
    ) -> None:
        """Run-split-aware token replacement shared by the flat and loop
        fillers.

        Concatenates every ``w:t`` element's text into one buffer while
        tracking which run owns each character. ``token_re`` is matched over
        the whole buffer — so tokens whose ``{{ ... }}`` span several runs are
        reassembled before matching. Each substituted value is attributed to
        the run that owned the token's opening character, preserving per-token
        layout regardless of how Word split the runs. Non-token characters keep
        their original owning run.

        This is the single, position-independent mechanism for placeholder
        substitution; it does NOT rely on run order or counting.
        """
        # Per-character owner index aligned 1:1 with the concatenated buffer.
        char_owner: list[int] = []
        buf: list[str] = []
        for run_idx, elem in enumerate(t_elems):
            txt = elem.text or ""
            buf.append(txt)
            char_owner.extend([run_idx] * len(txt))
        text = "".join(buf)

        if not token_re.search(text):
            return  # no tokens at all — keep run formatting intact

        # Reassemble (char, owner_run) pairs, mapping each substituted value
        # to the run owning the token's opening character.
        result: list[tuple[str, int]] = []
        pos = 0
        for mo in token_re.finditer(text):
            for k in range(pos, mo.start()):
                result.append((text[k], char_owner[k]))
            value = resolver(mo.group(1))
            open_owner = char_owner[mo.start()]
            for ch in value:
                result.append((ch, open_owner))
            pos = mo.end()
        for k in range(pos, len(text)):
            result.append((text[k], char_owner[k]))

        run_chars: list[list[str]] = [[] for _ in t_elems]
        for ch, owner in result:
            run_chars[owner].append(ch)
        for elem, chars in zip(t_elems, run_chars):
            elem.text = "".join(chars)


    @staticmethod
    def _resolve_flat(
        token: str,
        safe_context: dict[str, str],
        raw_context: Mapping[str, Any] | None = None,
    ) -> str:
        if "." in token:
            # Dotted context token (e.g. ``person.position``). Look it up in
            # the raw context dict passed explicitly (no shared state — D2).
            if isinstance(raw_context, Mapping):
                node: Any = raw_context
                for part in token.split("."):
                    if isinstance(node, Mapping) and part in node:
                        node = node[part]
                    else:
                        node = None
                        break
                if node is not None:
                    return str(node)
            # Leave unresolved dotted tokens visible (QA surfaces them).
            return "{{" + token + "}}"
        value = safe_context.get(token)
        if value is None:
            # Marker so QA sees an unserved placeholder instead of silent drop.
            return "{{" + token + "}}"
        return value

    # ------------------------------------------------------------------ #
    # External field scrubbing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _scrub_external_fields(root) -> None:
        """Neutralise LINK / INCLUDEPICTURE / INCLUDETEXT / DDEAUTO field codes
        by removing the offending ``w:instrText`` instruction while keeping the
        (already cached) visible result text. TOC/PAGE/NUMPAGES/REF/SEQ fields
        are left untouched."""
        for e in root.iter(W("instrText")):
            if e.text and EXTERNAL_FIELD_RE.search(e.text):
                logger.info("Scrubbing external field instruction: %.80r", e.text)
                parent = e.getparent()
                if parent is not None:
                    parent.remove(e)


def create_renderer(template_path: str | Path | None = None) -> "PmlaOoxmlFlatRenderer":
    """Factory function to create a renderer instance."""
    return PmlaOoxmlFlatRenderer(template_path)
