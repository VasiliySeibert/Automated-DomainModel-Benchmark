"""AutomatedDomainModelling_zenodo source group.

Reuses prompt strategies from Chen et al. 2023 (MODELS) — see Candidates/AutomatedDomainModelling_zenodo/README.md
(`AutomatedDomainModelling_zenodo/prompts.md` and
`LLM_for_modelling/llm-model-generation-master/prompt_generation.py`).

The folder name uses underscores (instead of the upstream's hyphens) so
that the helper `zenodo_text_format` can be imported as a normal Python
module:

    from Candidates.AutomatedDomainModelling_zenodo.zenodo_text_format
        import text_to_plantuml

The folder name *conceptually* still refers to the upstream repository
("Automated Domain Modelling with Large Language Models" — Zenodo).
"""