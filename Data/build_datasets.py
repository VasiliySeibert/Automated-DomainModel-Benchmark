"""Build the two benchmark datasets from their source repositories.

Outputs:
    Data/kaiser.json    — 45 synthetic domain models (Kaiser 2026).
    Data/reference.json — 8 reference models (ReferenceModels-and-NLT).

Both JSONs share the same schema: a list of {"id", "nlt", "puml"} entries.

Sources:
    Kaiser:   https://github.com/VasiliySeibert/text2uml-kaiser (mirror)
              /Users/vasiliy/Documents/GitHub/text2uml-kaiser/dataset/<Model>/
                  description.md   — natural-language text
                  plantuml.txt     — reference PlantUML class diagram

    Reference: https://github.com/VasiliySeibert/ReferenceModels-and-NLT
              /Users/vasiliy/Desktop/ReferenceModels-and-NLT/automated-archive/
                  groundTruthWithPlantUML.json
                  Each entry has model_id, full_name, nl_text, plant_uml.

Usage:
    python Data/build_datasets.py
    python Data/build_datasets.py --kaiser-root <path> --reference-root <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_KAISER_ROOT = Path(
    "/Users/vasiliy/Documents/GitHub/text2uml-kaiser/dataset"
)
DEFAULT_REFERENCE_ROOT = Path(
    "/Users/vasiliy/Desktop/ReferenceModels-and-NLT/automated-archive"
)
THIS_DIR = Path(__file__).resolve().parent


def build_kaiser(root: Path) -> list[dict]:
    """Walk <root>/<Model>/ and emit one entry per folder."""
    if not root.is_dir():
        raise FileNotFoundError(f"Kaiser dataset root not found: {root}")
    entries: list[dict] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        desc = sub / "description.md"
        puml = sub / "plantuml.txt"
        if not (desc.is_file() and puml.is_file()):
            continue
        nlt = desc.read_text(encoding="utf-8").strip()
        puml_text = puml.read_text(encoding="utf-8").strip()
        entries.append(
            {
                "id": sub.name,
                "nlt": nlt,
                "puml": puml_text,
            }
        )
    return entries


def build_reference(root: Path) -> list[dict]:
    """Read groundTruthWithPlantUML.json and normalise schema."""
    src = root / "groundTruthWithPlantUML.json"
    if not src.is_file():
        raise FileNotFoundError(f"Reference dataset not found: {src}")
    raw = json.loads(src.read_text(encoding="utf-8"))
    entries: list[dict] = []
    for model_id, payload in raw.items():
        entries.append(
            {
                "id": payload.get("model_id", model_id),
                "nlt": payload["nl_text"].strip(),
                "puml": payload["plant_uml"].strip(),
            }
        )
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kaiser-root", type=Path, default=DEFAULT_KAISER_ROOT)
    ap.add_argument("--reference-root", type=Path, default=DEFAULT_REFERENCE_ROOT)
    ap.add_argument(
        "--out-kaiser", type=Path, default=THIS_DIR / "kaiser.json"
    )
    ap.add_argument(
        "--out-reference", type=Path, default=THIS_DIR / "reference.json"
    )
    args = ap.parse_args()

    kaiser = build_kaiser(args.kaiser_root)
    reference = build_reference(args.reference_root)

    args.out_kaiser.write_text(
        json.dumps(kaiser, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    args.out_reference.write_text(
        json.dumps(reference, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Wrote {len(kaiser):>3} models -> {args.out_kaiser}")
    print(f"Wrote {len(reference):>3} models -> {args.out_reference}")
    return 0


if __name__ == "__main__":
    sys.exit(main())