PYTHONPATH ?= .
OUT ?= Data/NLP-Analysis/out

.PHONY: all analyze report summary examples test clean

all: analyze report summary examples

analyze:
	PYTHONPATH=$(PYTHONPATH) python3 $(CURDIR)/analyze.py --out $(OUT)

report:
	PYTHONPATH=$(PYTHONPATH) python3 $(CURDIR)/report.py --in $(OUT) --out $(OUT)

summary:
	PYTHONPATH=$(PYTHONPATH) python3 $(CURDIR)/build_summary_json.py --in $(OUT) --out $(OUT)

examples:
	PYTHONPATH=$(PYTHONPATH) python3 $(CURDIR)/build_examples.py --in $(OUT)/per_record.jsonl --out $(OUT)/examples

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest $(CURDIR)/tests/ -q

clean:
	rm -rf $(OUT)/per_record.csv $(OUT)/per_record.jsonl $(OUT)/per_element_match.csv \
	       $(OUT)/cross_dataset.csv $(OUT)/summary.md $(OUT)/summary.json \
	       $(OUT)/rel_kind_coverage.csv $(OUT)/nlt_sentence_stats.csv \
	       $(OUT)/nlt_style.csv $(OUT)/parser_warnings.csv \
	       $(OUT)/charts/*.png $(OUT)/examples/*.md
