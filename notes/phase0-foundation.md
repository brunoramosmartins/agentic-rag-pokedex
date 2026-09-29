# Phase 0 — Foundation, Licensing & Measurability Gate

**Objective.** Record the decisions that shape the project, publish the
measurability gate, and pass G1 before writing any pipeline. Draft E-001 in
full — hypotheses, predictions, threshold, falsifier, outcome space, error
taxonomy — while no number exists yet to contaminate it.

**Dates.** Opened 2026-09-24 · 5 partial working days timebox (size S, 3–5
days, week 1) · no hard deadline.

**Ends with.** Tag `v0.1-foundation` (no release): scaffold, ADRs 001–010
accepted, G1 decided, gate published, E-001 fully drafted.

---

## Phase readings (Joren 2025, Ferrazzi 2026, Singh 2025)

Three lit-notes with the author's takes and refined write-ups, and a synthesis
(`notes/phase0-synthesis.md`). Joren et al. fixed the label question: the
project's label is **coverage of a gold minimal sufficient set**, strictly
stronger than Joren's "a plausible answer exists" (decided 2026-09-26, ADR-001
Updates). Ferrazzi et al. showed agents rarely retrieve again (10% of queries)
at up to 3.6× the input tokens, with no label on whether their stops were
justified. Singh et al. name the stopping decision but give it no taxonomy box.
The positioning check found later work that already controls retrieval with a
sufficiency signal (SIM-RAG, S2G-RAG, Luo 2026), so the contribution is stated
as **measurement**, not method.

## Hypothesis, measurability gate and contingency (`docs/hypothesis.md`, `docs/measurability-gate.md`, `docs/contingency.md`)

H1 (explicit judge vs implicit detector) and H2 (judge vs fixed pipeline) on
the expected cost C = 0 / 1 / λ with λ = 4 as a scenario and λ\* as the
headline; action threshold 0.25; strata S0–S4 with S0 as the falsifier. The
eight measurability gates were answered before any code, and the contingency
gates G1–G5 each carry a written exit.

## Data sources and licensing — G1 (`docs/data-sources.md`)

**G1 passed.** PokéAPI (BSD-3) pinned to a commit with 14 CSVs hashed; MuSiQue
(CC BY 4.0) hashed. Findings that shaped Phase 1: adjacent generations differ
in only 3% of levels, so the version scope must span generations; DLC version
groups are empty; MuSiQue's test split has no labels. The published benchmark
is twin-side and fact-level only; the corpus is rebuilt locally.

## ADRs 001–010

Drafted as Proposed, reviewed by the author on 2026-09-25 — all ten stand;
five caveats checked. The review found one real gap: free text outside the
registry could state a gold fact unseen by the labeler, so a **shortcut scan**
validated on planted leaks was added (PI-001). ADR-008's scope was stated (one
model configuration) and ADR-010's 50% cut declared a reading convention. All
ten accepted the same day.

## Experiment registry — E-001 (full draft) and E-002 (typed expansion)

E-001 drafted in full while no number existed: hypotheses, per-stratum
predictions, threshold, falsifier, outcome space (rows 0 to 7b), error
taxonomy, λ\* cases. Two adversarial passes (5 blockers, 4 major, 3 minor; then
3 blockers, 5 major, 6 minor), all adopted. The ones that changed the design:
power targets the *supported* verdict at Δ_design = 0.35 (n\* = 78 / 175 / 311
for SD 1.0 / 1.5 / 2.0); **n_max** from measured costs instead of any budget
increase; a futility row (0b); a registered agent decision table; the A4p dose
as a permutation of A4's steps; the verdict decided by 97.5% BCa intervals
alone. E-002 became descriptive.

## Outcome space checked by test (`tests/test_outcome_space.py`)

Every combination of (H1, placebo, mediation, falsifier, O2 ceiling) and the
four λ\* cases is enumerated and must fall in exactly one row of the outcome
space — the previous project's Phase 11 lesson turned into a test.

## Power script reproducing P2's E-026 (`evaluation/power.py`)

**Gate 7 passed:** at P2's pooled discordance it reproduces every published
E-026 number (six floors, six interaction floors, eight "n needed"). The module
generalizes the method from a binary paired difference to any SD of D and adds
the verdict functions. One rounding error in an earlier journal line was found
and corrected.

## Token meter and cost estimate before any loop

**Gate 7 passed** on 10 real calls: the meter's totals equal the raw API usage,
and 10 of 10 local input counts are within tolerance. Snapshot
`gpt-5-mini-2025-08-07`. Reasoning on trivial prompts was small, so the 150 /
400 reasoning scenarios stayed until Phase 3 — they later proved low (Phase 1,
PI-014). Every LLM loop prints an estimate and supports `--limit N`.

## Scaffold, docker-compose (Neo4j + Phoenix) and CI

src layout, optional extras per concern, docker-compose with Neo4j and Phoenix,
CI with lint, unit tests on Python 3.11 and 3.12 and a Neo4j integration job,
GitHub templates and setup scripts. Secrets come from the environment with
`.env` as fallback and are never printed.

