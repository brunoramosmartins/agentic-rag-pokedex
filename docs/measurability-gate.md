# Measurability Gate

**Status:** answered 2026-09-24, before any pipeline code. Every number here is
either a registered threshold or a scenario; where a number is still an
estimate, the gate says which phase replaces it with a measurement.

**Applicability test.** Is any deliverable of this project a claim that
configuration A is better than, or equivalent to, B on a measured outcome?
**Yes** — three claims (H1, H2, H3; see [`hypothesis.md`](hypothesis.md)). So
the eight gates below are answered in writing, each with the condition that
fails it.

The lesson behind this document comes from the previous project in the trilogy
(`graphrag-mtg-rules`): several comparisons there were designed before their
power, evaluator ceiling or outcome mapping was known, and two had to be
withdrawn. Here those questions are answered first.

---

## Gate 1 — The decision before the architecture

**Decision the project serves:** *"Which detector should an agent over a closed
knowledge base use to decide to stop, continue or abstain, given that an error
costs 4× an abstention — and does any of them pay for itself against a fixed
pipeline?"*

Concrete consumers: (a) the README's recommendation; (b) whether to open a
multi-agent follow-up project — it only makes sense if detecting insufficiency
matters; (c) the v1.1 extension itself — if not even a gold-label stop on the agent's
own search (O2) pays, the classifier loses its reason to exist.

**Fails if:** two possible outcomes lead to the same recommendation. The
outcome space below maps every combination to a different reading, and
`tests/test_outcome_space.py` checks that every combination falls in exactly
one row.

### Outcome space of v1.0 (the first matching row wins)

**Three-valued verdict**, with D = C(reference) − C(treatment) and a 97.5%
BCa bootstrap interval (Bonferroni over the two primary contrasts):

- **supported:** the interval excludes zero in favour of the treatment **and**
  the point estimate is ≥ 0.25;
- **refuted:** the upper limit of the interval is **below 0.25** — the effect,
  if any, is smaller than would justify acting. Includes the treatment being
  worse and a statistically significant gain below the threshold;
- **inconclusive:** everything else.

| # | Condition | Published reading |
|---|---|---|
| 0 | **Gate 8 descriptive branch** (n\* > n_max) | No verdict: detector precision / recall by subtype, with intervals; the README states the budget did not support a cost claim |
| 0b | **Futility fired before the opening** (gate 8) | "A gold-label stop applied to A3's search did not reach the threshold on dev." H1 on eval is descriptive only and cannot enter rows 1–7; H2 is read as usual |
| 1 | **Falsifier fired**: H1 supported, the S0 gain is ≥ 50% of the pooled gain **and** the S0 interval excludes zero in favour of A4 (≥ 10 discordant pairs) | "The gain exists but is not attributable to detection: it appears where there is nothing to detect." |
| 2 | **Placebo explains the gain**: H1 supported, placebo delivered and not harmful, and A4's gain over A4p is < 50% of its gain over A3 | "The gain comes from searching more, not from knowing when to stop." A4's token cost becomes the argument against it |
| 3 | H1 supported and mediation ≥ 50% | **Thesis supported**: deliberate detection reduces cost, and the gain goes through correct stops |
| 4 | H1 supported and mediation < 50% | "The judge helps, but by another path" — diagnosis by subtype and steps spent |
| 5 | H1 refuted | "Deliberate detection does not pay for itself here." If A4 is worse, diagnosis by subtype: abstains too much? stops too late? |
| 6 | H1 inconclusive and the upper 95% limit of O2 − A3 < 0.25 | "A gold-label stop applied to A3's search does not reach the threshold." A finding about the premise |
| 7 | H1 inconclusive and the lower 95% limit of O2 − A3 ≥ 0.25 | "There is room, and the explicit judge does not capture it" — directly motivates v1.1 |
| 7b | H1 inconclusive otherwise | "Neither the gain nor the room is resolved at this n." |

Rows 2–4 are assigned on point estimates, with the interval printed next to the
row. Mediation counts the questions where A4 beats A3 and the judge overrode a
logged "answer" proposal at an insufficient step, **net of the same count for
the placebo A4p**. The exact definitions, the placebo delivery rules and the
A3′ noise null are registered in E-001 (`experiments/registry.md`).

