"""Deterministic page/caption/equation-label locators, never visual certification."""
import re
from collections import Counter

INSTRUCTIONS='''MANUSCRIPT LOCATORS v1: INPUT.manuscript_locators supplies page-image,
caption and equation-label candidates. Return {"$object_anchor":"locator id"} to
reference the selected page/object without copying extraction text. Inspect the
actual supplied page image before making a visual claim. A candidate label is NOT
certified formula transcription, object extent or a confirmed definition rather
than a reference. Repeated labels remain ambiguous; choose the specific page/line
candidate only after inspection. Extraction can miss objects. For unlisted objects
use a page locator plus a concrete visual description via $image_anchor; never
invent an object ID. Ordinary $anchor references still copy exact text passages.
These locators do not restrict full-paper review or certify any substantive claim.'''

def catalogue(context):
    result=[]
    for page in context['manuscript']:
        number=page['page']
        result.append({'id':f'IMG:P{number}','kind':'page_image','page':number,
          'label':None,'passage_id':None,'ambiguous_label':False,
          'status':'page_only_not_object_localization'})
        lines=page['text'].splitlines(keepends=True)
        for i,line in enumerate(lines,1):
            stripped=line.strip()
            caption=re.match(r'^(Fig(?:ure)?\.?|Table)\s+([0-9]+[a-z]?|[IVXLCDM]+)(?:\s*[:.]|\s*$)',stripped,re.I)
            if caption:
                kind='figure' if caption[1].lower().startswith('fig') else 'table'
                label=caption[2]
            else:
                # Two-column extraction may append the opposite column after a
                # displayed equation label. Keep uncertain candidates explicit.
                equation=re.search(r'\(([0-9]+[a-z]?)\)',stripped)
                if not equation:continue
                prefix=stripped[:equation.start()].strip()
                suffix=stripped[equation.end():].strip()
                if prefix and not any(c in prefix for c in '=∈≤≥∑∫∀→≜≈⊂π×−|'):
                    continue
                if not prefix and re.match(r'^(can|is|are|was|were|shows?|gives?|implies?|denotes?)\b',suffix,re.I):
                    continue
                kind='equation';label=equation[1]
            result.append({'id':f'{kind.upper()}:P{number}:L{i}','kind':kind,'label':label,'page':number,
              'passage_id':f'P{number}.{i}',
              'status':'unverified_label_candidate','ambiguous_label':False})
    counts=Counter((r['kind'],r['label']) for r in result if r['label'] is not None)
    for r in result:
        if r['label'] is not None:r['ambiguous_label']=counts[r['kind'],r['label']]>1
    return result

def expand(ident,context):
    if context.get('advisor_locators')!=1 or not isinstance(ident,str):
        raise ValueError('Unpinned or invalid object locator')
    found={r['id']:r for r in catalogue(context)}
    if ident not in found:raise ValueError('Unknown object locator')
    item=found[ident]
    if item['kind']=='page_image':description=f"Original supplied page {item['page']}; inspect the image for the actual object."
    else:description=f"{item['kind'].capitalize()} label {item['label']}, page {item['page']}, extracted line {item['passage_id'].rsplit('.',1)[1]}; verify against the original page image."
    return {'page':item['page'],'kind':'image','description':description}
