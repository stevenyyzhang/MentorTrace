"""Render a MentorTrace bilingual Markdown report with the saved print format."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path

from lxml import html


ASSET = Path(__file__).resolve().parents[1] / "assets" / "report_bilingual.css"
METADATA_MARKERS = (
    "Manuscript:",
    "稿件：",
    "Source SHA-256:",
    "Review setting:",
    "Result:",
    "Review record:",
)


def find_executable(explicit: str | None, names: tuple[str, ...], windows_paths: tuple[str, ...]) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"Executable not found: {path}")
        return str(path)
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for candidate in windows_paths:
        path = Path(candidate)
        if path.is_file():
            return str(path)
    raise FileNotFoundError(f"Install one of {', '.join(names)} or pass its path explicitly")


def separate_metadata_lines(markdown: str) -> str:
    """The report's four hard-wrapped metadata lines become four grid items."""
    lines = markdown.splitlines()
    first_section = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    output: list[str] = []
    for index, line in enumerate(lines):
        output.append(line.rstrip() if index < first_section else line)
        if (
            index < first_section
            and line.startswith("**")
            and any(marker in line for marker in METADATA_MARKERS)
            and index + 1 < len(lines)
            and lines[index + 1].strip()
        ):
            output.append("")
    return "\n".join(output) + "\n"


def group_finding_sections(card: html.HtmlElement) -> None:
    """Keep each language's location and manuscript excerpt in one source panel."""
    children = list(card)
    for start_label, end_labels, language in (
        ("Location:", ("Comment:",), "en"),
        ("位置：", ("审阅意见：", "评审意见："), "zh"),
    ):
        start = next((i for i, child in enumerate(children)
                      if child.tag == "p" and "".join(child.itertext()).strip().startswith(start_label)), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(children))
                    if children[i].tag == "p" and "".join(children[i].itertext()).strip().startswith(end_labels)), None)
        if end is None:
            continue
        source = html.Element("div", {"class": f"source-context {language}-source"})
        card.insert(start, source)
        for child in children[start:end]:
            source.append(child)
        children = list(card)

    first_chinese = next((child for child in card
                          if child.tag == "p" and "".join(child.itertext()).strip().startswith(
                              ("修改优先级：", "审阅意见：", "审阅意见:", "评审意见：", "评审意见:", "建议修改：", "建议修改:")))
                         , None)
    chinese_source = next((child for child in card
                           if "zh-source" in child.get("class", "").split()), None)
    boundary = first_chinese
    if chinese_source is not None and (boundary is None or card.index(chinese_source) < card.index(boundary)):
        boundary = chinese_source
    if boundary is not None:
        card.insert(card.index(boundary), html.Element("div", {"class": "language-divider"}))


