# Research Plan v0.1

## Purpose

Test whether subdomain-specific functional validation can improve the measurement of LLM jailbreak success compared with broader evaluators.

## Core hypothesis

A validator specialised for one narrow harmful subdomain may agree more closely with carefully constructed human ground truth than general-purpose or broader domain-level evaluators.

This hypothesis must be falsifiable. The project should be considered successful even if the result is that specialisation does not provide a meaningful advantage.

## First paper-shaped study

1. Complete a validation-focused literature review and novelty check.
2. Select one narrow malicious-code subdomain using evidence, not convenience alone.
3. Define human success criteria before finalising the proposed validator.
4. Build a development split for method design and a held-out test split for final evaluation.
5. Collect a shared response set from existing benchmark prompts where licensing permits.
6. Produce independent human annotations and adjudicate disagreements.
7. Reproduce 3–4 fair baseline validation methods.
8. Implement the proposed subdomain-specific validator.
9. Compare all methods on the same held-out cases.
10. Run ablations and error analysis.
11. Measure whether evaluator choice changes reported ASR or attack rankings.

## Candidate baseline families

- Generic LLM-as-a-judge
- RMCBench-style malicious-code evaluation
- CodeJailbreaker / Malicious Ratio
- GUIDEDEVAL-style case-specific judging
- Functional / scenario-specific validation inspired by RedCode

The final baseline set must be justified by the literature review.

## Primary outcomes

- Accuracy
- Precision
- Recall
- F1
- False-positive rate
- False-negative rate
- Agreement with human ground truth
- ASR distortion
- Attack-ranking sensitivity
- Error taxonomy

## Planned ablation

Semantic judge → + subdomain rubric → + static checks → + safe functional checks → full validator.

## Long-term research programme

Only if Stage 1 shows a real advantage:

1. add more specialised validators,
2. standardise their outputs,
3. study automatic multi-label domain/subdomain routing,
4. evaluate routing error separately from validator error,
5. expose the research system through the web interface.

## Current candidate subdomains

- Ransomware — working candidate
- Spyware — backup candidate
- Network-attack-related tasks — backup candidate

No category is locked until the literature and feasibility review are complete.
