"""Lossless author-facing numbering; never merge scientific requirements here."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

HEADING = re.compile(r'^(#{3,4} )(\d+)\. (.+?)(?: \(also ([\d, ]+)\))?$', re.M)
NUMBERS = r'\d+(?:(?:,\s*(?:and\s+)?|\s+and\s+|、|\s*[–—-]\s*)\d+)*'
EN = re.compile(r'\b((?:(?:content(?: and technical)?|technical|organization(?: and flow)?|language(?: and presentation)?)\s+)?comments?)\s+(' + NUMBERS + r')\b', re.I)
ZH = re.compile(r'((?:内容与技术|篇章与行文|语言与格式)?意见\s*|第\s*)(' + NUMBERS + r')(\s*条(?:的统一修改(?:动作|方案))?)?')

CATEGORIES = ('technical', 'organization', 'language')
LABELS = {'technical': ('content and technical', '内容与技术意见'),
          'organization': ('organization and flow', '篇章与行文意见'),
          'language': ('language and presentation', '语言与格式意见')}

def section_kind(line):
    if not line.startswith('## '):
        return None
    for key, terms in [('technical', ('Content and technical comments', '内容与技术意见')),
                       ('organization', ('Organization and flow comments', '篇章与行文意见')),
                       ('language', ('Language and presentation comments', '语言与格式意见')),
                       ('coverage', ('Coverage and remaining checks', '覆盖范围与待核对事项')),
                       ('usage', ('How to use this report', '使用说明'))]:
        if any(term in line for term in terms):
            return key
    return 'other'

def normalize(text: str) -> tuple[str, dict]:
    """Normalize per category, preserving source IDs and exact Original fields.

    Globally unique legacy IDs are accepted; repeated IDs across categories imply
    category-local input. References in that format use explicit category labels
    across sections and the current category for unqualified local references.
    """
    protected = []
    def shield(match):
        protected.append(match[0])
        return f'\x00MT_NUMBERING_{len(protected)-1}\x00'
    if '\x00MT_NUMBERING_' in text:
        raise ValueError('Reserved numbering sentinel in input')
    work = re.sub(r'^(```|~~~)[^\n]*\n[\s\S]*?^\1[^\n]*(?:\n|$)', shield, text, flags=re.M)
    work = re.sub(r'^\*\*Original:\*\*[^\n]*(?:\n(?!#{1,6}\s|\*\*[^\n*]+[:：]\*\*|---\s*$)[^\n]*)*', shield, work, flags=re.M)
    rows, mapping, globally = [], {}, {}
    counters = dict.fromkeys(CATEGORIES, 0)
    current = None
    lines = work.splitlines(keepends=True)
    for line in lines:
        current = section_kind(line) or current
        m = HEADING.fullmatch(line.rstrip('\r\n'))
        if not m:
            continue
        if current not in CATEGORIES:
            raise ValueError('Numbered opinion outside a comment category')
        counters[current] += 1
        ids = [int(m[2])] + [int(i) for i in re.findall(r'\d+', m[4] or '')]
        for old in ids:
            if (current, old) in mapping:
                raise ValueError(f'Duplicate opinion identity in {current}: {old}')
            target = (current, counters[current])
            mapping[current, old] = target
            globally.setdefault(old, []).append(target)
        rows.append({'category':current, 'display_number':counters[current], 'source_numbers':ids, 'title':m[3]})
    if not rows:
        raise ValueError('No numbered comments found')
    global_input = all(len(v) == 1 for v in globally.values())
    def explicit_category(prefix):
        for key, terms in [('technical', ('content', 'technical', '内容与技术')),
                           ('organization', ('organization', '篇章与行文')),
                           ('language', ('language', '语言与格式'))]:
            if any(t in prefix.lower() for t in terms):
                return key
        return None
    def resolve(value, prefix, current):
        requested = explicit_category(prefix)
        targets=[]
        for token in re.findall(r'\d+\s*[–—-]\s*\d+|\d+', value):
            ends=[int(i) for i in re.findall(r'\d+',token)]
            if ends[-1] < ends[0]:
                raise ValueError('Descending opinion range')
            for old in range(ends[0],ends[-1]+1):
                target = globally.get(old, [None])[0] if global_input else mapping.get((requested or current,old))
                if target is None or (requested and requested != target[0]):
                    raise ValueError(f'Dangling or wrong-category reference: {prefix} {old}')
                if target not in targets:
                    targets.append(target)
        if len({t[0] for t in targets}) != 1:
            raise ValueError('Mixed-category reference list; qualify each category separately')
        return targets[0][0], [str(t[1]) for t in targets]
    output=[];current=None
    for line in lines:
        current=section_kind(line) or current
        m=HEADING.fullmatch(line.rstrip('\r\n'))
        if m:
            output.append(f'{m[1]}{mapping[current,int(m[2])][1]}. {m[3]}' + line[len(line.rstrip('\r\n')):])
            continue
        def english(m):
            cat, ids=resolve(m[2],m[1],current)
            return LABELS[cat][0] + (' comment ' if len(ids)==1 else ' comments ') + (ids[0] if len(ids)==1 else ', '.join(ids[:-1])+' and '+ids[-1])
        def chinese(m):
            if m[1].startswith('第') and not m[3]:
                return m[0]
            cat,ids=resolve(m[2],m[1],current)
            if m[1].startswith('第') and cat==current:
                return '第 '+ '、'.join(ids)+(m[3] or '')
            return LABELS[cat][1]+' '+ '、'.join(ids)+(m[3] or '')
        output.append(ZH.sub(chinese,EN.sub(english,line)))
    work=''.join(output)
    for i,value in enumerate(protected):
        work=work.replace(f'\x00MT_NUMBERING_{i}\x00',value)
    return work, {'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
                  'display_sha256':hashlib.sha256(work.encode()).hexdigest(),
                  'count':len(rows), 'section_counts':counters, 'number_map':rows}

def validate_report(text):
    """Mechanical delivery gate; semantic accuracy of coverage is reviewed separately."""
    order=[]; current=None; numbers={key:[] for key in CATEGORIES}; coverage=[]
    for line in text.splitlines():
        kind=section_kind(line)
        if kind:
            order.append(kind);current=kind
        m=HEADING.fullmatch(line)
        if m:
            if current not in numbers or m[4]:
                raise ValueError('Opinion outside its category or visible internal alias')
            numbers[current].append(int(m[2]))
        if current=='coverage' and not kind:
            coverage.append(line)
    if order != ['usage',*CATEGORIES,'coverage']:
        raise ValueError('Required report sections missing, duplicated or out of order')
    for key,ids in numbers.items():
        if ids != list(range(1,len(ids)+1)):
            raise ValueError(f'Nonconsecutive category numbering: {key}')
    body='\n'.join(coverage).strip()
    if not re.search(r'[A-Za-z]{3,}',body) or not re.search(r'[\u3400-\u9fff]',body):
        raise ValueError('Coverage must contain substantive English and Chinese notes')
    # Re-resolve every visible reference in the scoped namespace, without repair.
    again,_=normalize(text)
    if again!=text:
        raise ValueError('References or category numbering are not canonical')
    return {'section_counts':{key:len(v) for key,v in numbers.items()},
            'coverage_present':True, 'coverage_semantics_verified':False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--markdown', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--map', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.map.exists():
        raise FileExistsError('Preserve existing reports/maps; use fresh output paths')
    result, record = normalize(args.markdown.read_text(encoding='utf-8'))
    validate_report(result)
    args.output.write_text(result, encoding='utf-8')
    args.map.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