def build_html(markdown: str, css_name: str, pandoc: str) -> tuple[str, int, int]:
    # GFM recognizes dollar math; normalize both TeX delimiter forms for
    # rendering only, without changing the frozen Markdown.
    render_markdown = re.sub(r"\\\((.+?)\\\)", lambda m: "$" + m.group(1).strip() + "$", markdown, flags=re.S)
    render_markdown = re.sub(
        r"\\\[(.*?)\\\]",
        lambda m: "\n\n$$\n" + m.group(1).strip() + "\n$$\n\n",
        render_markdown,
        flags=re.S,
    )
    fragment = subprocess.run(
        # Pandoc's GFM parser treats a standalone '=' inside a $$ block as a
        # Setext heading, leaving the surrounding equation as literal TeX.
        [pandoc, "--from=markdown+tex_math_dollars", "--to=html5", "--mathml"],
        input=separate_metadata_lines(render_markdown),
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout
    blocks = list(html.fragment_fromstring(fragment, create_parent="div"))
    # Older report drafts used a bold paragraph for the shared plan. Treat its
    # exact bilingual label as a semantic heading before identifying card ends.
    for block in blocks:
        if block.tag == "p" and " ".join(" ".join(block.itertext()).split()).rstrip(":：") == "Revision plan for this group / 本组修改方案":
            block.clear()
            block.tag = "h4"
            block.text = "Revision plan for this group / 本组修改方案"
    if not blocks or blocks[0].tag != "h1":
        raise ValueError("Expected a report title")

    report = html.Element("main", {"class": "report"})
    opening = html.Element("header", {"class": "report-header"})
    opening.append(blocks[0])

    index = 1
    metadata=[]
    while index < len(blocks) and blocks[index].tag == "p":
        content=" ".join(blocks[index].itertext()).strip()
        if any(content.startswith(marker) for marker in METADATA_MARKERS):
            metadata.append(blocks[index])
        else:
            blocks[index].set("class", "lead-note")
            opening.append(blocks[index])
        index += 1
    if metadata:
        grid = html.Element("div", {"class": "metadata-grid"})
        for block in metadata:
            content=" ".join(block.itertext())
            role = "sha" if "SHA-256:" in content else "manuscript" if content.startswith(("Manuscript:", "稿件：")) else "setting" if "Review setting:" in content else "result"
            item = html.Element("div", {"class": f"metadata-item {role}"})
            item.append(block)
            if role == "sha":
                for code in item.iter("code"):
                    code.set("class", "sha256")
            grid.append(item)
        opening.insert(1,grid)
    report.append(opening)

    section = ""
    subsection = ""
    card_count = 0
    language_count = 0
    while index < len(blocks):
        block = blocks[index]
        if block.tag == "h2":
            section = " ".join(" ".join(block.itertext()).split())
            subsection = ""
            report.append(block)
            index += 1
            continue
        title = " ".join(" ".join(block.itertext()).split()) if block.tag in ("h3", "h4", "h5") else ""
        is_numbered = bool(re.match(r"\d+\.\s", title))
        if block.tag == "h3" and not is_numbered:
            subsection = title
        is_content = any(term in section for term in ("Priority content findings", "优先处理的内容问题", "Content comments", "内容意见", "Content and technical comments", "内容与技术意见"))
        is_language = any(term in section for term in ("Language and presentation findings", "语言与格式问题", "Language and presentation comments", "语言与格式意见"))
        is_optional = ("Optional organization and flow suggestions" in section
            or "可选组织与行文建议" in section
            or (("Organization and flow comments" in section or "篇章组织与行文意见" in section)
                and "Suggested manuscript wording" not in subsection
                and "论文正文建议写法" not in subsection))
        is_legacy = bool(re.search(r"verify:F\d+", title))
        if block.tag in ("h3", "h4") and ((is_numbered and (is_content or is_language or is_optional)) or (is_legacy and is_content)):
            end=index+1
            while end < len(blocks) and blocks[end].tag not in ("h2","h3","h4","h5"):
                end += 1
            priority=" ".join(" ".join(b.itertext()) for b in blocks[index+1:end] if b.tag=="p" and "Revision priority" in " ".join(b.itertext()))
            level = "high" if (re.search(r"\bRevision priority:\s*High\b", priority)
                               or "High / 高" in title + priority
                               or "高 / High" in title + priority) else "medium"
            card_class = f"finding-card {level}" if is_content else "organization-card" if is_optional else "language-card"
            card = html.Element("article", {"class": card_class})
            card.append(block)
            index += 1
            while index < len(blocks) and blocks[index].tag not in ("h2", "h3", "h4", "h5"):
                child = blocks[index]
                if child.tag == "p":
                    content = "".join(child.itertext()).strip()
                    if content.startswith(("位置 / Location:", "Location:", "位置：")):
                        child.set("class", "location-row")
                    elif content.startswith(("Original / 原文:", "Suggested / 建议:", "Suggested revision / 建议修改:")):
                        child.set("class", "source-row")
                    elif content.startswith("Suggested revision:"):
                        child.set("class", "en revision-start")
                    elif content.startswith("Comment:"):
                        child.set("class", "en comment-start")
                    elif content.startswith(("建议修改：", "建议修改:")):
                        child.set("class", "zh revision-start")
                    elif content.startswith("修改优先级："):
                        child.set("class", "zh priority-row")
                    elif content.startswith(("中文：", "中文:", "审阅意见：", "审阅意见:", "评审意见：", "评审意见:")):
                        child.set("class", "zh")
                    elif content.startswith(("English:", "Comment:", "Suggested revision:")):
                        child.set("class", "en")
                card.append(child)
                index += 1
            group_finding_sections(card)
            report.append(card)
            if is_content:
                card_count += 1
            elif is_language:
                language_count += 1
            continue
        if block.tag == "h3" and is_content and not is_numbered:
            block.set("class", "group-heading")
        if block.tag == "h4":
            block.set("class", "plan-heading" if ("Revision plan" in title or "Shared revision actions" in title)
                      else "draft-heading")
        if block.tag == "h5":
            block.set("class", "draft-heading")
        if block.tag == "p" and "".join(block.itertext()).strip().startswith("Suggested wording / 建议文本:"):
            block.set("class", "draft-wording-label")
        if block.tag == "ol" and ("语言与表面问题" in section or "Language and surface" in section):
            block.set("class", "language-list")
        if block.tag == "ul" and ("检查覆盖与边界" in section or "Coverage and limits" in section or "Review coverage and limits" in section):
            block.set("class", "coverage-list")
        is_draft_section = any(term in section for term in (
            "Coordinated English replacement passages", "协调后的英文替换草稿",
            "Proposed wording by readiness", "按可用条件整理的建议改写"))
        is_draft_section = is_draft_section or (("Organization and flow comments" in section
            or "篇章组织与行文意见" in section) and
            ("Suggested manuscript wording" in subsection or "论文正文建议写法" in subsection))
        if block.tag == "p" and is_draft_section and block.find("strong") is not None:
            draft = html.Element("article", {"class": "draft-card"})
            block.set("class", "en")
            draft.append(block)
            index += 1
            next_strong = blocks[index].find("strong") if index < len(blocks) and blocks[index].tag == "p" else None
            if next_strong is not None and re.match(r"[\u4e00-\u9fff]", "".join(next_strong.itertext()).strip()):
                blocks[index].set("class", "zh")
                draft.append(blocks[index])
                index += 1
            report.append(draft)
            continue
        report.append(block)
        index += 1

    if not card_count:
        raise ValueError("No content findings were found")

    # A local draft's heading, conditions and text form one readable unit.
    # Keep the revision-plan actions independent so a whole group can paginate.
    draft_parent = None
    for child in list(report):
        if child.tag in ("h2", "h3", "h4", "h5") or any(
            name in child.get("class", "").split()
            for name in ("finding-card", "organization-card", "language-card")
        ):
            draft_parent = None
        if child.get("class") == "draft-heading":
            draft_parent = html.Element("article", {"class": "draft-block draft-card"})
            report.insert(report.index(child), draft_parent)
        if draft_parent is not None:
            draft_parent.append(child)

    for draft in report.xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " draft-block ")]'):
        chinese = next((child for child in draft if child.tag == "p" and
                        re.match(r"[\u3400-\u9fff]", "".join(child.itertext()).strip())), None)
        wording = next((child for child in draft if child.get("class") == "draft-wording-label"), None)
        for boundary in (chinese, wording):
            if boundary is not None:
                previous = boundary.getprevious()
                if previous is None or previous.tag != "hr":
                    draft.insert(draft.index(boundary), html.Element("hr"))

    # A shared plan is a sibling of the group's individual finding cards.
    # Permit the plan to paginate while keeping each bilingual action together.
    plan_parent = None
    for child in list(report):
        boundary = child.tag in ("h2", "h3", "h4", "h5") or any(
            name in child.get("class", "").split()
            for name in ("finding-card", "organization-card", "language-card", "draft-block"))
        if boundary:
            plan_parent = None
        if child.get("class") == "plan-heading":
            plan_parent = html.Element("section", {"class": "group-revision-plan"})
            report.insert(report.index(child), plan_parent)
        if plan_parent is not None:
            plan_parent.append(child)

    # Shared plans use English actions as one run, followed by Chinese actions.
    # The divider marks the language change without boxing any action pair.
    for plan in report.xpath('.//section[contains(concat(" ", normalize-space(@class), " "), " group-revision-plan ")]'):
        chinese = next((child for child in plan if child.tag == "p"
                        and "".join(child.itertext()).strip().startswith(("建议修改:", "建议修改："))), None)
        if chinese is not None:
            plan.insert(plan.index(chinese), html.Element("hr", {"class": "plan-language-divider"}))

    group_parent = None
    for child in list(report):
        starts_ungrouped_card = child.tag == "article" and len(child) and child[0].tag == "h3"
        if child.tag in ("h2", "h3") or starts_ungrouped_card:
            group_parent = None
        if child.get("class") == "group-heading":
            group_parent = html.Element("section", {"class": "revision-group"})
            report.insert(report.index(child), group_parent)
        if group_parent is not None:
            group_parent.append(child)

    coverage_parent = None
    for child in list(report):
        if child.tag == "h2":
            coverage_parent = None
            if "Coverage and remaining checks" in " ".join(" ".join(child.itertext()).split()):
                coverage_parent = html.Element("section", {"class": "coverage-block"})
                report.insert(report.index(child), coverage_parent)
        if coverage_parent is not None:
            coverage_parent.append(child)

    page = html.Element("html", {"lang": "en"})
    head = html.Element("head")
    head.append(html.Element("meta", {"charset": "utf-8"}))
    head.append(html.Element("meta", {"name": "viewport", "content": "width=device-width, initial-scale=1"}))
    title = html.Element("title")
    title.text = "MentorTrace Bilingual Manuscript Review / 双语论文审阅报告"
    head.append(title)
    head.append(html.Element("link", {"rel": "stylesheet", "href": css_name}))
    page.append(head)
    body = html.Element("body")
    body.append(report)
    page.append(body)
    return "<!DOCTYPE html>\n" + html.tostring(page, encoding="unicode", method="html", pretty_print=True), card_count, language_count


