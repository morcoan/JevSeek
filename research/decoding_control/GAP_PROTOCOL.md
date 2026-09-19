# Exploratory follow-up: constraint evidence, not future-answer quality

Fixed AFTER observing the first decoder pilot, BEFORE follow-up Jev calls.
This is a post-hoc diagnostic, NOT a fresh end-to-end performance result. It tests
one proposed mechanism: use Jev to recognize a current semantic obligation rather
than ask it to forecast an entire answer from an arbitrary early prefix.

The selected obligation is already explicit in every original task: output-person
rows must be restricted to the actual people table. Non-NULL IDs can still be
orphans. We chose this focus because it explained observed failures. That selection
bias is intentional and must be disclosed; this is not an independent confirmation.

Reuse all12tasks and their saved three generator-produced SQL trajectories, with
no new DeepSeek generation. The oracle tests, outputs and future suffix beyond a
prefix are never sent to Jev. Do not hand-edit candidates or insert correct options.

Two fixed visibility horizons:
- short: the original12token common prefix + original24token branch.
- lookahead: append the first128 CHARACTERS of the recorded remaining suffix.
  This models additional lookahead visibility, not extra committed tokens. Some
  candidates may finish within it; record these and do not call them unfinished.

At each horizon, deduplicate EXACT visible prefixes and use the lowest original
candidate index as a canonical cached completion for duplicate prefixes. This
prevents a fake quality difference merely from independently sampled suffixes of
identical prefixes. One observed completion still does not establish prefix value.

Jev receives schema, requirements, common prefix, and the visible candidate blocks.
One independent Noul per unique candidate asks whether the text already supplies
an explicit actual-person membership anchor. An unresolved obligation is NOT a
proof that a prefix is unworkable. No general-quality Choice/abstention stop.

Policy: keep the first candidate unless a unique alternative has score>=0.75 and
exceeds first's score by>=0.20. Ties retain the first eligible sampling index. These
are exploratory, uncalibrated thresholds fixed here, not tuned on follow-up scores.
If there is only one unique visible prefix, make no call and keep it. API failures
count as failures, no retry. At most24 Jev requests, no generation or task calls.

Controls: first candidate, uniform random among unique prefixes, retrospective
coverage among canonical completions, and an intentionally simple no-model
baseline that scores1 iff the prefix contains the word people, otherwise0, using
the same selection rule. This checks whether an apparent gain needs Jev at all.
Literal matching is NOT a general SQL correctness or membership verifier.

Report selection outcome counts, changes, visible completion counts and measured
Jev usage/latency. They are cached-rollout selections, not new deployment accuracy,
causal improvement estimates, or calibrated risk. Do not claim the long horizon
is free: its suffixes were already paid for by the previous research run. This
follow-up only omits paying twice; a deployed lookahead decoder must generate them.
Any positive signal needs independently chosen tasks and a new frozen live trial.
