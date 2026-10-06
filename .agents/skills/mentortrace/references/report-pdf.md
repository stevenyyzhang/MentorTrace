# Bilingual report print format

Use this format when a bilingual manuscript review is exported to HTML/PDF. It formats a **frozen author-facing Markdown report**; it does not change findings, issue counts, source dispositions, or advisor-comparison policy.

Apply the [author-facing bilingual report rules](report-language.md) before export. The current report format puts English first and displays separately numbered content/technical, organization/flow, and language/presentation comments without internal IDs. Preserve the Markdown grouping and local revision plans rather than flattening them or collecting drafts elsewhere.

In 使用说明, keep `Revision priority: ...` and `修改优先级： ...` as two separate paragraphs, English first, with plain (unbolded) labels and the explanation on the same line as its label. Do not turn them into a combined heading or merge them with comment-type descriptions. Preserve locally attached paragraph drafts and their use conditions selected by the revision-scope check.

## Reusable resources

- CSS source of truth: [`../assets/report_bilingual.css`](../assets/report_bilingual.css).
- Markdown → HTML/CSS/PDF renderer: [`../scripts/render_bilingual_report.py`](../scripts/render_bilingual_report.py).
- The renderer copies the CSS beside the output HTML. Keep the HTML and CSS together so local and printed rendering use the same stylesheet.

From the MentorTrace root, with Pandoc, Chrome/Chromium and a Python environment containing `lxml` and `pypdf`:

```powershell
python .agents/skills/mentortrace/scripts/render_bilingual_report.py `
  --markdown runs/<run>/report_bilingual.md `
  --preservation-audit runs/<run>/delivery_audit.json `
  --requirements-audit workspaces/<audit>/B.json `
  --output-dir runs/<run>
```

The default basename is `report_bilingual`, producing `.html`, `.css` and `.pdf`. Use `--name` for a different basename, `--html-only` to inspect HTML/CSS before printing, and `--force` only when intentionally replacing an existing export. `--pandoc` and `--chrome` accept explicit executable paths. Chrome prints a local `file:` URL with a fresh temporary profile; the renderer does not upload the manuscript. When the user asks for Markdown first, deliver the checked `.md` before generating an HTML/PDF export.

## Design contract

- Render the bilingual `Manuscript` and `稿件` metadata as adjacent cards in the two-column metadata grid. A Chinese manuscript label must not fall through to an unrelated lead note.
- Preserve direct English replacement wording in both language blocks; do not replace the Chinese action with a reference to wording elsewhere. Keep substantive Original excerpts and their numbered display formulas together inside each comment card. The renderer must convert both inline `\(...\)` and display `\[...\]` math to printable MathML before PDF export.
- `Suggested wording / 建议文本:` is followed by a paragraph break before the replacement passage; preserve that break in HTML/PDF. Other comment/revision fields keep their same-line values.
- Start directly with the Markdown report title; do not inject an extra “MentorTrace / Bilingual manuscript review” eyebrow above it. Use the body font stack for the `Location` label and its prose value. Keep monospace for actual code, symbols and hashes only.

