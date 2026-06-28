# Data/

Two benchmark datasets, each a JSON list of `{id, nlt, puml}` entries.

| File          | Source                                                                            | # Models |
|---------------|-----------------------------------------------------------------------------------|---------:|
| `kaiser.json` | `text2uml-kaiser/dataset/<Model>/{description.md,plantuml.txt}`                   |       45 |
| `reference.json` | `ReferenceModels-and-NLT/automated-archive/groundTruthWithPlantUML.json`       |        8 |

Both sources are external research artefacts. They are reproduced here as
fair benchmark corpora; see the top-level README for full attribution.

## Schema

```json
[
  {
    "id":   "AirTravel",
    "nlt":  "The name, type, year of manufacture, ...",
    "puml": "@startuml\nclass Airline {\n String Name\n}\n...\n@enduml"
  },
  ...
]
```

`nlt` is the natural-language specification; `puml` is the reference PlantUML
class diagram that the benchmark candidates are scored against.

## Regenerate

```bash
PYTHONPATH=. python Data/build_datasets.py
```

Optional overrides:

```bash
PYTHONPATH=. python Data/build_datasets.py \
    --kaiser-root    /path/to/text2uml-kaiser/dataset \
    --reference-root /path/to/ReferenceModels-and-NLT/automated-archive
```

## Parser

`Data/Parser/` is a copy of the `Quantitative-Analysis/Workflow/Parser/` package
from `domainModel-Metrics-Comparison`. The local parser parses every record in
both datasets **without raising** under `strict=False` (45/45 kaiser and 8/8
reference), but **17/53 records contain unrecognised syntax** that the strict
parser rejects:

- **12 records** use `enum X <<enum>> { … }` (e.g. `CelO`, `LabTracker`,
  `BuildingManagement`). The local parser drops the entire enum body and every
  value as "skipped" warnings.
- **6 lines on 6 records** use malformed diamonds like `School "1"*-"*" Room`
  (single dash on one side). The local parser drops the whole association as
  a warning.
- **1 record** (`HBMS`) uses `class SpecialOffer extends Offer`, which the
  parser drops silently.

The scoring engine (`metrik-4`) re-parses the reference with **`strict=True`**.
Any unrecognised line raises `ValueError`, which `Workflow/metric_runner.py`
catches and records as `error=<exception>`, with all three element scores set
to `0.0`. Net effect: every cell that references an affected record scores
zero on that pair, regardless of the candidate's actual output.

Zero external dependencies — pure stdlib.

```python
from Data.Parser import PlantUMLParser
parser = PlantUMLParser(strict=False)
model  = parser.parse(puml_string)
print(model.summary())
```

## Cleaned datasets

`Data/clean_datasets.py` applies five pure, idempotent rewrites and emits
side-by-side copies that **all parse cleanly under strict=True**:

- `Data/kaiser_clean.json` (45 records)
- `Data/reference_clean.json` (8 records)

| Repair | Records affected |
|---|---|
| `enum X <<enum>>` → `enum X` | 12 (BuildingManagement, CardGameApp, CelO, Ebike, FilmSet, HelpingHands, House, LabTracker, TeamSportsScoutingSystem, TransportCompany, TruckLogistics, eHome2020) |
| Single-dash diamonds (`*-`, `-*`, `*->`, `<-*`, `o->`, `<-o`) → canonical 2-dash / 3-char form | 6 (GasStation_TUW, HelpingHands, School, TileOGame, University) |
| `class Sub extends Parent` → `class Sub` + `Sub --|> Parent` | 1 (HBMS) |
| `A <--> B` → `A --> B` | 1 (TeamSportsScoutingSystem) |
| `note "X" as ALIAS` and any references to `ALIAS` dropped | 1 (FilmSet) |

The union covers all 17 records; raw `kaiser.json` / `reference.json` are
left bit-for-bit identical for fair citation. Loaders:

```python
from Data import load_kaiser_clean, load_reference_clean, load_dataset
load_dataset("kaiser_clean")
load_dataset("reference_clean")
```

Regenerate:

```bash
PYTHONPATH=. python Data/clean_datasets.py
PYTHONPATH=. python Data/clean_datasets.py --verify   # also self-similarity
```

## Smoke

```bash
PYTHONPATH=. python -m pytest tests/test_data_smoke.py tests/test_data_clean.py -v
```