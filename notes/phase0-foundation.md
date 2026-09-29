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

## Hypothesis, measurability gate and contingency (`docs/hypothesis.md`, `docs/measurability-gate.md`, `docs/contingency.md`)

## Data sources and licensing — G1 (`docs/data-sources.md`)

## ADRs 001–010

## Experiment registry — E-001 (full draft) and E-002 (typed expansion)

## Outcome space checked by test (`tests/test_outcome_space.py`)

## Power script reproducing P2's E-026 (`evaluation/power.py`)

## Token meter and cost estimate before any loop

## Scaffold, docker-compose (Neo4j + Phoenix) and CI

## Initial README with problem statement and trademark notice

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