def print_pdf(chrome: str, html_path: Path, pdf_path: Path, markdown: str,
              no_sandbox: bool = False) -> int:
    with tempfile.TemporaryDirectory(prefix="mentortrace-pdf-", ignore_cleanup_errors=True) as profile:
        with tempfile.TemporaryDirectory(prefix="mentortrace-output-") as intermediate:
            proof = Path(intermediate) / "proof.pdf"
            args = [
                chrome, "--headless=new", "--disable-gpu",
                "--disable-extensions", "--no-pdf-header-footer",
                f"--user-data-dir={profile}", f"--print-to-pdf={proof}", html_path.as_uri(),
            ]
            if no_sandbox:
                args.insert(2, "--no-sandbox")
            result = subprocess.run(args, capture_output=True, text=True, timeout=45)
            deadline = time.monotonic() + 30
            last_size = -1
            stable_checks = 0
            while time.monotonic() < deadline:
                if proof.is_file():
                    size = proof.stat().st_size
                    stable_checks = stable_checks + 1 if size > 0 and size == last_size else 0
                    last_size = size
                    if stable_checks >= 3:
                        break
                time.sleep(0.25)
            else:
                raise RuntimeError(f"Chrome did not write the PDF (exit {result.returncode}): {result.stderr[-1000:]}")

            from pypdf import PdfReader

            reader = PdfReader(str(proof))
            text = " ".join(page.extract_text() or "" for page in reader.pages)
            expected = set(re.findall(r"verify:F\d+", markdown))
            missing = expected - set(re.findall(r"verify:F\d+", text))
            if missing:
                raise RuntimeError(f"PDF is missing finding IDs: {sorted(missing)}")
            if not expected:
                def normalized_title(value):
                    return re.sub(r"\\[()]|[{}_]|\s+", "", unicodedata.normalize("NFKC", value)).casefold()
                normalized_pdf = normalized_title(text)
                headings = re.findall(r"(?m)^#{3,4} \d+\. ([^/\n]+) /", markdown)
                missing_titles = [
                    heading for heading in headings
                    if normalized_title(heading) not in normalized_pdf
                ]
                if missing_titles:
                    raise RuntimeError(f"PDF is missing numbered finding titles: {missing_titles}")
            shutil.copyfile(proof, pdf_path)
            return len(reader.pages)


