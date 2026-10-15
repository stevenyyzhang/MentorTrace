"""Reconcile model-normalized PDF text anchors to exact frozen page text.

The model output remains untouched. Every changed anchor and both hashes are
recorded alongside the normalized candidate for MentorTrace validation.
"""

import argparse
import copy
import unicodedata
import hashlib
import json
import re
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
    configuration = candidate.get('configuration_review', {})
    configuration_items = configuration.get('items', []) if isinstance(configuration, dict) else []
    if isinstance(configuration_items, list):
        for index, item in enumerate(configuration_items):
            if not isinstance(item, dict) or not isinstance(item.get('evidence'), list):
                continue
            for evidence_index, value in enumerate(item['evidence']):
                if not isinstance(value, str):
                    continue
                match = re.match(r'^Page\s+([1-9]\d*)\s+[^\d–-]', value)
                if not match or len(re.findall(r'\bPage\s+\d+\b', value)) != 1:
                    continue
                if re.match(r'^Page\s+\d+\s+(?:and|or|to)\s+\d', value):
                    continue
                page = int(match.group(1))
                if page not in pages:
                    continue
                converted = {'page': page, 'kind': 'image',
                    'description': 'Model-provided page locator (not a literal quotation or certified transcription): ' + value}
                item['evidence'][evidence_index] = converted
                type_changes.append({'path': f'configuration_review.items[{index}].evidence[{evidence_index}]',
                    'from': value, 'to': converted,
                    'reason': 'Explicit single available-page location serialized as an image locator. Complete original description retained; no inferred page, quotation or judgment.'})
    for path, anchor in iter_anchors(candidate):
        page = anchor.get("page")
        quote = anchor.get("quote", "")
        source = pages.get(page, "")
        try:
            mentortrace.anchor(anchor, pages)
            if quote and quote in source:
                continue
            reason = "Native normalized match is not a literal extraction quote"
        except ValueError as error:
            reason = str(error)
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
        for field in ["current_order", "proposed_order", "reason"]:
            value = suggestion.get(field)
            if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
                suggestion[field] = "\n".join(value)
                type_changes.append({"path": f"organization_suggestions[{index}].{field}",
                                     "from": value, "to": suggestion[field],
                                     "reason": "Ordered nonempty prose list serialized without changing its content."})
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
    for index, transfer in enumerate(candidate.get("writing_transfers", [])):
        for field in ["learned_distinction", "reader_task", "current_handling",
                      "proposed_action", "preserved_dependencies", "limits"]:
            value = transfer.get(field)
            if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
                transfer[field] = "\n".join(value)
                type_changes.append({"path": f"writing_transfers[{index}].{field}",
                                     "from": value, "to": transfer[field],
                                     "reason": "Ordered nonempty text list serialized without adding or removing content; source excerpts and judgments unchanged."})
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
        "policy": "Only complete unique text alignment under declared normalization is allowed; schema repairs are logged. Explicit single-page location descriptions may be serialized as image locators with the entire original description retained. No target-specific overrides, quotation-to-image conversions or judgment changes. Finding content is unchanged.",
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
    args.stage = mentortrace.naming.stage_id(args.stage)
    raw = args.raw or (args.run / "calls" / args.stage / "codex-authorized/final_text.json")
    output, changed, unresolved = normalize(args.run, args.stage, raw)
    print(json.dumps({"stage": args.stage, "module_name": mentortrace.naming.display_name(args.stage), "changed": changed,
                      "unresolved": len(unresolved), "output": str(output)}))


if __name__ == "__main__":
    main()