- A4 pages with `12mm` margins and browser print backgrounds enabled.
- Body font stack begins `Inter`, system sans, `Segoe UI`, then Chinese sans fallbacks; monospace begins `JetBrains Mono`, `Fira Code`, then system code fonts. Inspect actual embedded fonts after export because unavailable fonts fall back locally.
- Title `18pt/700`; section headings `13pt/600` with a 2px pale-blue underline; finding headings `11pt/600`.
- When metadata is needed, use a two-column grid; do not add private review provenance merely to populate it. Metadata labels `9pt/600`, values `9pt/400`; SHA-256 uses `8.5pt` monospace with wrapping.
- Body line height `1.55`. English paragraphs precede Chinese paragraphs, with distinct spacing; the English text is muted on screen.
- Each content finding is a bordered card with `14px` padding, `8px` radius, and a 4px red (high) or amber (medium) left stripe.
- **Paginate continuously by default:** do not force a page break before every numbered comment or reserve a whole page for one comment. Short comments may share a page. Keep one complete comment card on a single page when it fits, using `break-inside: avoid`. Do not force an entire revision group onto one page. Keep a comment heading with the start of its card. A local draft is one bordered block containing its heading, use/scope instructions, Chinese explanation, and single Suggested wording passage; keep the whole block on one page when it fits. If a block is taller than the printable page, split only at a natural paragraph or equation boundary, keeping the heading with its instructions and the `Suggested wording / 建议文本:` label with the passage it introduces. Visually verify that no text, equation, alternative version, or closing sentence is clipped or left outside its border.
- For grouped reports, render the unnumbered group headings separately and recognize numbered fourth-level problem headings as finding cards. Allow groups and shared revision plans to span pages, but keep each bilingual action together. Keep each local draft heading, use conditions and proposed text/checklist together when they fit on a page. Do not wrap following comment cards into a draft block. Normalize whitespace when recognizing bilingual section titles.
- A shared `Shared revision actions for comments … / 第 … 条的统一修改动作` (or earlier `Revision plan for comments … / 第 … 条的统一修改方案`) explicitly names its numbered scope and is a group-level section after its numbered cards, never a child of the final comment card. Render all English actions as consecutive paragraphs, then all Chinese actions as consecutive paragraphs, with a simple language divider. Do not put a shaded frame around the full plan or any English/Chinese action pair. Continue recognizing the legacy `Revision plan for this group / 本组修改方案` label even in bold-paragraph form so older Markdown cannot silently merge it into a comment. Keep the logical group free to paginate.
- In each numbered card, wrap the English Location and its entire Original excerpt (including displayed formulas and continuation paragraphs) in one light-gray panel. Align Location, Original, Comment, Suggested revision, 审阅意见 and 建议修改 to the same text inset. Place a light divider between the complete English block and the compact Chinese block, never above the English Suggested revision. The Chinese block contains only 审阅意见 and any 建议修改; no repeated priority, location or source panel appears there. Leave clear paragraph space between Comment and Suggested revision and between 审阅意见 and 建议修改. For grouped content, place shared revision plans outside individual cards, after all scoped problem cards. Keep all field values on the same line as their labels except Suggested wording, whose passage starts in the next paragraph. Recognize fifth-level local-draft headings as the start of a separate draft block at the same readable heading size as a numbered comment. The block includes English instructions, a divider, Chinese explanation, a divider, and exactly one Suggested wording label and passage; no formula, version or closing sentence may fall outside its border.
- **Print text is black**, including metadata, labels, lists and page numbers. The risk stripe and blue section rule retain their colors. This is the user's current PDF preference; the HTML screen view may use muted text colors.

## Delivery check

Render all PDF pages to images and inspect long headings, SHA wrapping, Chinese/English glyphs, card breaks and last-page balance. Check that short comments can share pages, fitting cards do not split, long cards are not clipped, and every local draft has one visible border containing its title, conditions, both separators and a single complete wording passage. Confirm no draft heading or Suggested wording label is stranded on a different page from its text, and no shared plan has a shaded frame or pairwise action box. Confirm the PDF contains every numbered finding; keep internal IDs in the private mapping, not in the author-facing report. For the black-text variant, inspect PDF text color rather than inferring it from CSS alone. Keep page count, findings count and model settings specific to each run; the prior report's values are not template constants.

## Preservation prerequisite

Before rendering, complete references/delivery-preservation.md and pass --preservation-audit DELIVERY.json plus --requirements-audit B.json to render_bilingual_report.py. The first must be a completed version 2 final-text audit; the second must be a delivery-ready consolidation comparison bound to this exact report and the same final review. Both are required for HTML-only and PDF exports and are checked before any output writes. Existing frozen report files remain unchanged.
