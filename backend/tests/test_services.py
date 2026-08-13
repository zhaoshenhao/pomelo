import os
import tempfile

from openpyxl import Workbook

from app.services.document_parser import (
    convert_to_markdown,
    parse_text,
    parse_xlsx,
)
from app.services.file_service import sanitize_filename, save_library_file


class TestDocumentParser:
    def test_parse_text(self):
        filepath = os.path.join(tempfile.gettempdir(), "test_parse.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Hello World\nLine 2")
        result = parse_text(filepath)
        os.unlink(filepath)
        assert result == "Hello World\nLine 2"

    def test_convert_txt_to_md(self):
        filepath = os.path.join(tempfile.gettempdir(), "test_convert.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Test content")
        result = convert_to_markdown(filepath)
        os.unlink(filepath)
        assert "# Test content" in result

    def test_parse_xlsx(self):
        filepath = os.path.join(tempfile.gettempdir(), "test_excel.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Name", "Age"])
        ws.append(["Alice", "30"])
        ws.append(["Bob", "25"])
        wb.save(filepath)
        wb.close()

        result = parse_xlsx(filepath)
        os.unlink(filepath)
        assert "## Sheet1" in result
        assert "| Name | Age |" in result
        assert "| Alice | 30 |" in result
        assert "| Bob | 25 |" in result


class TestFileService:
    def test_save_library_file(self):
        test_dir = "test_lib_dir"
        filepath = save_library_file(test_dir, "hello.md", "# Hello")
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == "# Hello"
        os.unlink(filepath)
        os.rmdir(os.path.dirname(filepath))

    def test_sanitize_filename_rejects_traversal(self):
        for bad in ("..", ".", "", "../evil", "evil/../x", "a\\b", "/etc/passwd"):
            try:
                sanitize_filename(bad)
                assert False, f"should reject: {bad!r}"
            except ValueError:
                pass
        assert sanitize_filename("normal.md") == "normal.md"
        assert sanitize_filename("  spaced.md  ") == "spaced.md"
