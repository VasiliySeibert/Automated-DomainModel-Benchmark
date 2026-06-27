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
from `domainModel-Metrics-Comparison`. It parses both datasets **100%** (45/45
kaiser and 8/8 reference). Zero external dependencies — pure stdlib.

```python
from Data.Parser import PlantUMLParser
parser = PlantUMLParser(strict=False)
model  = parser.parse(puml_string)
print(model.summary())
```

## Smoke

```bash
PYTHONPATH=. python -m pytest tests/test_data_smoke.py -v
```