## Initial README with problem statement and trademark notice

Problem statement, plan table, trademark notice and PokéAPI attribution.

## Phase close

The close sweep logged PI-001 to PI-009; the plan was revised on 2026-09-28
before the tag. The v1.0 cost cap went from US$ 13.5 to **US$ 20 before any
data**, with a two-stage A2 sweep; SIM-RAG and S2G-RAG joined the Phase 5
readings. All nine impacts resolved.

---

## Lessons Learned

### 1. A research question has to be narrower than the intuition that motivated it

The original intuition was broad: LLM systems should know when they do not have
enough information to answer reliably. The Phase 0 work forced that intuition
into a measurable question: whether a retrieval agent can detect, at each step,
that its accumulated evidence is sufficient to stop searching.

That narrowing is not a loss of ambition. It is what makes the hypothesis
experimentally testable.

### 2. Sufficiency is not the same as relevance, correctness, or confidence

The reading of Joren et al. made the distinction explicit. A context can be
relevant without being sufficient, and a model can answer correctly despite
insufficient context because of information outside the retrieved evidence.

For this project, these are separate variables. The examiner labels evidence
sufficiency; the grader measures answer correctness; the experiment separately
controls the generator's access to parametric knowledge through the
counterfactual twin.

### 3. The oracle must be stronger than the treatment it evaluates

An LLM judge can be useful as the experimental treatment, but it should not also
define the primary outcome. The project therefore separates A4, which predicts
sufficiency during the loop, from the labeler, which provides the exact
sufficiency label for every step of every arm. O2 is the oracle arm that stops
on that label; it measures the room for improvement, not the correctness of
other arms' stops.

This makes it possible to ask whether the detector is correct instead of
implicitly assuming that its own judgment is the ground truth.

### 4. Experimental control is part of the contribution

The counterfactual twin, controlled sufficiency strata, minimal sufficient sets,
single-opening evaluation splits, and explicit outcome space are not merely
implementation details. They exist to prevent alternative explanations from
being mistaken for evidence of the hypothesis.

The project is intentionally a controlled sufficiency benchmark, not a claim
that Pokémon represents real-world enterprise data.

### 5. A negative or inconclusive result is a valid outcome

The project should not be designed to guarantee that explicit sufficiency
detection wins. The registered outcome space allows the result to be
sustained, refuted, or inconclusive, including the possibility that there is too
little measurable headroom for a detector to matter.

This changes the objective from "demonstrate that A4 is better" to "measure
whether explicit sufficiency detection provides a measurable benefit under the
registered conditions."

### 6. Literature can change the gap without invalidating the experiment

Phase 0 showed that the original gap statement around iterative sufficiency
was too broad. Prior work already explores iterative and sufficiency-aware
retrieval.

The defensible contribution is therefore narrower: measure sequential
sufficiency as a stopping problem under exact, controlled labels and quantify
its effect on cost and answer reliability.

## Failed Attempts

### 1. Treating the project as the first iterative sufficiency system

An early formulation implicitly treated iterative retrieval driven by
sufficiency as an unexplored problem.

The Phase 0 literature review showed that this is no longer defensible. Later
work already combines sufficiency judgments with multi-round retrieval.

The claim was narrowed from introducing the idea to experimentally isolating
and measuring the stopping problem with exact per-step labels.

### 2. Treating Joren's sufficiency label as interchangeable with the project's label

Joren's definition allows a context to be sufficient when it supports a
plausible answer, even when that answer is wrong relative to the gold answer.

The project initially approached the definitions as if they were directly
interchangeable. S3 without truncation cues exposed the difference most
clearly: a partial list is itself a plausible answer, so Joren's definition
calls that context sufficient while the project's label does not. S2 and S4
first looked like the obvious cases, but they depend on how careful the rater
is, not on the definition.

The project therefore defines sufficiency operationally through minimal
sufficient sets for the gold answer. This is a stronger, experiment-specific
oracle rather than a replacement for Joren's definition.

### 3. Conflating decision errors with answer errors

The reading exposed a case that the initial taxonomy did not make sufficiently
explicit: an agent can stop on insufficient context and still produce the
correct answer through parametric knowledge or chance.

The project therefore treats stopping correctness and answer correctness as
separate measurements. A stopping decision can be wrong even when the final
answer happens to be correct.

### 4. Treating iterative retrieval as the contribution by itself

The project could easily have become another implementation of agentic or
iterative RAG.

Phase 0 clarified that the architecture is not the main research object. The
research object is the detection of sequential sufficiency and the value of
using that signal as a stopping policy.

### 5. Assuming a larger or more flexible evaluator automatically gives a better experiment

Joren's comparison between lexical and LLM-based evaluation showed that the
choice of evaluator can materially change absolute correctness rates.

Rather than adopting an LLM judge for flexibility, the project chose a
deterministic grader with explicit aliases. This preserves auditability and
keeps the primary measurement independent of the A4 treatment.
