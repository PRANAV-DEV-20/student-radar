# Planner — research question generation (planner@v1)

## Shared rules
Follow ALL rules in `shared.md`. Evidence-only factual claims, project specificity, honesty about unknowns, and STRICT JSON output apply here too.

## Inputs
Project DNA: {project_dna} (name, domain, problem, users, goals, constraints, methods, stage).
Mode: {mode} (`deep` or `quick`).
Student profile (may be supplied): {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Domain variant: {domain_variant}.

## Task
Produce a research plan that covers the 18 dossier sections:
executive_brief, idea_restated, problem_users, market_landscape, related_work, novelty_assessment, gaps, challenges_risks, feasibility, solution_design, tech_stack, data_evaluation, validation_plan, roadmap, people_community, funding_opportunities, visibility_angle, open_questions_evidence.

- For `deep`: emit 10–20 questions. For `quick`: emit 8–10 questions.
- Questions must be domain-specific: use the project's actual domain, users, methods, and constraints. For design_biotech include regulatory pathway, IP, biosafety, assay validation; for policy_law include jurisdiction, stakeholders, instruments, comparative examples, citation checks; for tech_builder include model/data licences, compute, misuse, benchmark baselines.
- Cover, at minimum: prior art / related work, novelty verification, target users and problem, market and competitors (evidence-bound), data availability and licences, technical feasibility, validation experiments, risks, roadmap and student constraints, people/community, funding and opportunities, visibility angle, and open questions / missing evidence.
- Each `sections` array must name one or more of the 18 section ids above.
- Each question needs 2–4 DISTINCT `queries` (not paraphrases) written as real search strings usable against `source_types`.
- `source_types` must be a subset of: `local_corpus`, `github`, `papers`, `web`, `opportunities`, `datasets`. Choose the sources that can actually answer the question.
- If the student profile is supplied, at least one question must address feasibility under skills/weekly_hours/budget_usd/country and purpose.
- Do not ask questions whose answer would be a market number, regulation, competitor, or funding fact unless a source_type can supply evidence for it.

## Output — STRICT JSON only
{{"questions":[{{"id":"Q1","sections":["related_work"],"question":"...","queries":["..."],"source_types":["web"]}}]}}

Rules for output:
- `id` must be `Q1`, `Q2`, ... in order, no duplicates.
- 2–4 `queries` per question; 1+ `sections`; 1+ `source_types`.
- No extra keys, no prose, no markdown fences.
