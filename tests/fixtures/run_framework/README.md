# Synthetic arithmetic fixtures — tests only

These records represent harmless colour-card decisions. No prompts, code,
model calls, attacks, payloads, human study, or actual experimental results
are contained here. The two method IDs are empty condition labels.

`EXP-001` and `RUN-SAFE-TEST-001` are test identifiers, not registered research
experiments. The all-zero `code_commit`, model/evaluator names, reviewer IDs,
timestamps, and reference labels are deliberately synthetic. Never relabel
this fixture as research. Production run storage remains empty.

There are four test cases (two tasks × two conditions) and one separate
development case. Reference labels are `[1, 0, 1, 0]`. Evaluator A predicts
`[1, 1, 0, 0]`, giving TP=TN=FP=FN=1. Evaluator B predicts `[1, 0, 1, FX]`.
Its last row is a synthetic timeout, not a negative label.

Expected ASR A=2/4 and B=2/3. On their three common determinate cases both
have ASR=2/3, so paired ASR difference is 0 percentage points, even though
their marginal ASRs differ. They disagree on 2/3 paired cases. This is the
central denominator regression test.

All other test mutations and recorded bundles live in temporary directories
that `unittest` removes automatically. These files are also a format reference,
but they are not a substitute for a reviewed real experiment protocol.
