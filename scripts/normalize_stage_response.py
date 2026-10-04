"""Reconcile model-normalized PDF text anchors to exact frozen page text.

The model output remains untouched. Every changed anchor and both hashes are
recorded alongside the normalized candidate for MentorTrace validation.
"""

import argparse
import copy
import unicodedata
import hashlib
import json
from pathlib import Path

import mentortrace_v1 as mentortrace

def normalized_text(text):
    result, offsets = [], []
    for index, char in enumerate(text):
        for item in unicodedata.normalize("NFKC", char):
            if not item.isspace() and item != "\u00ad":
                result.append(item)
                offsets.append((index, index + 1))
    return "".join(result), offsets


def iter_anchors(value, path=""):
    if isinstance(value, dict):
        if "page" in value and "quote" in value:
            yield path, value
        for key, child in value.items():
            yield from iter_anchors(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_anchors(child, f"{path}[{index}]")


def normalize(run: Path, stage: str, raw_path: Path):
    run = run.resolve()
    raw_path = raw_path.resolve()
    original = mentortrace.read(raw_path)
    candidate = copy.deepcopy(original)
    pages = {p["page"]: p["text"] for p in mentortrace.read(run / "inputs/paper/body.json")}
    changes = []
    unresolved = []
    type_changes = []
    for path, anchor in iter_anchors(candidate):
        try:
            mentortrace.anchor(anchor, pages)
            continue
        except ValueError as error:
            reason = str(error)
        page = anchor.get("page")
        quote = anchor.get("quote", "")
        source = pages.get(page, "")
        if not source or not quote:
            unresolved.append({"path": path, "page": page, "reason": reason})
            continue
        normalized_quote, _ = normalized_text(quote)
        normalized_source, offsets = normalized_text(source)
        start = normalized_source.find(normalized_quote) if normalized_quote else -1
        if start < 0 or normalized_source.find(normalized_quote, start + 1) >= 0:
            unresolved.append({"path": path, "page": page, "reason": reason,
                               "alignment": "complete unique normalized quote not found"})
            continue
        stop = start + len(normalized_quote)
        replacement = source[offsets[start][0]:offsets[stop - 1][1]]
        anchor["quote"] = replacement
        mentortrace.anchor(anchor, pages)
        changes.append({"path": path, "page": page,
                        "old_quote": quote, "exact_frozen_page_quote": replacement,
                        "reason": "Complete unique match after whitespace, soft-hyphen and Unicode compatibility normalization; no fuzzy fragment or image conversion."})
    for index, suggestion in enumerate(candidate.get("organization_suggestions", [])):
        links = suggestion.get("affected_links")
        if isinstance(links, list) and all(isinstance(link, str) for link in links):
            suggestion["affected_links"] = "; ".join(links)
            type_changes.append({"path": f"organization_suggestions[{index}].affected_links",
                                 "from": links, "to": suggestion["affected_links"]})
        conditions = suggestion.get("conditions")
        if isinstance(conditions, list) and all(isinstance(item, str) for item in conditions):
            suggestion["conditions"] = "; ".join(conditions)
            type_changes.append({"path": f"organization_suggestions[{index}].conditions",
                                 "from": conditions, "to": suggestion["conditions"]})
    evidence = candidate.get("evidence_requests")
    if isinstance(evidence, list) and evidence and all(isinstance(item, str) for item in evidence):
        limits = candidate.setdefault("limits", [])
        mentortrace.require(isinstance(limits, list), "Cannot preserve textual evidence limits")
        for item in evidence:
            if item not in limits:
                limits.append(item)
        candidate["evidence_requests"] = []
        type_changes.append({"path": "evidence_requests", "from": evidence,
                             "to": "limits", "reason": "Textual external/conditional limitations lack required card_id; retained as limits."})
    elif isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if isinstance(item, dict) and not item.get("reason") and isinstance(item.get("purpose"), str):
                item["reason"] = item.pop("purpose")
                type_changes.append({"path": f"evidence_requests[{index}]",
                                     "change": "purpose renamed reason without changing its text"})
    folder = raw_path.parent
    output_path = folder / "normalized_response.json"
    log_path = folder / "anchor_normalization.json"
    output_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    log_path.write_text(json.dumps({
        "model_output_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "normalized_response_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "policy": "Only complete unique text alignment under declared normalization is allowed; schema repairs are logged. No target-specific overrides, image conversions or judgment changes. Finding content is unchanged.",
        "changes": changes,
        "type_changes": type_changes,
        "unresolved": unresolved,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path, len(changes), unresolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--raw", type=Path)
    args = parser.parse_args()
    raw = args.raw or (args.run / "calls" / args.stage / "codex-authorized/final_text.json")
    output, changed, unresolved = normalize(args.run, args.stage, raw)
    print(json.dumps({"stage": args.stage, "changed": changed,
                      "unresolved": len(unresolved), "output": str(output)}))


if __name__ == "__main__":
    main()
