"""Inspect dependencies locally; no network or manuscript access."""
import importlib.metadata
import json
import shutil
import sys

if __name__ == '__main__':
    packages = {}
    for name in ['lxml', 'pypdf']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    tools = {name: bool(shutil.which(name)) for name in ['pandoc', 'pdftotext', 'pdftoppm', 'codex']}
    tools['browser_on_path'] = any(shutil.which(name) for name in ['chrome', 'google-chrome', 'chromium', 'msedge'])
    print(json.dumps({'python': sys.version.split()[0], 'packages': packages, 'tools': tools,
                      'note': 'A browser can also be passed explicitly to the PDF renderer. Model access and context capacity require separate verification.'}, indent=2))
    raise SystemExit(0 if sys.version_info >= (3, 10) and all(packages.values()) else 1)
