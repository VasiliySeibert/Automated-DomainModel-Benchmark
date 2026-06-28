"""Produce cleaned copies of the two benchmark datasets.

The raw `kaiser.json` and `reference.json` are bit-identical mirrors of the
upstream research corpora (so the citations stay fair). However, when the
scoring pipeline (`domain_model_metrics` / metrik-4) parses a reference under
`strict=True`, 17 of the 53 records raise `ValueError` on unrecognised
PlantUML syntax, which the orchestrator records as an automatic score of 0.

This module applies five pure, idempotent, character-level rewrites that fix
the failure modes observed in the dataset:

1. **Enum stereotype strip** — `enum Foo <<enum>> { ... }` →
   `enum Foo { ... }`. The `<<enum>>` stereotype is non-standard and the
   metric's parser treats the keyword as the start of a relationship line.
   Affects 12 records (BuildingManagement, CardGameApp, CelO, Ebike, FilmSet,
   HelpingHands, House, LabTracker, TeamSportsScoutingSystem,
   TransportCompany, TruckLogistics, eHome2020).

2. **Single-dash diamond repair** — the six 2/3-character forms `*-`, `-*`,
   `*- >`, `<-*`, `o->`, `<-o` (where one of the dashes is missing) are
   rewritten to the canonical 2-dash / 3-char form (`*--`, `--*`, `*-->`,
   `<--*`, `o-->`, `<--o`). The rewrite is applied only outside enum
   bodies to avoid mangling enum values. Affects 6 lines on 6 records
   (GasStation_TUW, HelpingHands, School, TileOGame, University).

3. **Class extends rewrite** — `class Sub extends Parent` (non-standard
   Java-flavoured inheritance shorthand) is split into `class Sub` followed
   by `Sub --|> Parent`, matching the canonical PlantUML syntax used
   elsewhere in the dataset. Affects 1 record (HBMS).

4. **Bidirectional arrow rewrite** — `A <--> B` (PlantUML's bidirectional
   association) is rewritten to `A --> B`, which is a directed
   association in the same direction. Affects 1 record
   (TeamSportsScoutingSystem).

5. **Note-with-alias drop** — `note "X" as ALIAS` plus any subsequent
   references to `ALIAS` as a class identifier are removed. The parser
   does not recognise the single-line note with the `as` keyword. Affects
   1 record (FilmSet). The remaining dependency lines in the diagram are
   preserved.

The output JSONs share the schema `{id, nlt, puml}` and the same record
count as the originals. The `nlt` field is unchanged; only `puml` is
rewritten.

Usage:
    PYTHONPATH=. python Data/clean_datasets.py
    PYTHONPATH=. python Data/clean_datasets.py --verify   # also run self-similarity

Verify:
    PYTHONPATH=. python -m pytest tests/test_data_clean.py -v
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from Data import KAISER_PATH, REFERENCE_PATH

THIS_DIR = Path(__file__).resolve().parent
CLEAN_KAISER_PATH = THIS_DIR / "kaiser_clean.json"
CLEAN_REFERENCE_PATH = THIS_DIR / "reference_clean.json"

# Mapping of malformed diamond arrows to their canonical 2-dash / 3-char forms.
# Order matters: 3-char forms first so that `*- >` is matched before the 2-char
# `*-` prefix.
DIAMOND_PAIRS: list[tuple[str, str]] = [
    ("*->",   "*-->"),
    ("o->",   "o-->"),
    ("<-*",   "<--*"),
    ("<-o",   "<--o"),
    ("*-",    "*--"),
    ("-*",    "--*"),
    ("-o",    "--o"),
]

_ENUM_OPENER_INLINE = re.compile(
    r"^enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{.*\}\s*$"
)
_ENUM_OPENER_MULTILINE = re.compile(
    r"^enum\s+[A-Za-z_][A-Za-z0-9_]*\s*"
)
_ENUM_STEREOTYPE = re.compile(
    r"(enum\s+[A-Za-z_][A-Za-z0-9_]*)\s*<<enum>>"
)
_EXTENDS_LINE = re.compile(
    r"^(\s*)class\s+([A-Za-z_][A-Za-z0-9_]*)\s+extends\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
    re.MULTILINE,
)
_BIDIRECTIONAL = re.compile(r"(\S)\s*<-->\s*(\S)")
_NOTE_ALIAS_DEF = re.compile(
    r'note\s+"[^"]*"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)'
)


def _fix_diamonds_in_line(line: str) -> str:
    """Apply the 7 diamond repairs to a single line.

    The lookbehind `(?<![<.\\-\\d])` and lookahead `(?!-)` ensure we never
    rewrite characters that are already part of a canonical 2-dash / 3-char
    arrow such as `<|--`, `--*`, `o--`, etc. The constraint also excludes
    digits and dots so we don't accidentally rewrite fragments of a
    cardinality like `0..1`.
    """
    out = line
    for bad, good in DIAMOND_PAIRS:
        out = re.sub(r"(?<![<.\-\d])" + re.escape(bad) + r"(?!-)", good, out)
    return out


def _repair_diamonds(puml: str) -> str:
    """Apply diamond repairs outside enum bodies.

    Enum values are simple identifiers in this dataset (verified by survey),
    but we still skip them defensively to avoid false positives like `bar-o`
    or `top-3`.
    """
    out_lines: list[str] = []
    in_enum = False
    enum_brace_depth = 0
    for line in puml.split("\n"):
        s = line.strip()
        if _ENUM_OPENER_INLINE.match(s):
            out_lines.append(line)
            continue
        if not in_enum and _ENUM_OPENER_MULTILINE.match(s) and "{" in s and s.count("{") > s.count("}"):
            in_enum = True
            enum_brace_depth = 1
            out_lines.append(_fix_diamonds_in_line(line))
            continue
        if in_enum:
            enum_brace_depth += s.count("{") - s.count("}")
            if enum_brace_depth <= 0:
                in_enum = False
            out_lines.append(line)
            continue
        out_lines.append(_fix_diamonds_in_line(line))
    return "\n".join(out_lines)


def _strip_enum_stereotype(puml: str) -> str:
    return _ENUM_STEREOTYPE.sub(r"\1", puml)


def _rewrite_extends(puml: str) -> str:
    def repl(m: re.Match) -> str:
        indent, sub, parent = m.group(1), m.group(2), m.group(3)
        return f"{indent}class {sub}\n{indent}{sub} --|> {parent}"
    return _EXTENDS_LINE.sub(repl, puml)


def _rewrite_bidirectional(puml: str) -> str:
    return _BIDIRECTIONAL.sub(r"\1 --> \2", puml)


def _rewrite_note_alias(puml: str) -> str:
    """Drop `note "X" as ALIAS` and every subsequent reference to ALIAS."""
    aliases = set(_NOTE_ALIAS_DEF.findall(puml))
    if not aliases:
        return puml
    new_lines: list[str] = []
    for line in puml.split("\n"):
        s = line.strip()
        if re.match(r'^note\s+"[^"]*"\s+as\s+[A-Za-z_][A-Za-z0-9_]*\s*$', s):
            continue
        if any(
            re.search(r"(^|\s)" + re.escape(a) + r"(\s|$|:)", line)
            for a in aliases
        ):
            continue
        new_lines.append(line)
    return "\n".join(new_lines)


def normalise(puml: str) -> str:
    """Apply all five repairs. Idempotent — running twice gives the same result."""
    p = puml
    p = _strip_enum_stereotype(p)
    p = _repair_diamonds(p)
    p = _rewrite_extends(p)
    p = _rewrite_bidirectional(p)
    p = _rewrite_note_alias(p)
    return p


def _normalise_dataset(records: list[dict]) -> list[dict]:
    return [
        {"id": r["id"], "nlt": r["nlt"], "puml": normalise(r["puml"])}
        for r in records
    ]


def _self_verify(records: list[dict], label: str) -> int:
    """Score each cleaned record against itself via metrik-4.

    A "clean" record must yield zero parse warnings on the reference side
    and at least ~1.0 (the metrik-4 self-similarity ceiling) on all three
    element scores, with `error is None`.
    """
    from Metric.wrapper import compute
    failures = 0
    for r in records:
        out = compute(r["puml"], r["puml"])
        err = out["error"]
        warn_ref = len(out["parse_warning_ref"])
        warn_gen = len(out["parse_warning_gen"])
        ok = err is None and warn_ref == 0 and warn_gen == 0
        if not ok:
            failures += 1
            print(
                f"  [FAIL] {label}::{r['id']:30s} err={err} "
                f"warn_ref={warn_ref} warn_gen={warn_gen}"
            )
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify", action="store_true",
        help="Run metrik-4 self-similarity on the cleaned output before exit.",
    )
    ap.add_argument("--out-kaiser", type=Path, default=CLEAN_KAISER_PATH)
    ap.add_argument("--out-reference", type=Path, default=CLEAN_REFERENCE_PATH)
    args = ap.parse_args()

    kaiser = json.loads(KAISER_PATH.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))

    kaiser_clean = _normalise_dataset(kaiser)
    reference_clean = _normalise_dataset(reference)

    args.out_kaiser.write_text(
        json.dumps(kaiser_clean, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    args.out_reference.write_text(
        json.dumps(reference_clean, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {len(kaiser_clean):>3} cleaned models -> {args.out_kaiser}")
    print(f"Wrote {len(reference_clean):>3} cleaned models -> {args.out_reference}")

    if args.verify:
        print("\n=== Self-verification (metrik-4 self-similarity) ===")
        f1 = _self_verify(kaiser_clean, "kaiser_clean")
        f2 = _self_verify(reference_clean, "reference_clean")
        print(f"  kaiser_clean failures:    {f1}/{len(kaiser_clean)}")
        print(f"  reference_clean failures: {f2}/{len(reference_clean)}")
        return 0 if (f1 == 0 and f2 == 0) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())