H2 is read independently, with three values (supported / refuted /
inconclusive), each with its sentence registered in E-001. **The H2 population
is always S1–S4**; the typed-expansion measurement (E-002) is descriptive and
cannot change it. λ\* accompanies every row: it is the reading that does not
depend on the λ = 4 scenario
([ADR-005](adr/adr-005-cost-function-lambda-4-and-caps.md)).

---

## Gate 2 — Every candidate outcome, with its labeling cost

| Outcome | How it is labeled | Labeling cost | Role |
|---|---|---|---|
| Expected cost **C** (λ = 4) | Exact match + abstention from structured output | Zero | **Primary** |
| Accuracy; abstention rate | Same | Zero | Secondary |
| Per-step sufficiency, with subtype | By construction: gold chain × evidence units seen | Zero | Mechanism |
| Per-step detector precision / recall | Derived from the above | Zero | Mechanism |
| Operating point (error × abstention) and tipping point λ\* between arms | Derived | Zero | **Headline**: robustness to the choice of λ |
| Risk-coverage curve; AURC | Derived | Zero | Only for an arm with a continuous score (A5, v1.1) |
| Template gap A × B | Derived | Zero | Generalization beyond the generator |
| Tokens, US$, steps | API usage meter | Zero | Owner's cost |
| Calibration (ECE, reliability) | Derived | Zero | v1.1 extension |
| Gold correctness | Human audit, 60 questions | ~2 h per round | Instrument (G3) |
| Grader correctness | Human audit, 100 outputs | ~1 h | Instrument (gate 4) |
| Rendered cases | Manual reading | ~30 min per arm | Every aggregate is backed by a read case |

**Fails if:** any primary or mechanism outcome requires an LLM judge. None does
— the structural difference from the previous project, whose judge ceiling was
0.843.

---

## Gate 3 — Sized under scenarios, never from a point estimate

The per-question outcome is **C ∈ {0, 1, 4}**; the analysis is paired, on
**D = C(reference arm) − C(tested arm)**. The standard deviation of D is unknown
before the dress rehearsal. Starting heuristic: 30% discordant pairs with a
typical |D| ≈ 3 gives **SD ≈ 1.64**.

**Convention printed next to the number:** *n* is the number of **paired
questions pooled over strata S1–S4**, not per stratum. Primary family of two
contrasts (H1, H2). The **verdict is decided by 97.5% BCa intervals**
(Bonferroni, α = 0.025 two-sided per contrast); sign-flip p-values, raw and
Holm-adjusted, are reported as descriptive. Sizing uses the same α, power 0.80.

Minimum detectable effect (in units of C), by pooled n and SD of D:

| pooled n, S1–S4 | SD = 1.0 | SD = 1.5 | SD = 2.0 |
|---:|---:|---:|---:|
| 240 | 0.199 | 0.299 | 0.398 |
| **320 (plan)** | **0.172** | **0.259** | **0.345** |
| 400 | 0.154 | 0.231 | 0.308 |
| 480 | 0.141 | 0.211 | 0.281 |
| 640 | 0.122 | 0.183 | 0.244 |

MDE = (z₀.₉₈₇₅ + z₀.₈₀) · SD / √n = 3.08 · SD / √n. The n needed to detect the
action threshold 0.25: **153 / 343 / 609** pooled questions for SD 1.0 / 1.5 / 2.0.

**Action threshold, written before the run: 0.25 units of C.** In words: 1 in
every 16 questions going from wrong to correct, or 1 in 12 going from wrong to
abstained.

Per-stratum contrasts (n = 80, α = 0.05): detectable effect 0.31 / 0.47 / 0.63.
**That is why per-stratum readings are descriptive**, with intervals, and no
single-stratum claim enters the verdict.

**The falsifier is not a powered interaction test.** An interaction costs ~4×
the n of a simple contrast. The falsifier is a registered rule on the S0
interval, declared as a check, not a power test.

### Power for the *supported* verdict

The table above sizes for "the interval excludes zero". The verdict
**supported** also needs the point estimate to be ≥ 0.25; at a true effect of
exactly 0.25 that happens at most half the time, whatever n is (exactly half
once z·SE ≤ 0.25; slightly less below that n, e.g. 0.498 at n = 320, SD = 2.0). Power is therefore
computed for the event *supported* = {point ≥ 0.25 and lower limit > 0} at a
**design effect Δ_design = 0.35**:

| P(supported) at n = 320 | SD = 1.0 | SD = 1.5 | SD = 2.0 |
|---|---:|---:|---:|
| true effect 0.25 | 0.50 | 0.50 | 0.50 |
| true effect 0.30 | 0.81 | 0.72 | 0.67 |
| **true effect 0.35** | **0.96** | **0.88** | **0.81** |
| true effect 0.40 | 1.00 | 0.96 | 0.91 |

n\* for P(supported) ≥ 0.80 at Δ_design = 0.35: **78 / 175 / 311** pooled
questions for SD 1.0 / 1.5 / 2.0. The plan of 320 holds up to SD ≈ 2.03. In
words: the design is powered to call an effect of 0.35 *supported*; an effect of
exactly 0.25 is a coin flip, and that is stated next to the verdict.
**Δ_design = 0.35 is a budget choice**, not a relevance claim: 0.30 would need
n ≈ 638 at SD 1.5. True effects in [0.25, 0.35) have 50–88% power at the plan.

**Power to refute.** *Refuted* needs the upper limit below 0.25. At n = 320:

| P(refuted) | SD = 1.0 | SD = 1.5 | SD = 2.0 |
|---|---:|---:|---:|
| true effect 0 | 0.99 | 0.77 | 0.50 |
| true effect 0.10 | 0.67 | 0.33 | 0.18 |

A null or small effect with a noisy D often lands in rows 6–7b rather than in
row 5; the README says so when it happens.

**Fails if:** the SD of D measured in the dress rehearsal (Phase 6) requires
n\* > n_max → gate 8.

---

## Gate 4 — The evaluator ceiling

Two instruments produce the truth, and both are audited:

- **Gold** (the generator): human audit of 60 stratified questions, requiring
  ≥ 58 correct (G3 in [`contingency.md`](contingency.md)).
- **Grader** (exact match with alias normalization + abstention from structured
  output): 100 stratified outputs checked by hand, requiring **≥ 98/100**
  agreement before any number is published.

The effective ceiling is the product of the two. No LLM judge on any primary
outcome.

**Fails if:** either falls below its threshold → the instrument is fixed and
re-audited on a **fresh sample** before any arm is measured.

---

## Gate 5 — Superiority or equivalence, chosen now

| Claim | Design | Population | Threshold |
|---|---|---|---|
| **H1** — A4 reduces C vs A3 | Superiority | S1–S4 pooled, eval-L1 | 0.25 |
| **H2** — A4 reduces C vs A2 | Superiority | S1–S4 pooled, eval-L1 | 0.25 |
| H1b — A4 beats A4p | Superiority, secondary (outside Holm) | S1–S4 pooled, eval-L1 | Outcome-space row 2 |
| **H3** — A5 not worse than A4 in C, with fewer tokens | Non-inferiority, margin 0.25, tokens as co-requirement | S1–S4 pooled, eval-L2 | margin 0.25 |

n for H3 (one-sided α = 0.05, power 0.80): **99 / 223 / 396** for SD 1.0 / 1.5 /
2.0; eval-L2 pooled is planned at 240.

Stratum S0 gets **no** equivalence test (there would be no power): it gets a
descriptive interval and the falsifier rule.

**Fails if:** the README makes any comparative claim outside this table.

---

## Gate 6 — The pilot estimates noise, never effect

- **Phase 3 (pilot, dev split):** A0, A1, A2 on 150 questions; A3 on 30.
  Estimates: SD of D between A1 and A3 (proxy), tokens and steps per arm,
  shortcut rate, closed-book accuracy on the twin, implicit-detector firing rate
  (descriptive).
- **Phase 6 (dress rehearsal, dev):** every v1.0 arm on 60 questions.
  Estimates the SD of D for **both** contrasts (A3 − A4 and A2 − A4) and uses
  the **upper limit of each 80% interval** for the final sizing (gate 8).

The effect used for sizing is **always the registered design effect
Δ_design = 0.35** (gate 3), never the difference observed on dev.

