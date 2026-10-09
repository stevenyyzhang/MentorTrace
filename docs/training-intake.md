# Local training material intake

The development workspace includes a read-only intake utility for mixed PDF,
LaTeX and archive sources. It inventories hashes, reads PDF annotation objects
and text locators, records LaTeX dependencies and possible editing markers, and
indexes exact duplicates. It uses the existing `pypdf` dependency and does not
send source material to a model or alter either frozen corpus.

Run it with an explicit source directory and a new output directory under this
development workspace's `private/` directory:

```powershell
python scripts/training_intake.py --source ./materials --output private/analysis/new-intake
```

An occupied output directory is rejected so an uncertain previous run is
inspected before another extraction. ZIP members are read in memory. RAR input
requires a local `tar` executable with RAR support; this batch-oriented path reads
members with filename suffixes and reports that limitation. It never extracts
archive member names onto the filesystem or executes LaTeX source.

All generated records are private, including filenames, annotations and TeX
source. `inventory.json` records files and archive members;
`annotations.jsonl` preserves raw annotation authors, page and object locators;
`pdf_text.jsonl` stores extracted text for locating passages;
`latex_sources.json` preserves source text and dependency locators;
`duplicates.json` binds identical bytes to all aliases; `summary.json` records
coverage, errors and the extractor hash. Exact duplicate PDF/TeX bytes are parsed
once. Role hints are screening suggestions and require review.

PDF author metadata alone does not establish identity. Record human identity
confirmations separately from raw extraction. Student comments can supply response
context but must retain their attribution. A blank annotation body can still be
a deletion, highlight or handwritten change; use the original page and annotation
geometry. Extracted PDF text does not certify equation transcription.

TeX comparisons establish what changed, not who made a change or why. Keep
conflict copies, backups and differing archive snapshots as distinct sources.
Record chronology and annotated-page/source correspondence where supported; if
these remain unknown, compare variants without claiming a response sequence. A
local role match is not a complete document match. A publication-like directory label does not establish publication
or manuscript quality. Related short and long papers must remain linked when
selecting training and evaluation material.

Corpus admission requires a separate evidence review. Reconcile exact source
overlap with previous training material and check prior learning coverage before
counting observations as new. Annotation-object counts are not concern counts.
Do not promote raw extractions or inferred intentions directly into a frozen
Advisor corpus or the published-paper cases. For semantic extraction and version
chains, use the skill's [historical training intake](../.agents/skills/mentortrace/references/historical-training-intake.md)
reference. New snapshots require complete six-field comparison, a private decision
ledger and source mapping, disclosed training exposure and regenerated freeze hashes.

Reading and comparing TeX needs no TeX compiler. Rebuilding a project additionally
requires its document class, packages, bibliography and figures, and may require
EPS conversion tools. A successful dependency lookup does not establish successful
compilation.

Focused verification:

```powershell
python -m unittest discover -s tests -p test_training_intake.py -v
```
