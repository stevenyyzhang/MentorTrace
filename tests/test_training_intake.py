"""Focused intake tests: source preservation, archive aliases and provenance."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("training_intake", ROOT / "scripts" / "training_intake.py")
intake = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = intake
spec.loader.exec_module(intake)


def annotated_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=500)
    annotations = []
    for subtype, author, contents in [("/Link", "", ""), ("/Popup", "", ""),
                                      ("/Text", "Unverified alias", "Clarify the input."),
                                      ("/Ink", "", "")]:
        obj = DictionaryObject({NameObject("/Type"): NameObject("/Annot"),
                                NameObject("/Subtype"): NameObject(subtype),
                                NameObject("/Rect"): ArrayObject([FloatObject(x) for x in [10, 10, 30, 30]]),
                                NameObject("/T"): TextStringObject(author),
                                NameObject("/Contents"): TextStringObject(contents)})
        annotations.append(writer._add_object(obj))
    page[NameObject("/Annots")] = ArrayObject(annotations)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class TrainingIntake(unittest.TestCase):
    def test_readonly_scan_deduplicates_archive_aliases_without_advisor_attribution(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "private") as temp:
            base = Path(temp)
            source = base / "source"
            source.mkdir()
            data = annotated_pdf()
            (source / "draft.pdf").write_bytes(data)
            (source / "draft.tex").write_text(r"\documentclass{article}" + "\n", encoding="utf-8")
            with zipfile.ZipFile(source / "copies.zip", "w") as archive:
                # A traversal-shaped member is read in memory, never written to its name.
                archive.writestr("../outside.pdf", data)
            before = {p.name: intake.digest(p.read_bytes()) for p in source.iterdir()}
            summary = intake.scan(source, base / "records")
            self.assertEqual(summary["unique_pdfs"], 1)
            self.assertEqual(summary["unique_non_link_popup_widget_annotations"], 2)
            self.assertEqual(summary["errors"], [])
            self.assertFalse((base / "outside.pdf").exists())
            self.assertEqual(before, {p.name: intake.digest(p.read_bytes()) for p in source.iterdir()})
            records = [json.loads(s) for s in (base / "records" / "annotations.jsonl").read_text().splitlines()]
            self.assertTrue(all(r["advisor_identity"] == "unconfirmed" for r in records))
            self.assertTrue(all(len(r["paths"]) == 2 for r in records))
            self.assertEqual(records[1]["contents"], "")
            with self.assertRaisesRegex(ValueError, "already contains"):
                intake.scan(source, base / "records")

    def test_comments_do_not_become_active_dependencies(self):
        source = (r"% \input{not-active}" + "\n" + r"\input{actual}" + "\n" +
                  r"a\% literal % \input{not-active-either}" + "\n" + r"a\\% \input{comment}")
        details = intake.tex_details(source.encode())
        self.assertEqual(details["dependencies"], [{"kind": "input", "target": "actual", "line": 2}])
        self.assertIn(r"a\% literal", intake.uncomment(source))

    def test_output_must_not_write_into_sources_or_public_tree(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "private") as temp:
            source = Path(temp)
            with self.assertRaisesRegex(ValueError, "outside source"):
                intake.scan(source, source / "results")
            with self.assertRaisesRegex(ValueError, "within development/private"):
                intake.scan(source, ROOT / "unexpected-public-output")
            self.assertFalse((ROOT / "unexpected-public-output").exists())


if __name__ == "__main__":
    unittest.main()
