"""Neutral Poppler line coordinates, not inferred paragraphs or certified glyphs."""
import re
import xml.etree.ElementTree as ET


def parse_bbox(text,source_sha256,first_page=1):
    # Poppler sometimes emits control glyphs that XML cannot encode. Coordinates
    # remain usable; discarded control characters are explicitly counted.
    invalid=re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]');removed=len(invalid.findall(text))
    try:root=ET.fromstring(invalid.sub('',text))
    except ET.ParseError as error:raise ValueError('Unavailable layout XML: '+str(error)) from error
    pages=[]
    for number,page in enumerate(root.iter(),0):
        if page.tag.rsplit('}',1)[-1]!='page':continue
        index=len(pages)+first_page;lines=[]
        for item in page.iter():
            if item.tag.rsplit('}',1)[-1]!='line':continue
            words=[''.join(w.itertext()) for w in item if w.tag.rsplit('}',1)[-1]=='word']
            lines.append({'id':f'layout:p{index}:l{len(lines)+1}','page':index,'text':' '.join(words),
                'box':[float(item.attrib[k]) for k in ['xMin','yMin','xMax','yMax']]})
        pages.append({'page':index,'lines':lines})
    return {'version':1,'source_sha256':source_sha256,'pages':pages,'removed_control_characters':removed,
        'scope':'Extracted line text and PDF coordinates only. Images govern glyphs; no paragraph or column semantics inferred.'}


def indentation(geometry,facts):
    lines={l['id']:l for p in facts['pages'] for l in p['lines']}
    line=lines[geometry['line_ref']];column=lines[geometry['column_ref']]
    if line['page']!=column['page']:raise ValueError('Layout reference pages differ')
    result={**geometry,'line_x':line['box'][0],'column_x':column['box'][0]}
    for key in ['line_x','column_x']:
        if key in geometry and abs(geometry[key]-result[key])>0.0001:raise ValueError('Claimed geometry differs from frozen source coordinates')
    return result
