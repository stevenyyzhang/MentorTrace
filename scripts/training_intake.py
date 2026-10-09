"""Read-only local intake of mixed training sources; never promotes corpus records.

PDF text is a locator, annotation authors are unverified metadata, and TeX diffs
are observations rather than evidence of an advisor's intent. Outputs contain
private source material and must remain in the development tree's private area.
No source compilation, macro execution, network access or model call occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from pypdf import PdfReader

SEMANTIC = {
    "/Text", "/FreeText", "/Line", "/Square", "/Circle", "/Polygon",
    "/PolyLine", "/Highlight", "/Underline", "/Squiggly", "/StrikeOut",
    "/Stamp", "/Caret", "/Ink", "/FileAttachment", "/Redact", "/Sound",
}
BUILD = {".aux", ".blg", ".log", ".out", ".dvi", ".nav", ".snm", ".toc", ".vrb", ".gz"}
MAX_MEMBER_BYTES = 160 * 1024 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def uncomment(text: str) -> str:
    """Strip TeX line comments; an odd number of preceding slashes escapes %."""
    result = []
    for line in text.splitlines():
        end = len(line)
        for pos, char in enumerate(line):
            if char == "%":
                slashes = len(line[:pos]) - len(line[:pos].rstrip("\\"))
                if slashes % 2 == 0:
                    end = pos
                    break
        result.append(line[:end])
    return "\n".join(result)


def tex_details(data: bytes) -> dict:
    encoding = "utf-8-sig"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = "gb18030"
        text = data.decode(encoding)
    active = uncomment(text)
    dependencies = []
    for m in re.finditer(r"\\(documentclass|usepackage|input|include|bibliography|includegraphics)(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}", active):
        dependencies.append({"kind": m[1], "target": m[2], "line": active[:m.start()].count("\n") + 1})
    markers = []
    pattern = r"\\(?:textcolor|color|sout|uline|added|deleted|replaced|todo|marginpar)\b|liang|liu|revise|rewrite|comment|修改|建议"
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(pattern, line, re.I):
            markers.append({"line": number, "text": line})
    title = re.search(r"\\title(?:\s*\[[^\]]*\])?\s*\{", active)
    return {"encoding": encoding, "text": text, "active_text_sha256": digest(active.encode()),
            "dependencies": dependencies, "markers": markers,
            "title_locator": active[title.start():title.start() + 450] if title else "",
            "lines": len(text.splitlines()), "status": "parsed_not_compiled"}


def pdf_details(data: bytes, source_id: str) -> dict:
    reader = PdfReader(io.BytesIO(data), strict=False)
    if reader.is_encrypted:
        return {"status": "encrypted_not_read", "annotations": [], "pages": []}
    annotations, page_rows = [], []
    subtype_counts = Counter()
    for number, page in enumerate(reader.pages, 1):
        for index, ref in enumerate(page.get("/Annots", []) or []):
            ann = ref.get_object()
            subtype = str(ann.get("/Subtype", ""))
            subtype_counts[subtype] += 1
            if subtype in {"/Link", "/Popup", "/Widget"}:
                continue
            annotations.append({
                "source_id": source_id, "page": number, "annotation_index": index,
                "object_id": getattr(ref, "idnum", None), "subtype": subtype,
                "semantic_candidate": subtype in SEMANTIC,
                "author_raw": str(ann.get("/T", "")), "contents": str(ann.get("/Contents", "")),
                "subject": str(ann.get("/Subj", "")), "modified": str(ann.get("/M", "")),
                "created": str(ann.get("/CreationDate", "")),
                "rect": [float(x) for x in ann.get("/Rect", [])],
                "quad_points": [float(x) for x in ann.get("/QuadPoints", [])],
                "reply_to_object_id": getattr(ann.get("/IRT"), "idnum", None),
                "has_appearance": bool(ann.get("/AP")),
                "has_ink": bool(ann.get("/InkList")),
                "advisor_identity": "unconfirmed", "visual_verified": False,
            })
        # All pages are inspected for annotations. Text extraction is only a locator.
        page_rows.append({"page": number, "text": page.extract_text() or ""})
    text = "\n".join(p["text"] for p in page_rows)
    return {"status": "parsed", "page_count": len(page_rows),
            "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()},
            "subtypes": dict(subtype_counts), "annotations": annotations, "pages": page_rows,
            "annotation_count": len(annotations),
            "annotation_authors": dict(Counter(a["author_raw"] for a in annotations)),
            "text_chars": len(text), "text_sha256": digest(text.encode()),
            "visual_verified": False}


def role_hint(name: str, pdf: dict | None = None) -> str:
    """Hints route human review; never silently discard a source."""
    path = name.split("::")[-1].lower().replace("\\", "/")
    suffix = Path(path).suffix
    basename = Path(path).name
    if "冲突副本" in path:
        return "conflict_branch_needs_confirmation"
    if "ieeetran_how" in path or "bare_jrnl" in path:
        return "publisher_template"
    if suffix in BUILD:
        return "build_artifact"
    if suffix == ".bak":
        return "backup_needs_comparison"
    if suffix in {".zip", ".rar"}:
        return "archive_container"
    if suffix in {".eps", ".fig", ".png", ".pptx"} or "/figures/" in path or "-eps-converted-to" in path:
        return "figure_or_slide_asset"
    if "presentation" in path or "/pre latex/" in path:
        return "presentation_support"
    if any(x in path for x in ("rebuttal", "buttal", "response letter", "response tcom")):
        return "reviewer_response"
    if any(x in basename for x in ("transmittal", "biographies", "overlength", "charge-form")):
        return "publication_administration"
    if suffix == ".tex":
        return "latex_manuscript_candidate"
    if suffix == ".pdf":
        if pdf and pdf.get("page_count", 2) == 1 and not pdf.get("annotation_count"):
            return "single_page_needs_review"
        return "pdf_document_candidate"
    if suffix in {".bib", ".bbl", ".cls", ".sty"}:
        return "latex_build_dependency"
    return "other_support_needs_review"


def archive_members(path: Path):
    """Read archive bytes without extracting paths or executing project content."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            entries = [x for x in archive.infolist() if not x.is_dir()]
            if len(entries) > 10000 or sum(x.file_size for x in entries) > MAX_ARCHIVE_BYTES:
                raise ValueError("archive exceeds local intake limit")
            for info in entries:
                if info.file_size > MAX_MEMBER_BYTES:
                    raise ValueError(f"member exceeds local intake limit: {info.filename}")
                yield info.filename, archive.read(info)
    else:
        tar = shutil.which("tar")
        if not tar:
            raise ValueError("RAR listing requires tar with RAR support")
        listed = subprocess.run([tar, "-tf", str(path)], check=True, capture_output=True, timeout=60)
        names = listed.stdout.decode("utf-8").splitlines()
        total = 0
        for name in names:
            # This batch's RAR directories have no suffix. Report that scope explicitly.
            if not Path(name).suffix:
                continue
            member = subprocess.run([tar, "-xOf", str(path), "--", name], check=True,
                                    capture_output=True, timeout=60).stdout
            total += len(member)
            if len(member) > MAX_MEMBER_BYTES or total > MAX_ARCHIVE_BYTES:
                raise ValueError("archive exceeds local intake limit")
            yield name, member


