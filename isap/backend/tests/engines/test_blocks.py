"""Tests for block serialization/deserialization."""
import json

from src.application.engines.blocks import (
    HeadingBlock, ParagraphBlock, TableBlock, ImageBlock,
    serialize_blocks, deserialize_blocks,
)
from src.application.services.enhanced_generator import (
    _serialize_sections, _deserialize_sections,
)


class TestSerializeBlocks:
    def test_heading_block(self):
        blocks = [HeadingBlock(text="Заголовок", level=1, center=True)]
        result = serialize_blocks(blocks)
        assert len(result) == 1
        assert result[0]["__type__"] == "heading"
        assert result[0]["text"] == "Заголовок"
        assert result[0]["level"] == 1
        assert result[0]["center"] is True

    def test_paragraph_block(self):
        blocks = [ParagraphBlock(text="Текст", bold=True)]
        result = serialize_blocks(blocks)
        assert result[0]["__type__"] == "paragraph"
        assert result[0]["text"] == "Текст"
        assert result[0]["bold"] is True

    def test_table_block(self):
        blocks = [TableBlock(
            headers=["A", "B"],
            rows=[["1", "2"], ["3", "4"]],
            caption="Таблица 1",
        )]
        result = serialize_blocks(blocks)
        assert result[0]["__type__"] == "table"
        assert result[0]["headers"] == ["A", "B"]
        assert result[0]["rows"] == [["1", "2"], ["3", "4"]]
        assert result[0]["caption"] == "Таблица 1"

    def test_image_block(self):
        blocks = [ImageBlock(path="/img.png", width_cm=10.0, caption="Рисунок")]
        result = serialize_blocks(blocks)
        assert result[0]["__type__"] == "image"
        assert result[0]["path"] == "/img.png"

    def test_mixed_blocks(self):
        blocks = [
            HeadingBlock(text="Заголовок"),
            ParagraphBlock(text="Абзац"),
            TableBlock(headers=["X"], rows=[["Y"]]),
        ]
        result = serialize_blocks(blocks)
        assert len(result) == 3
        assert result[0]["__type__"] == "heading"
        assert result[1]["__type__"] == "paragraph"
        assert result[2]["__type__"] == "table"

    def test_empty_list(self):
        assert serialize_blocks([]) == []


class TestDeserializeBlocks:
    def test_heading_block(self):
        data = [{"__type__": "heading", "text": "Заголовок", "level": 2, "center": False}]
        result = deserialize_blocks(data)
        assert len(result) == 1
        assert isinstance(result[0], HeadingBlock)
        assert result[0].text == "Заголовок"
        assert result[0].level == 2

    def test_table_block(self):
        data = [{"__type__": "table", "headers": ["A"], "rows": [["B"]], "caption": None}]
        result = deserialize_blocks(data)
        assert isinstance(result[0], TableBlock)
        assert result[0].headers == ["A"]

    def test_unknown_type_skipped(self):
        data = [{"__type__": "unknown"}, {"__type__": "paragraph", "text": "OK"}]
        result = deserialize_blocks(data)
        assert len(result) == 1
        assert isinstance(result[0], ParagraphBlock)

    def test_roundtrip(self):
        original = [
            HeadingBlock(text="H", level=1, center=True),
            ParagraphBlock(text="P", bold=False),
            TableBlock(headers=["A", "B"], rows=[["1", "2"]], caption="T"),
        ]
        serialized = serialize_blocks(original)
        deserialized = deserialize_blocks(serialized)
        assert len(deserialized) == 3
        assert isinstance(deserialized[0], HeadingBlock)
        assert deserialized[0].text == "H"
        assert isinstance(deserialized[2], TableBlock)
        assert deserialized[2].headers == ["A", "B"]


class TestSerializeSections:
    def test_text_section(self):
        sections = {"Раздел 1": "Текст"}
        result = _serialize_sections(sections)
        assert result["Раздел 1"]["__blocks__"] is False
        assert result["Раздел 1"]["data"] == "Текст"

    def test_blocks_section(self):
        sections = {"Раздел 2": [ParagraphBlock(text="Абзац")]}
        result = _serialize_sections(sections)
        assert result["Раздел 2"]["__blocks__"] is True
        assert result["Раздел 2"]["data"][0]["__type__"] == "paragraph"

    def test_json_serializable(self):
        sections = {"Раздел": [TableBlock(headers=["A"], rows=[["B"]])]}
        serialized = _serialize_sections(sections)
        # Должно сериализоваться в JSON без ошибок
        json_str = json.dumps(serialized)
        assert len(json_str) > 0


class TestDeserializeSections:
    def test_text_section(self):
        data = {"Раздел 1": {"__blocks__": False, "data": "Текст"}}
        result = _deserialize_sections(data)
        assert result["Раздел 1"] == "Текст"

    def test_blocks_section(self):
        data = {"Раздел 2": {"__blocks__": True, "data": [
            {"__type__": "paragraph", "text": "Абзац", "bold": False}
        ]}}
        result = _deserialize_sections(data)
        assert isinstance(result["Раздел 2"], list)
        assert isinstance(result["Раздел 2"][0], ParagraphBlock)

    def test_backward_compat_old_format(self):
        # Старый формат: просто строка
        data = {"Раздел": "Текст"}
        result = _deserialize_sections(data)
        assert result["Раздел"] == "Текст"

    def test_roundtrip(self):
        original = {
            "Текстовый": "Просто строка",
            "Блочный": [HeadingBlock(text="H"), TableBlock(headers=["A"], rows=[["B"]])],
        }
        serialized = _serialize_sections(original)
        deserialized = _deserialize_sections(serialized)
        assert deserialized["Текстовый"] == "Просто строка"
        assert isinstance(deserialized["Блочный"], list)
        assert isinstance(deserialized["Блочный"][0], HeadingBlock)
