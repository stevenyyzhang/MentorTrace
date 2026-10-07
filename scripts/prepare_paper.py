"""Prepare local annotation-free pages; inspect burned-in comments manually."""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
import mentortrace_v1 as m

def prepare(source, output, *, text_tool='pdftotext', image_tool='pdftoppm', dpi=150):
    source, output = Path(source).resolve(), Path(output).resolve()
    m.require(not output.exists(), 'Output already exists; preserve prior package')
    m.require(shutil.which(text_tool) and shutil.which(image_tool), 'Install Poppler or supply executable paths')
    m.require(dpi >= 72, 'Page images need a readable resolution')
    with tempfile.TemporaryDirectory(prefix='mentortrace-paper-') as temp:
        work = Path(temp)
        reader = PdfReader(source)
        writer = PdfWriter()
        for page in reader.pages:
            page.pop(NameObject('/Annots'), None)
            writer.add_page(page)
        clean = work / 'annotation-free.pdf'
        with clean.open('wb') as stream:
            writer.write(stream)
        result = subprocess.run([text_tool, '-layout', str(clean), '-'], check=True, capture_output=True, encoding='utf-8', errors='replace')
        texts = result.stdout.split('\f')
        if texts and not texts[-1].strip():
            texts.pop()
        m.require(len(texts) == len(reader.pages), 'Extracted page count differs from PDF')
        images = work / 'images'
        images.mkdir()
        subprocess.run([image_tool, '-png', '-r', str(dpi), str(clean), str(images / 'page')], check=True, capture_output=True)
        raw = sorted(images.glob('page-*.png'), key=lambda path: int(path.stem.rsplit('-', 1)[1]))
        m.require(len(raw) == len(texts), 'Rendered page count differs from text')
        normalized = work / 'normalized-images'
        normalized.mkdir()
        for number, path in enumerate(raw, 1):
            shutil.copy2(path, normalized / f'page-{number:04d}.png')
        body = work / 'body.json'
        m.save(body, [{'page': number, 'text': text} for number, text in enumerate(texts, 1)])
        m.import_paper(body, normalized, source, output, m.sha(source))
    return {'pages': len(texts), 'annotation_objects_removed': True,
            'text_extraction_fidelity': 'Not certified; raw extraction locates evidence, original page images govern glyphs.',
            'required_manual_check': 'Inspect burned-in comments, text/image correspondence, decisive formula delimiters/operators and the physical placement of split words.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pdftotext', default='pdftotext')
    parser.add_argument('--pdftoppm', default='pdftoppm')
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()
    print(m.dump(prepare(args.pdf, args.out, text_tool=args.pdftotext, image_tool=args.pdftoppm, dpi=args.dpi)))
