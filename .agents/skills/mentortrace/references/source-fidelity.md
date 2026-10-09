# Source fidelity before judgment and delivery

Extracted text is a navigation and prose-reading aid. PDF text layers can omit mathematical delimiters, scripts or operators even when the page is clear. Hashes prove the version, not extraction fidelity. Keep raw extraction and original page images. A corrected transcription is a separate record tied to the image hash; never silently repair the frozen body. Agreement between extractors is not proof of correctness.

## Formula-dependent judgments

Inspect and transcribe the decisive expression from its original page before alleging a defect. Identify observed symbols and their scope that control the allegation: magnitude/norm delimiters, powers, signs, conjugation, optimization direction or indices, as applicable. Record page/column/equation, the frozen image hash and differences from extraction. A description such as "complex-weight voting" does not establish whether a magnitude operator is present.

If the page contradicts the allegation, withdraw it or narrow it to a separately supported requirement. Repeated lane agreement does not settle shared extraction corruption. For unreadable glyphs, obtain a sharper local render/crop or permitted source; retain uncertainty if still insufficient. Never guess an expression or add external calls without applicable authorization. Alternative extraction/OCR can flag discrepancies but cannot replace page inspection.

New `source_fidelity: 1` protocols require Verify's `source_fidelity_checks` for every input finding and each new finding. Formula rows record the expression, decisive symbols, image hash and extraction comparison; non-formula rows explain that classification. The runner rejects missing records, stale hashes, retained contradicted premises and confirmed outputs based on unreadable formulas. Visual transcription and correct formula/non-formula classification still need substantive review.

## Surface candidates without silent normalization

At creation the runner scans raw text for alphabetic fragments separated by a hyphen and horizontal whitespace within one extracted line. `inputs/source_fidelity.json` retains exact spans, page, offsets and context. The scan does not certify physical same-line placement or author error, and does not cover all split words or spelling errors.

Language inspects each candidate on the page and returns `source_candidate_dispositions`:

- `definite_error`: unintended split visible on the page; link a Language finding with observed spelling and correction.
- `valid_source`: intentional compound, notation or valid layout; explain the observed placement.
- `extraction_artifact`: the page is correct and extraction created the anomaly; explain the difference.
- `unresolved`: source or intended term cannot be resolved; link an anchored uncertainty item.

A normal word broken at the physical line end may be reconstructed for reading. A hyphen and space inside the physical line needs a separate judgment before joining fragments. Legitimate compounds/notation may retain hyphens. Dispose of every candidate, including non-errors, while continuing the complete Language read. Whole-page `checked` status does not dispose of candidates. Never use earlier reports or advisor answers for this initial inspection.

## Report quotations

Reuse checked transcription for formula-centered `Original` passages, or an unaltered source crop if faithful transcription is unavailable. Compare the rendered report with the original page for meaning-bearing symbols; a correctly rendered but incorrect transcription fails this check. Review repeated quotations together. If a corrected quotation changes an opinion's premise, re-adjudicate the opinion and its shared revision actions. Source-to-report preservation alone does not establish source accuracy.

Apply this contract to new runs. Historical frozen inputs/requests/findings retain their protocol; label later corrections as corrections, not fresh discoveries. Structural acceptance does not guarantee zero false alarms or missed errors.
