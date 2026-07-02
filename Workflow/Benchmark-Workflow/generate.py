#!/usr/bin/env python3
"""Workflow/Benchmark-Workflow/generate.py — step 1 of the benchmark pipeline.

Invokes a Candidate against every record in one dataset and writes
the raw `(nlt, generated, reference)` triples to a JSON file.

Usage:
    PYTHONPATH=. python Workflow/Benchmark-Workflow/generate.py \
        --candidate Candidates/dummy_candidate/candidate.py \
        --dataset kaiser_clean \
        --out Workflow/Results/dummy_candidate/kaiser_clean.json

Optional:
    --limit N         run only the first N records of the dataset.

Output JSON schema:
    {
      "candidate":  "Candidates/dummy_candidate/candidate.py",
      "dataset":    "kaiser_clean",
      "n_records":  45,
      "n_failed":   0,
      "elapsed_seconds": 12.3,
      "records": [
        {
          "id":              "AirTravel",
          "nlt":             "...",
          "reference":       "@startuml ... @enduml",
          "generated":       "@startuml ... @enduml",
          "failed":          false,
          "error":           null,
          "raw_excerpt":     "...",
          "elapsed_seconds": 0.04
        },
        ...
      ]
    }

No metric scoring happens here. `Workflow/Benchmark-Workflow/score.py` reads this file.

Available datasets:
    kaiser_clean       (45 records, Data/data-source-1/)
    reference_clean    (8 records,  Data/data-source-2/)
    data-source-1      (alias for kaiser_clean)
    data-source-2      (alias for reference_clean)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Candidates.candidate_interface import load_candidate, reconfigure_candidate
from Data import load_dataset


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.generate")


def _run_one(candidate, row: dict) -> dict:
    """Invoke the candidate on one row; never raise."""
    rid = row["id"]
    nlt = row["nlt"]
    ref = row["puml"]
    t0 = time.time()
    try:
        out = candidate(nlt)
        elapsed = round(time.time() - t0, 3)
        return {
            "id":              rid,
            "nlt":             nlt,
            "reference":       ref,
            "generated":       out.generated_model,
            "failed":          bool(out.failed),
            "error":           out.error,
            "raw_excerpt":     out.raw_excerpt,
            "elapsed_seconds": elapsed,
        }
    except Exception as exc:
        log.error("candidate raised on %s: %s", rid, exc)
        elapsed = round(time.time() - t0, 3)
        return {
            "id":              rid,
            "nlt":             nlt,
            "reference":       ref,
            "generated":       "",
            "failed":          True,
            "error":           f"exception: {type(exc).__name__}: {exc}",
            "raw_excerpt":     "",
            "elapsed_seconds": elapsed,
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", required=True,
                    help="Path to candidate.py OR to a folder containing it.")
    ap.add_argument("--dataset", required=True,
                    choices=["kaiser_clean", "reference_clean",
                             "data-source-1", "data-source-2"],
                    help="Dataset name (or data-source-N alias).")
    ap.add_argument("--out", required=True, help="Output JSON path.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Run only the first N records.")
    ap.add_argument("--settings-json", default=None,
                    help="Optional JSON object string of resolved candidate "
                         "settings (model, temperature, etc.). If the "
                         "candidate's class accepts any of these kwargs, "
                         "the candidate is re-instantiated with them before "
                         "running. Default: no reconfiguration.")
    args = ap.parse_args(argv)

    candidate_path = Path(args.candidate).resolve()
    candidate = load_candidate(candidate_path)
    log.info("loaded candidate from %s", candidate_path)

    if args.settings_json:
        try:
            settings = json.loads(args.settings_json)
        except json.JSONDecodeError as exc:
            log.error("--settings-json is not valid JSON: %s", exc)
            return 1
        if isinstance(settings, dict):
            reconfigure_candidate(candidate, settings)
        else:
            log.warning("--settings-json must decode to an object; ignoring")

    rows = load_dataset(args.dataset)
    if args.limit is not None:
        rows = rows[: args.limit]
    log.info("dataset %s: %d records", args.dataset, len(rows))

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    records: list[dict] = []
    for i, row in enumerate(rows, 1):
        rec = _run_one(candidate, row)
        records.append(rec)
        log.info(
            "  [%d/%d] %-30s  %.2fs  failed=%s",
            i, len(rows), rec["id"], rec["elapsed_seconds"], rec["failed"],
        )

    payload = {
        "candidate":       str(candidate_path),
        "dataset":         args.dataset,
        "n_records":       len(records),
        "n_failed":        sum(1 for r in records if r["failed"]),
        "elapsed_seconds": round(time.time() - t0, 2),
        "records":         records,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "wrote %s (%d records, %d failed, %.1fs)",
        out_path, payload["n_records"], payload["n_failed"], payload["elapsed_seconds"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())