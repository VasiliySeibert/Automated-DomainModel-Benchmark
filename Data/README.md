# Data/

Two parser-cleaned benchmark corpora, each in its own subfolder.

| Folder / file                                | Records |
|----------------------------------------------|--------:|
| `data-source-1/kaiser_clean.json`            |      45 |
| `data-source-2/reference_clean.json`         |       8 |

Both files are produced from external research artefacts (see
`Candidates/adjustments.md` and the top-level attribution):

- kaiser corpus from `text2uml-kaiser/dataset/<Model>/...`
- reference corpus from `ReferenceModels-and-NLT/automated-archive/...`

The cleaned variants are the canonical benchmark corpora — they parse
under `strict=True` mode (which the metrik-N scorers use), so every
record scores non-zero on a perfect self-match.

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

`nlt` is the natural-language specification; `puml` is the reference
PlantUML class diagram that the benchmark candidates are scored
against.

## Loaders

```python
from Data import (
    load_kaiser_clean, load_reference_clean, load_dataset,
)
load_dataset("kaiser_clean")        # 45 records (data-source-1)
load_dataset("reference_clean")     # 8 records  (data-source-2)
load_dataset("data-source-1")       # alias for kaiser_clean
load_dataset("data-source-2")       # alias for reference_clean
```

## Parser

`Data/Parser/` is a copy of the `Quantitative-Analysis/Workflow/Parser/`
package from `domainModel-Metrics-Comparison`. Zero external
dependencies — pure stdlib.

```python
from Data.Parser import PlantUMLParser
parser = PlantUMLParser(strict=False)
model  = parser.parse(puml_string)
print(model.summary())
```