Because the gold is generated, **the size of the evaluation split stays
adjustable until its ids are frozen** in Phase 6: the instrument is not fixed
when the floor is computed.

**Fails if:** a performance difference measured on dev is used to choose n,
threshold or stratum.

---

## Gate 7 — No instrument produces a number before running against a known answer

| Instrument | Known answer it runs against |
|---|---|
| Renamer (twin) | Round trip = identity, on 100% of entities |
| Renderer | Every graph fact appears in ≥ 1 unit; the fact → units registry is complete |
| Generator | Human audit (G3), which also reads the flavor text of the entities on every audited chain |
| Shortcut scan | **Planted leaks** — hand-built units naming a question's anchor and its answer outside the gold units, one of them in flavor text — flagged 100%; then run on every generated question, flags published N-of-M |
| Sufficiency labeler | Hand-built trajectories with known labels; 100% correct |
| Grader | Audit of 100 outputs (gate 4) |
| Token meter | Usage reported by the API on 10 calls (`scripts/check_token_meter.py`): the meter's totals equal the raw API usage, and every local input count is within 5% or 10 tokens of the API's |
| Power script | Reproduces the detectability table of the previous project's E-026 (`graphrag-mtg-rules@b3f293e`): every floor, interaction floor and "n needed" (`python -m agentic_pokedex.evaluation.power --reproduce-e026`) |
| Identity probe | **Positive control:** real pages **with their own name masked** must be identified in ≥ 50% (threshold fixed here, before running); if not, the probe is broken, not the twin safe |
| Classifier (v1.1) | Evaluated only on held-out templates and on real trajectory states |
| Depth placebo (A4p) | Total-variation distance ≤ 0.10 per stratum between the realized step distribution and A4's — checked before any result is read; one re-run with a new seed on failure |

**Fails if:** a number in `docs/evaluation.md` comes from an instrument without
its registered check.

---

## Gate 8 — The abort criterion

**Power (Phase 6, before freezing eval-L1 ids):** SD_sup = the upper limit of
the 80% percentile-bootstrap interval of the SD of D on the dress-rehearsal
S1–S4 questions, computed **separately for D(A3 − A4) and D(A2 − A4)**. n\* =
the smallest pooled n with P(supported | Δ_design = 0.35) ≥ 0.80; the larger of
the two n\* governs both contrasts.

**n_max** = the largest pooled S1–S4 n the v1.0 cap pays for after the cut
order ([`contingency.md`](contingency.md), G5), computed with the **Phase 3
measured costs** and written in the decision journal **before the dress
rehearsal**. There is no cap increase after the dress rehearsal.

- **n\* ≤ 320 (SD_sup ≤ 2.03):** keep the plan.
- **320 < n\* ≤ n_max:** the generator draws more questions up to n\*, balanced
  by stratum.
- **n\* > n_max:** H1 and H2 stop being superiority tests (outcome-space row 0).
  The primary claim becomes **descriptive**: detector precision / recall by
  insufficiency subtype, with intervals, and the README states that the budget
  did not support a cost claim. Registered now, not negotiated later.

**Update 2026-09-30 (PI-021, E-001 amendment of the same date).** Two inputs
of this gate changed before any run. (1) eval-L1 questions are clustered
(withheld pairs, S3 moves, S1 lines), so n* is multiplied by a design effect
from the drawn cluster sizes, with ρ = 1 in S3 and S4 and the dress-rehearsal
estimate elsewhere, and inference is by clusters. (2) Balanced growth stops at
a pooled S1–S4 n of 448 (material S1): **n_max_eff = min(n_max, 448)**
replaces n_max in the branches above, and n* > n_max_eff is row 0.

**Futility (Phase 6, before the opening):** if the **upper 80% limit** of the
O2 − A3 difference on dev S1–S4 is below 0.25, a gold-label stop applied to
A3's own search would not reach the threshold. H1 is declared without room
before the opening (outcome-space row 0b). eval-L1 is still opened, for H2 and for a
descriptive H1. O2 is an oracle and is labelled as such wherever quoted; it is
not a strict ceiling under C, because abstaining on sufficient but error-prone
questions can beat it.

**Cost (Phase 3):** if the measured cost per question exceeds 1.3× the estimate,
the cut order is applied before Phase 4.
