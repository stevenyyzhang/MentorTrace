"""Stage-specific reference selection; manuscript and opinion inputs are unchanged."""
from pathlib import Path

DRAFT_REFERENCES = ('section-argument.md', 'report-language.md', 'reader-checklist.md',
                    'repair-contract.md', 'source-fidelity.md')


def drafting_references(folder, *, lean=False):
    """Keep legacy snapshots exact; new drafts realize already verified requests.

    Section discovery/checklist work belongs to Reader. Its frozen decisions and
    full manuscript remain in the draft context; only diagnostic instructions go.
    Missing section markers are errors, never permission to silently drop rules.
    """
    parts=[]
    for name in DRAFT_REFERENCES:
        if lean and name=='reader-checklist.md':
            continue
        text=(Path(folder)/name).read_text(encoding='utf-8')
        if lean and name=='section-argument.md':
            start=text.index('## From diagnosis to a revision proposal')
            end=text.index('## Generic Reader integration',start)
            text=text[start:end].rstrip()+'\n'
        parts.append('\n'+name+'\n'+text)
    return ''.join(parts)