def scan(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    private = Path(__file__).resolve().parents[1] / "private"
    if not source.is_dir() or output.is_relative_to(source) or not output.is_relative_to(private):
        raise ValueError("source must exist; output must be outside source and within development/private")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output already contains records; inspect them before selecting a new run directory")
    output.mkdir(parents=True, exist_ok=True)
    rows, archive_rows, pdfs, texs, errors = [], [], {}, {}, []

    def inspect(name, data, origin):
        sha = digest(data)
        row = {"path": name, "origin": origin, "bytes": len(data), "sha256": sha,
               "extension": Path(name.split("::")[-1]).suffix.lower()}
        try:
            if row["extension"] == ".pdf":
                if sha not in pdfs:
                    pdfs[sha] = pdf_details(data, sha)
                row["pdf"] = {k: v for k, v in pdfs[sha].items() if k not in {"pages", "annotations"}}
            elif row["extension"] == ".tex" or name.endswith(".tex.bak"):
                if sha not in texs:
                    texs[sha] = tex_details(data)
                row["latex"] = {k: v for k, v in texs[sha].items() if k != "text"}
        except Exception as exc:
            row["read_error"] = f"{type(exc).__name__}: {exc}"
            errors.append({"path": name, "error": row["read_error"]})
        row["role_hint"] = role_hint(name, row.get("pdf"))
        return row

    files = sorted(p for p in source.rglob("*") if p.is_file())
    for number, path in enumerate(files, 1):
        name = path.relative_to(source).as_posix()
        rows.append(inspect(name, path.read_bytes(), "filesystem"))
        if path.suffix.lower() in {".zip", ".rar"}:
            try:
                for member_name, data in archive_members(path):
                    archive_rows.append(inspect(name + "::" + member_name, data, "archive_member"))
            except Exception as exc:
                errors.append({"path": name, "error": f"{type(exc).__name__}: {exc}"})
        if number % 50 == 0:
            print(json.dumps({"files_processed": number, "total": len(files)}), flush=True)
    aliases = defaultdict(list)
    for row in rows + archive_rows:
        aliases[row["sha256"]].append(row["path"])
    for sha, details in pdfs.items():
        details["paths"] = aliases[sha]
    for sha, details in texs.items():
        details["paths"] = aliases[sha]
    write_json(output / "inventory.json", {"source_root": str(source), "files": rows, "archive_members": archive_rows})
    write_jsonl(output / "pdf_text.jsonl", ({"sha256": s, "paths": d["paths"], "pages": d["pages"]} for s, d in pdfs.items()))
    write_jsonl(output / "annotations.jsonl", (a | {"paths": d["paths"]} for d in pdfs.values() for a in d["annotations"]))
    write_json(output / "latex_sources.json", texs)
    write_json(output / "duplicates.json", {s: names for s, names in aliases.items() if len(names) > 1})
    summary = {
        "schema_version": 1, "baseline_version": (private.parent / "VERSION").read_text().strip(),
        "source_root": str(source), "script_sha256": digest(Path(__file__).read_bytes()),
        "model_calls": 0, "source_mutations": 0, "corpus_promotions": 0,
        "filesystem_files": len(rows), "filesystem_bytes": sum(r["bytes"] for r in rows),
        "extensions": dict(Counter(r["extension"] for r in rows)),
        "archive_members_read": len(archive_rows), "unique_pdfs": len(pdfs),
        "unique_tex_and_tex_backups": len(texs),
        "unique_non_link_popup_widget_annotations": sum(len(d["annotations"]) for d in pdfs.values()),
        "annotation_authors_raw": dict(Counter(a["author_raw"] for d in pdfs.values() for a in d["annotations"])),
        "annotation_subtypes": dict(Counter(a["subtype"] for d in pdfs.values() for a in d["annotations"])),
        "errors": errors,
        "limits": ["Role hints require human review; neither filenames nor PDF authors prove advisor identity.",
                   "PDF text and TeX markers are locators; page images govern notation and visual revisions.",
                   "RAR members without filename suffixes are not read by this batch-oriented scanner.",
                   "No TeX compilation or full figure/slide/document semantic review performed.",
                   "No new advisor concern is inferred or admitted to the frozen corpus."],
    }
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(scan(args.source, args.output), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
