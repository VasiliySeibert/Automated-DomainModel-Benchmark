"""Build the per-record case-study markdown files in out/examples/.

We pick five representative records and produce a self-contained markdown
page for each, with NLT excerpt, diagram summary, lex-match table, and
sample dep-graph bindings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CASES = [
    ("kaiser", "BankAccount", "Short NLT, simple diagram"),
    ("kaiser", "AirTravel", "Mid-length, classic NLT-for-class-diagram textbook example"),
    ("kaiser", "CelO", "Domain model with multiple inheritance and roles"),
    ("reference", "LabTracker", "Long, complex NLT with enum-heavy model"),
    ("kaiser", "BusTransportationManagementSystem", "Fielded NLT with explicit BTMS acronym"),
]


def _truncate(text: str, n: int = 700) -> str:
    if len(text) <= n:
        return text
    return text[:n] + f"\n\n[…truncated, total {len(text)} chars]"


def _bullet(s: str) -> str:
    return s.replace("\n", "  \n  ")


def _make_example(dataset: str, rec_id: str, blurb: str,
                  sidecars: dict, out_dir: Path):
    key = f"{dataset}::{rec_id}"
    if key not in sidecars:
        return
    s = sidecars[key]
    diagram = s["diagram"]
    matches = s["matches"]
    cab = s["class_attr_bindings"]
    rb = s["rel_bindings"]
    nlt = s["nlt"]

    lines = []
    lines.append(f"# {rec_id} ({dataset}) — {blurb}\n")
    words = re.findall(r"\b\w+\b", nlt)
    sents = re.split(r"(?<=[.!?])\s+", nlt.strip())
    lines.append(f"**NLT length:** {len(nlt)} chars, {len(words)} words, "
                 f"{len(sents)} sentences\n")
    lines.append("\n## Natural language text (excerpt)\n")
    lines.append("```")
    lines.append(_truncate(nlt, 1200))
    lines.append("```\n")
    lines.append("\n## Diagram summary\n")
    lines.append(f"- {len(diagram['classes'])} classes, {len(diagram['enums'])} enums, "
                 f"{len(diagram['relationships'])} relationships\n")
    if diagram["classes"]:
        lines.append("### Classes and their attributes\n")
        lines.append("| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |")
        lines.append("|---|---|---|---|---|---|---|---|")
        cmap = {c["name"]: c for c in matches["classes"]}
        for c in diagram["classes"]:
            attr_str = ", ".join(f"{a['name']}" + (f" ({a['type']})" if a['type'] else "")
                                 for a in c["attributes"]) or "—"
            m = cmap.get(c["name"], {})
            lines.append(f"| {c['name']} | {c['is_abstract']} | {_bullet(attr_str)[:200]} | "
                         f"{'✓' if m.get('L1_direct') else '✗'} | "
                         f"{'✓' if m.get('L2_lemma') else '✗'} | "
                         f"{'✓' if m.get('L3_camelcase') else '✗'} | "
                         f"{'✓' if m.get('L4_synonym') else '✗'} | "
                         f"{'**YES**' if m.get('absent') else 'no'} |")
    lines.append("\n### Relationships\n")
    lines.append("| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |")
    lines.append("|---|---|---|---|---|---|---|---|")
    rmap = {(r["source"], r["target"]): r for r in matches["relationships"]}
    for r in diagram["relationships"]:
        m = rmap.get((r["source"], r["target"]), {})
        lines.append(f"| {r['source']} | {r['type']} | {r['target']} | "
                     f"{r.get('source_card') or '—'} | {r.get('target_card') or '—'} | "
                     f"{r.get('label') or '—'} | "
                     f"{'**YES**' if m.get('source_absent') else 'no'} | "
                     f"{'**YES**' if m.get('target_absent') else 'no'} |")
    lines.append("\n## Lex-match — interesting cases\n")
    absent_classes = [c for c in matches["classes"] if c["absent"]]
    if absent_classes:
        lines.append("\nClasses that are **lexically absent** in the NLT "
                     "(no L1, L2, L3 or L4 match):\n")
        for c in absent_classes:
            lines.append(f"- `{c['name']}` — sentence indices with token hits: "
                         f"{c['sent_indices']}")
    absent_attrs = [a for a in matches["attributes"] if a["absent"]]
    if absent_attrs:
        lines.append("\nAttributes that are **lexically absent** in the NLT:\n")
        for a in absent_attrs:
            lines.append(f"- `{a['class']}.{a['name']}` (type: {a['type'] or '—'}) — "
                         f"sentence indices: {a['sent_indices']}")
    lines.append("\n## Dependency-graph bindings (first 8)\n")
    if cab:
        lines.append("\n### Class↔Attribute\n")
        lines.append("| Class | Attribute | Sentence | Path | Hops |")
        lines.append("|---|---|---|---|---|")
        for b in cab[:8]:
            lines.append(f"| {b['class']} | {b['attribute']} | "
                         f"#{b['sent_i']} | `{b['path_text']}` | {b['hop_count']} |")
    if rb:
        lines.append("\n### Class↔Relationship (best path per relationship)\n")
        lines.append("| Source | Type | Target | # sentences | Best path | Hops |")
        lines.append("|---|---|---|---|---|---|")
        for b in rb:
            best = b["best"]
            lines.append(f"| {b['source']} | {b['type']} | {b['target']} | "
                         f"{b['n_sentences_with_both']} | `{best['path_text']}` | "
                         f"{best['hop_count']} |")

    out = out_dir / f"{dataset}_{rec_id}.md"
    out.write_text("\n".join(lines))
    print(f"[example] {out}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True,
                    help="path to per_record.jsonl")
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()
    sidecars = {}
    with open(args.inp) as f:
        for line in f:
            r = json.loads(line)
            sidecars[f"{r['dataset']}::{r['id']}"] = r
    out_dir = Path(args.outp)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ds, rid, blurb in CASES:
        _make_example(ds, rid, blurb, sidecars, out_dir)


if __name__ == "__main__":
    main()
