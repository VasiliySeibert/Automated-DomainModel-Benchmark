# AutomatedDomainModelling-zenodo / zero_shot

Reuses the zenodo §1 prompt verbatim:

* `PROBLEM_STATEMENT` (system prompt — `prompt_system.txt`)
* `TASK_DESCRIPTION` (task description — `prompt_task.txt`)

The LLM is asked to emit a structured text response
(`Enumeration:` / `Class:` / `Relationships:` sections). We
post-process the response with the bundled `text_to_plantuml()` helper
to synthesise a PlantUML block the parser can ingest.

**No skip folders.**