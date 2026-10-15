"""Current reviewer names over stable, versioned storage/schema identifiers.

Never rewrite manuscript text, frozen corpus records, IDs or old requests.
"""
import re

NAMES = {'reader': 'Reader', 'technical': 'Expert', 'supplement': 'Advisor', 'language': 'Editor'}
ALIASES = {'expert': 'technical', 'editor': 'language'}
REFERENCES = {'technical-checks.md': 'expert-checks.md',
              'goodpaper-technical.md': 'goodpaper-expert.md',
              'language-surface.md': 'editor-surface.md'}


def stage_id(name):
    return ALIASES.get(name, name)


def display_name(stage):
    stage = stage_id(stage)
    if stage == 'advisor_tasks' or stage.startswith(('supplement_', 'evidence_')):
        return 'Advisor'
    return NAMES.get(stage, {'objects': 'Planning', 'merge': 'Merge', 'verify': 'Verify'}.get(stage, stage))


def reference_name(name, current):
    if current:
        return REFERENCES.get(name, name)
    return {value: key for key, value in REFERENCES.items()}.get(name, name)


def current_instructions(text):
    """Apply only to authored instruction prose, never the INPUT payload."""
    text = re.sub(r'\bTechnical\b(?! (?:validity|correctness))', 'Expert', text)
    text = re.sub(r'\bLanguage\b(?! (?:and presentation|and surface|comments|order))', 'Editor', text)
    for old, new in REFERENCES.items():
        text = text.replace(old, new)
    return text
