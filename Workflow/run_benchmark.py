#!/usr/bin/env python3
"""Workflow/run_benchmark.py — interruptible, resumable benchmark harness.

Runs the benchmark pipeline across the Cartesian product of:

    candidates × llms × datasets × run-indices

with a **persistent on-disk joblist** for interruption + resume,
per-subprocess log capture, per-invocation cache isolation (so
concurrent workers never collide), and a `tqdm` progress bar.

The default matrix is the reduced 3-candidate design:

    rule_based  (no LLM)
    zenodo_zero_shot        (AutomatedDomainModelling_zenodo/zero_shot)
    kaiser_zero_shot        (text2uml-kaiser/zero_shot)

    3 LLMs: minimax-m3:cloud, glm-5.1:cloud, kimi-k2.6:cloud
    2 datasets: kaiser_clean, reference_clean
    3 run-indices: 1, 2, 3

    Total = 6 (rule_based) + 18 (zenodo) + 18 (kaiser) = 42 jobs.

Joblist semantics
-----------------
On startup, the harness writes (or updates) ``--out-dir/.joblist.json``
with one entry per job, status ``pending``. As each job completes the
status becomes ``done`` (or ``failed``) and the entry is updated with
``rc``, ``wall_seconds``, ``artifact``, ``log``. The joblist is the
source of truth for "what still needs to run".

Resume: on the next launch with the same ``--out-dir``, any job whose
artifact JSON is well-formed AND matches the requested
``(candidate, llm, dataset, run_index)`` is left as ``done``; the rest
are re-queued. So Ctrl-C + restart picks up where you left off.

Concurrency
-----------
``--workers N`` controls how many jobs run in parallel. Each
subprocess gets its own ``Workflow/Results/cache/pidNNN_wNNN_tNNN/``
subdir so the driver's per-run cache wipe never takes down a sibling.

Cancellation
------------
SIGINT (Ctrl-C) sets a flag. In-flight subprocesses are *not* killed
mid-stream (an LLM call in flight is left to finish — interrupting
Ollama mid-call is a known footgun). Queued jobs are abandoned and
the joblist is updated to ``cancelled`` for any ``in_progress`` jobs.
On the next launch, ``cancelled`` jobs are re-queued automatically.

Usage
-----
::

    PYTHONPATH=. python Workflow/run_benchmark.py
    PYTHONPATH=. python Workflow/run_benchmark.py --list
    PYTHONPATH=. python Workflow/run_benchmark.py --status
    PYTHONPATH=. python Workflow/run_benchmark.py --reset
    PYTHONPATH=. python Workflow/run_benchmark.py --workers 6 --llms minimax-m3:cloud
    PYTHONPATH=. python Workflow/run_benchmark.py --candidates rule_based kaiser_zero_shot
    PYTHONPATH=. python Workflow/run_benchmark.py --rerun-failed
    PYTHONPATH=. python Workflow/run_benchmark.py --no-resume
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tqdm import tqdm


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR_DEFAULT = REPO_ROOT / "Workflow" / "Results" / "runs"


# ---------------------------------------------------------------------------
# Candidate registry.
# ---------------------------------------------------------------------------
# (kind, candidate_id, driver_path, strategy_arg_or_None)

CANDIDATES: list[tuple[str, str, str, Optional[str]]] = [
    # Non-LLM baseline.
    ("single",  "rule_based",
        "Candidates/rule_based/run.py", None),

    # LLM: zero-shot zenodo.
    ("single",  "zenodo_zero_shot",
        "Candidates/AutomatedDomainModelling_zenodo/zero_shot/run.py", None),

    # LLM: zero-shot kaiser (text2uml-kaiser), via the unified driver.
    ("unified", "kaiser_zero_shot",
        "Candidates/text2uml-kaiser/run-candidate.py", "kaiser_zero_shot"),
]


# Candidates whose driver accepts a stage-2 "translate" step.
_HAS_TRANSLATE_STAGE = {"zenodo_zero_shot"}

# Non-LLM candidate: the LLM slot must be None (rule_based ignores --model).
_IS_NON_LLM = {"rule_based"}


DEFAULT_LLMS: list[Optional[str]] = [
    "glm-5.1:cloud",
    "kimi-k2.6:cloud",
]
DEFAULT_DATASETS: list[str] = ["kaiser_clean", "reference_clean"]
DEFAULT_RUNS: int = 3
DEFAULT_METRIC: str = "metrik-4"
DEFAULT_TIMEOUT_SECONDS: int = 1800


# ---------------------------------------------------------------------------
# Joblist I/O.
# ---------------------------------------------------------------------------

JOBLIST_FILENAME = ".joblist.json"
SUMMARY_FILENAME = ".summary.json"
LOGS_SUBDIR = ".logs"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _utc_filename_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


# ---------------------------------------------------------------------------
# Logging.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("Workflow.run_benchmark")


# ---------------------------------------------------------------------------
# Data classes.
# ---------------------------------------------------------------------------


@dataclass
class WorkItem:
    candidate_id: str
    kind: str
    driver_path: str
    strategy_arg: Optional[str]
    llm: Optional[str]
    dataset: str
    run_index: int

    @property
    def key(self) -> tuple:
        return (
            self.candidate_id,
            self.llm,
            self.dataset,
            self.run_index,
        )

    @property
    def label(self) -> str:
        llm_part = self.llm or "no-llm"
        return (
            f"{self.candidate_id} | {llm_part} | {self.dataset} | "
            f"run{self.run_index:02d}"
        )

    def build_command(
        self,
        *,
        metric: str,
        out_dir: Path,
        cache_dir: Path,
        think: bool,
        limit: Optional[int],
    ) -> list[str]:
        """Build the subprocess argv for this work item."""
        cmd: list[str] = [
            sys.executable,
            str(REPO_ROOT / self.driver_path),
            "--dataset",   self.dataset,
            "--metric",    metric,
            "--run-index", str(self.run_index),
            "--out-dir",   str(out_dir),
            "--results-dir", str(cache_dir),
        ]
        if self.kind == "unified":
            assert self.strategy_arg is not None
            cmd += ["--strategy", self.strategy_arg]
        if self.llm is not None and self.candidate_id not in _IS_NON_LLM:
            cmd += ["--model", self.llm]
        if think and self.candidate_id not in _IS_NON_LLM:
            cmd += ["--think"]
        if limit is not None:
            cmd += ["--limit", str(limit)]
        return cmd


@dataclass
class JobState:
    """Persistent state for one job in the joblist."""
    key: tuple
    candidate_id: str
    llm: Optional[str]
    dataset: str
    run_index: int
    kind: str
    driver_path: str
    strategy_arg: Optional[str]
    status: str = "pending"  # pending | in_progress | done | failed | cancelled
    rc: Optional[int] = None
    wall_seconds: Optional[float] = None
    started_utc: Optional[str] = None
    finished_utc: Optional[str] = None
    log: Optional[str] = None
    artifact: Optional[str] = None
    error_excerpt: str = ""
    attempt: int = 0

    @property
    def label(self) -> str:
        llm_part = self.llm or "no-llm"
        return (
            f"{self.candidate_id} | {llm_part} | {self.dataset} | "
            f"run{self.run_index:02d}"
        )

    def to_json(self) -> dict:
        d = asdict(self)
        d["key"] = list(self.key)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "JobState":
        d = dict(d)
        d["key"] = tuple(d["key"])
        d["llm"] = d.get("llm")
        d["strategy_arg"] = d.get("strategy_arg")
        return cls(**d)

    @classmethod
    def from_workitem(cls, it: WorkItem) -> "JobState":
        return cls(
            key=it.key,
            candidate_id=it.candidate_id,
            llm=it.llm,
            dataset=it.dataset,
            run_index=it.run_index,
            kind=it.kind,
            driver_path=it.driver_path,
            strategy_arg=it.strategy_arg,
        )


# ---------------------------------------------------------------------------
# Subprocess runner.
# ---------------------------------------------------------------------------


def _execute_one(
    item_dict: dict,
    *,
    metric: str,
    out_dir: str,
    logs_dir: str,
    cache_dir: str,
    think: bool,
    limit: Optional[int],
) -> dict:
    """Run one work item to completion. Used as a ProcessPoolExecutor task.

    Returns a dict matching ``JobState.to_json()`` for the executed job.
    """
    item = WorkItem(
        candidate_id=item_dict["candidate_id"],
        kind=item_dict["kind"],
        driver_path=item_dict["driver_path"],
        strategy_arg=item_dict["strategy_arg"],
        llm=item_dict["llm"],
        dataset=item_dict["dataset"],
        run_index=item_dict["run_index"],
    )

    out_dir_p = Path(out_dir)
    logs_dir_p = Path(logs_dir)
    logs_dir_p.mkdir(parents=True, exist_ok=True)
    cache_dir_p = Path(cache_dir)
    cache_dir_p.mkdir(parents=True, exist_ok=True)

    cmd = item.build_command(
        metric=metric,
        out_dir=out_dir_p,
        cache_dir=cache_dir_p,
        think=think,
        limit=limit,
    )

    llm_part = (item.llm or "no-llm").replace("/", "_").replace(":", "_")
    log_filename = (
        f"{item.candidate_id}__{llm_part}__{item.dataset}__"
        f"run{item.run_index:02d}__{_utc_filename_ts()}.log"
    )
    log_path = logs_dir_p / log_filename

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
    }
    # Note: we deliberately do NOT set OLLAMA_THINK=false; whether the
    # model uses thinking is controlled per-job by the harness's --think
    # flag and the per-candidate driver's --think/--no-think argument.

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except Exception as exc:
        rc = 1
        stdout = ""
        stderr = f"subprocess raised: {type(exc).__name__}: {exc}\n"
    wall = time.time() - t0

    log_path.write_text(
        f"=== command ===\n{' '.join(cmd)}\n\n"
        f"=== env (subset) ===\nPYTHONPATH={env['PYTHONPATH']}\n\n"
        f"=== exit code ===\n{rc}\n\n"
        f"=== stdout ===\n{stdout}\n\n"
        f"=== stderr ===\n{stderr}\n",
        encoding="utf-8",
    )

    artifact: Optional[str] = None
    error_excerpt = ""
    if rc == 0:
        for cand in sorted(out_dir_p.glob(f"{item.candidate_id}*.json")):
            if cand.name.startswith("."):
                continue
            try:
                with cand.open() as f:
                    payload = json.load(f)
            except Exception:
                continue
            if (
                payload.get("candidate") == item.candidate_id
                and payload.get("dataset") == item.dataset
                and payload.get("run_index") == item.run_index
                and (
                    item.llm is None
                    or payload.get("settings", {}).get("model") == item.llm
                )
            ):
                artifact = str(cand)
                break
    else:
        err_lines = [
            ln.strip() for ln in stderr.splitlines()
            if ln.strip() and "WARNING" not in ln
        ]
        error_excerpt = "\n".join(err_lines[-6:])[:800]

    return {
        "key": list(item.key),
        "candidate_id": item.candidate_id,
        "llm": item.llm,
        "dataset": item.dataset,
        "run_index": item.run_index,
        "kind": item.kind,
        "driver_path": item.driver_path,
        "strategy_arg": item.strategy_arg,
        "status": "done" if rc == 0 else "failed",
        "rc": rc,
        "wall_seconds": round(wall, 2),
        "started_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat(),
        "finished_utc": _utc_iso(),
        "log": str(log_path.relative_to(out_dir_p)),
        "artifact": artifact,
        "error_excerpt": error_excerpt,
        "attempt": 1,
    }


# ---------------------------------------------------------------------------
# Joblist persistence.
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write ``data`` to ``path`` atomically (temp-file + rename)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_joblist(path: Path) -> dict[str, JobState]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("joblist %s unreadable: %s — starting fresh", path, exc)
        return {}
    out: dict[str, JobState] = {}
    for k, v in raw.get("jobs", {}).items():
        try:
            out[k] = JobState.from_json(v)
        except Exception as exc:
            log.warning("joblist entry %s invalid: %s — skipping", k, exc)
    return out


def _save_joblist(path: Path, jobs: dict[str, JobState], *,
                  matrix_meta: dict) -> None:
    payload = {
        "version": 1,
        "updated_utc": _utc_iso(),
        "matrix": matrix_meta,
        "jobs": {k: j.to_json() for k, j in jobs.items()},
    }
    _atomic_write_json(path, payload)


def _artifact_matches(
    artifact: Path,
    *,
    candidate_id: str,
    llm: Optional[str],
    dataset: str,
    run_index: int,
) -> bool:
    if artifact.name.startswith("."):
        return False
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except Exception:
        return False
    if payload.get("candidate") != candidate_id:
        return False
    if payload.get("dataset") != dataset:
        return False
    if payload.get("run_index") != run_index:
        return False
    if llm is not None and payload.get("settings", {}).get("model") != llm:
        return False
    return True


def _find_artifact_for(
    out_dir: Path,
    *,
    candidate_id: str,
    llm: Optional[str],
    dataset: str,
    run_index: int,
) -> Optional[Path]:
    matches: list[Path] = []
    for path in out_dir.glob(f"{candidate_id}*.json"):
        if _artifact_matches(
            path,
            candidate_id=candidate_id, llm=llm,
            dataset=dataset, run_index=run_index,
        ):
            matches.append(path)
    if not matches:
        return None
    # Prefer the most recent.
    return max(matches, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# Cancellation.
# ---------------------------------------------------------------------------


class _Cancel:
    """Cooperative cancellation flag set by SIGINT."""
    def __init__(self) -> None:
        self.cancelled = False
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)

    def _handler(self, signum, frame) -> None:  # noqa: ARG002
        if not self.cancelled:
            log.warning("cancellation requested — finishing in-flight jobs, "
                        "abandoning queue")
            self.cancelled = True


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--llms", nargs="+", default=DEFAULT_LLMS,
                   help="Ollama model tags. Default: %(default)s")
    p.add_argument("--candidates", nargs="+", default=None,
                   help="Restrict to these candidate_ids. Default: the 3 "
                        "registered in CANDIDATES.")
    p.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS,
                   help="Datasets to run. Default: %(default)s")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                   help="Number of run-indices per (candidate, llm, dataset). "
                        "Default: %(default)s")
    p.add_argument("--metric", default=DEFAULT_METRIC,
                   help="Metric to score with. Default: %(default)s")
    p.add_argument("--workers", type=int, default=4,
                   help="Parallel worker processes. Default: 4.")
    p.add_argument("--out-dir", default=None,
                   help="Directory to write artifacts into. "
                        "Default: Workflow/Results/runs/")
    p.add_argument("--limit", type=int, default=None,
                   help="Per-run record cap (smoke-testing).")
    p.add_argument("--think", action="store_true",
                   help="Enable Ollama thinking mode on LLM calls.")
    p.add_argument("--no-think", action="store_false", dest="think",
                   help="Disable Ollama thinking mode. (default)")
    p.set_defaults(think=False)
    p.add_argument("--reset", action="store_true",
                   help="Wipe runs/, cache/, and the joblist before running. "
                        "Destructive.")
    p.add_argument("--list", action="store_true",
                   help="Print the planned joblist and exit.")
    p.add_argument("--status", action="store_true",
                   help="Print current joblist status and exit.")
    p.add_argument("--rerun-failed", action="store_true",
                   help="Re-run jobs whose last status was 'failed'.")
    p.add_argument("--no-resume", action="store_true",
                   help="Build a fresh joblist; ignore any previous one.")
    return p


def _expand_work(
    *,
    llms: list[Optional[str]],
    candidates_filter: Optional[list[str]],
    datasets: list[str],
    runs: int,
) -> list[WorkItem]:
    items: list[WorkItem] = []
    for kind, cid, driver, strat in CANDIDATES:
        if candidates_filter and cid not in candidates_filter:
            continue
        if cid in _IS_NON_LLM:
            local_llms: list[Optional[str]] = [None]
        else:
            local_llms = list(llms)
        for llm in local_llms:
            for ds in datasets:
                for ri in range(1, runs + 1):
                    items.append(WorkItem(
                        candidate_id=cid,
                        kind=kind,
                        driver_path=driver,
                        strategy_arg=strat,
                        llm=llm,
                        dataset=ds,
                        run_index=ri,
                    ))
    return items


def _print_joblist(jobs: dict[str, JobState]) -> None:
    by_status: dict[str, list[JobState]] = {}
    for j in jobs.values():
        by_status.setdefault(j.status, []).append(j)
    print(f"joblist: {len(jobs)} total")
    for status in ("done", "in_progress", "pending", "failed", "cancelled"):
        n = len(by_status.get(status, []))
        print(f"  {status:14s} {n:4d}")
    if "failed" in by_status:
        print("\n--- failed jobs ---")
        for j in by_status["failed"]:
            print(f"  {j.label}  {j.error_excerpt.splitlines()[0] if j.error_excerpt else ''}")


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    out_dir = (
        Path(args.out_dir).resolve() if args.out_dir else RUNS_DIR_DEFAULT
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = out_dir / LOGS_SUBDIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    cache_root = REPO_ROOT / "Workflow" / "Results" / "cache"
    joblist_path = out_dir / JOBLIST_FILENAME
    summary_path = out_dir / SUMMARY_FILENAME

    if args.reset:
        # Wipe runs/ and cache/ AND the joblist.
        for child in out_dir.iterdir():
            if child.is_file() and child.name.startswith("."):
                child.unlink()
            elif child.is_dir():
                import shutil
                shutil.rmtree(child)
        if cache_root.exists():
            import shutil
            shutil.rmtree(cache_root)
        # Re-create the logs dir so workers can write into it.
        logs_dir.mkdir(parents=True, exist_ok=True)
        log.info("--reset: wiped %s and %s", out_dir, cache_root)

    work = _expand_work(
        llms=args.llms,
        candidates_filter=args.candidates,
        datasets=args.datasets,
        runs=args.runs,
    )

    matrix_meta = {
        "created_utc": _utc_iso(),
        "metric": args.metric,
        "think": args.think,
        "limit": args.limit,
        "datasets": list(args.datasets),
        "llms": list(args.llms),
        "candidates": sorted({it.candidate_id for it in work}),
        "runs": args.runs,
    }

    # ---- Build or load the joblist ----
    if args.no_resume or args.reset or not joblist_path.is_file():
        jobs: dict[str, JobState] = {}
        for it in work:
            jobs["|".join(map(str, it.key))] = JobState.from_workitem(it)
        log.info("built fresh joblist with %d jobs", len(jobs))
    else:
        prev = _load_joblist(joblist_path)
        new_keys = {"|".join(map(str, it.key)) for it in work}
        # Drop jobs no longer in the planned set.
        for k in list(prev):
            if k not in new_keys:
                del prev[k]
        # Add new jobs.
        for it in work:
            k = "|".join(map(str, it.key))
            if k not in prev:
                prev[k] = JobState.from_workitem(it)
        jobs = prev
        log.info("loaded joblist with %d jobs from %s", len(jobs), joblist_path)

    # If a job's artifact already exists on disk and parses, mark it done.
    for k, j in jobs.items():
        if j.status == "done":
            continue
        if j.status == "cancelled":
            j.status = "pending"
            continue
        if j.status == "failed" and not args.rerun_failed:
            continue
        if j.status == "in_progress":
            # Was running when we were killed; treat as pending for re-run.
            j.status = "pending"
            continue
        if j.status == "pending":
            # Look on disk.
            artifact = _find_artifact_for(
                out_dir,
                candidate_id=j.candidate_id,
                llm=j.llm,
                dataset=j.dataset,
                run_index=j.run_index,
            )
            if artifact is not None:
                j.status = "done"
                j.rc = 0
                j.artifact = str(artifact.relative_to(out_dir))
                j.wall_seconds = 0.0
                j.finished_utc = _utc_iso()

    if args.list:
        _print_joblist(jobs)
        return 0
    if args.status:
        _print_joblist(jobs)
        return 0

    pending_keys = [k for k, j in jobs.items() if j.status in ("pending", "failed")]
    if args.rerun_failed:
        pending_keys = [k for k, j in jobs.items() if j.status in ("pending", "failed")]
    n_pending = len(pending_keys)
    n_done = sum(1 for j in jobs.values() if j.status == "done")
    n_failed = sum(1 for j in jobs.values() if j.status == "failed")

    print("=" * 72)
    print(f"run_benchmark — {len(jobs)} jobs total, {n_pending} to run")
    print("=" * 72)
    print(f"  out-dir      : {out_dir}")
    print(f"  cache-dir    : {cache_root}/<pid>")
    print(f"  metric       : {args.metric}")
    print(f"  think        : {args.think}")
    print(f"  workers      : {args.workers}")
    print(f"  joblist      : {joblist_path}")
    if args.limit:
        print(f"  limit        : {args.limit} records per run")
    print(f"  status       : {n_done} done / {n_failed} failed / {n_pending} pending")
    print()

    _save_joblist(joblist_path, jobs, matrix_meta=matrix_meta)

    if n_pending == 0:
        print("Nothing to do.")
        _write_summary(jobs, summary_path, matrix_meta,
                       started_utc=matrix_meta["created_utc"],
                       finished_utc=_utc_iso(),
                       wall_seconds=0.0)
        return 0

    cancel = _Cancel()
    executor = ProcessPoolExecutor(max_workers=args.workers)

    # Progress bar: one row per pending job, completed as futures finish.
    pbar = tqdm(
        total=len(pending_keys),
        desc="benchmark",
        unit="job",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )

    try:
        futures = {}
        for k in pending_keys:
            j = jobs[k]
            j.started_utc = _utc_iso()
            j.attempt += 1
            cache_dir = cache_root / f"pid{os.getpid()}_t{id(j)}"
            fut = executor.submit(
                _execute_one,
                {
                    "candidate_id": j.candidate_id,
                    "kind":         j.kind,
                    "driver_path":  j.driver_path,
                    "strategy_arg": j.strategy_arg,
                    "llm":          j.llm,
                    "dataset":      j.dataset,
                    "run_index":    j.run_index,
                },
                metric=args.metric,
                out_dir=str(out_dir),
                logs_dir=str(logs_dir),
                cache_dir=str(cache_dir),
                think=args.think,
                limit=args.limit,
            )
            futures[fut] = k
            if cancel.cancelled:
                # Mark the rest as pending (so a future resume re-queues).
                for kk in pending_keys:
                    if jobs[kk].status == "in_progress" and kk != k:
                        jobs[kk].status = "pending"
                break

        for fut in as_completed(futures):
            k = futures[fut]
            j = jobs[k]
            # Mark the job as in_progress *now* (it just dequeued from
            # the executor's queue and is being processed).
            j.status = "in_progress"
            _save_joblist(joblist_path, jobs, matrix_meta=matrix_meta)
            try:
                result = fut.result()
            except Exception as exc:
                j.status = "failed"
                j.rc = 1
                j.wall_seconds = 0.0
                j.finished_utc = _utc_iso()
                j.error_excerpt = f"{type(exc).__name__}: {exc}"
            else:
                j.status = result["status"]
                j.rc = result["rc"]
                j.wall_seconds = result["wall_seconds"]
                j.finished_utc = result["finished_utc"]
                j.log = result["log"]
                j.artifact = result["artifact"]
                j.error_excerpt = result["error_excerpt"]
            pbar.update(1)
            tag = "OK " if j.rc == 0 else "ERR"
            pbar.write(f"  {tag} {j.label}  ({j.wall_seconds or 0:.1f}s)")
            _save_joblist(joblist_path, jobs, matrix_meta=matrix_meta)
            if cancel.cancelled:
                pbar.write("  cancellation: abandoning remaining queue")
                break
    finally:
        pbar.close()
        executor.shutdown(wait=False, cancel_futures=True)

    # Mark any still-pending or in-progress jobs after the loop.
    for j in jobs.values():
        if j.status == "in_progress":
            j.status = "cancelled"
            j.finished_utc = _utc_iso()
    _save_joblist(joblist_path, jobs, matrix_meta=matrix_meta)

    n_done_final = sum(1 for j in jobs.values() if j.status == "done")
    n_failed_final = sum(1 for j in jobs.values() if j.status == "failed")
    n_cancelled = sum(1 for j in jobs.values() if j.status == "cancelled")
    n_pending_final = sum(1 for j in jobs.values() if j.status == "pending")

    print()
    print("=" * 72)
    print(
        f"DONE: {n_done_final} done / {n_failed_final} failed / "
        f"{n_cancelled} cancelled / {n_pending_final} pending"
    )
    print(f"joblist: {joblist_path}")
    print("=" * 72)

    _write_summary(
        jobs, summary_path, matrix_meta,
        started_utc=matrix_meta["created_utc"],
        finished_utc=_utc_iso(),
        wall_seconds=(
            (datetime.fromisoformat(_utc_iso().replace("Z", "+00:00"))
             - datetime.fromisoformat(matrix_meta["created_utc"].replace("Z", "+00:00"))
            ).total_seconds()
        ),
    )
    return 0 if n_failed_final == 0 and n_pending_final == 0 else 1


def _write_summary(
    jobs: dict[str, JobState],
    summary_path: Path,
    matrix_meta: dict,
    *,
    started_utc: str,
    finished_utc: str,
    wall_seconds: float,
) -> None:
    by_status: dict[str, int] = {}
    for j in jobs.values():
        by_status[j.status] = by_status.get(j.status, 0) + 1
    summary = {
        "version": 1,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "wall_seconds": round(wall_seconds, 1),
        "matrix": matrix_meta,
        "totals": by_status,
        "jobs": [j.to_json() for j in jobs.values()],
    }
    _atomic_write_json(summary_path, summary)


if __name__ == "__main__":
    sys.exit(main())