def validate_delivery(markdown_path, preservation_path, requirements_path=None):
    """Validate the actual report against both frozen audit records before export."""
    from audit_report_preservation import read, validate
    ledger = read(preservation_path)
    preservation = validate(ledger, markdown_path, require_v2=True)
    if requirements_path is None:
        raise ValueError("New delivery needs --requirements-audit with a report-bound consolidation review")
    import importlib.util
    module_path = Path(__file__).resolve().parents[4] / "scripts" / "audit_merge_obligations.py"
    if not module_path.is_file():
        raise ValueError("Consolidation checker unavailable; keep the complete MentorTrace repository")
    spec = importlib.util.spec_from_file_location("mentortrace_delivery_obligations", module_path)
    obligations = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obligations)
    upstream = obligations.read(requirements_path)
    consolidation = obligations.validate(upstream, report_path=markdown_path, require_ready=True)
    package = obligations.read(Path(upstream["audit_directory"]) / "package.json")
    final_hash = package["source_files"]["final.json"]
    if not any(source["sha256"] == final_hash for source in ledger["sources"]):
        raise ValueError("Delivery sources do not include the final review bound by the consolidation audit")
    return {"preservation": preservation, "consolidation": consolidation,
            "semantic_correctness_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", type=Path, required=True, help="Frozen bilingual Markdown report")
    parser.add_argument("--preservation-audit", type=Path, required=True, help="Completed source-to-report preservation ledger")
    parser.add_argument("--requirements-audit", type=Path, help="Completed report-bound phase B consolidation ledger")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="report_bilingual", help="Output basename")
    parser.add_argument("--pandoc", help="Path to pandoc executable")
    parser.add_argument("--chrome", help="Path to Chrome or Chromium executable")
    parser.add_argument("--chrome-no-sandbox", action="store_true",
                        help="Use only when a restricted local environment blocks Chrome's sandbox")
    parser.add_argument("--html-only", action="store_true", help="Write HTML/CSS without printing PDF")
    parser.add_argument("--force", action="store_true", help="Replace existing output files")
    args = parser.parse_args()

    markdown_path = args.markdown.resolve(strict=True)
    validate_delivery(markdown_path, args.preservation_audit, args.requirements_audit)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{args.name}.html"
    css_path = output_dir / f"{args.name}.css"
    pdf_path = output_dir / f"{args.name}.pdf"
    targets = (html_path, css_path) if args.html_only else (html_path, css_path, pdf_path)
    existing = [path for path in targets if path.exists()]
    if existing and not args.force:
        raise FileExistsError(f"Refusing to overwrite: {', '.join(map(str, existing))}; pass --force")

    pandoc = find_executable(
        args.pandoc, ("pandoc",), ()
    )
    markdown = markdown_path.read_text(encoding="utf-8")
    html_text, card_count, language_count = build_html(markdown, css_path.name, pandoc)
    html_path.write_text(html_text, encoding="utf-8")
    shutil.copyfile(ASSET, css_path)
    if args.html_only:
        print(f"HTML/CSS: {html_path}, {css_path}; {card_count} content and {language_count} language cards")
        return

    chrome = find_executable(
        args.chrome, ("chrome", "google-chrome", "chromium", "msedge"),
        (),
    )
    pages = print_pdf(chrome, html_path, pdf_path, markdown, args.chrome_no_sandbox)
    print(f"PDF: {pdf_path}; {pages} A4 pages; {card_count} content and {language_count} language cards")


if __name__ == "__main__":
    main()
