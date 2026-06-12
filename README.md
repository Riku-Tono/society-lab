# SocietyLab v1.4 — Can Interpretation Reach History?

[Japanese version](ja/README.md)

SocietyLab v1.4 is a small agent-based village simulation written in Python.
It asks one question:

> **Can a difference in how people interpret events ever reach probabilistic history — who dies, who is born, and how the village changes?**

v1.4 is the base model built to test that question. It has no explicit variables for religion, ideology, authority, class, or factions. It only has a minimal set of materials: memory, trust, voice, and interpretation. A tiny **3% interpretation nudge** is added, and the model observes whether that difference can bend 80 years of village history.

This project was developed by one human working with several AIs (Claude / ChatGPT / Codex / Grok), with the models checking and auditing one another's results.

---

## Conclusion First

> **Tiny interpretation nudges almost disappear as a force that moves history. But they do not disappear completely.**
> Even after a strict RNG-stream separation audit, small differences remain in some seeds through a social channel: support -> project -> resource -> death. The effect is small (maximum 2 people over 80 years, average 0.5 among diverged seeds). It is neither strong causality nor pure noise, but a **path residue** that passes only when high-impact actors sit near support thresholds.

This is not a flashy result. In fact, much of the initially dramatic result — 38/100 seeds diverging, with a maximum population difference of 14 — turned out to be an **RNG bookkeeping artifact**. The core of this project is the process of stripping away that artifact and isolating the small residue that remains.

---

## Model Lineage

v1.4 did not appear all at once. It is the fifth step in a small sequence.

| Version | Added |
|---|---|
| v1.0 | Trust network |
| v1.1 | Cooperation and failure |
| v1.2 | Voice weight (`voice_weight`) |
| v1.3 | Seeds of interpretation — event interpretation is **observed only** and does not affect action |
| **v1.4** | **Interpretation weakly affects action** — interpretation bias adds only +0.03 to proposal choice and support decisions |

The difference between v1.3 and v1.4 is only one bridge: interpretation -> support. That minimal intervention is the premise behind every later claim.

---

## How the World Works

The model runs a village of about 30 to 40 people for 80 years. It uses plain Python with no external runtime dependency for the core simulation.

**Agent attributes** include age, sex, health, hunger, fear, charisma, voice weight, trust toward other people, and three interpretation biases: **spiritual / practical / blame**.

The rough yearly cycle is:

```text
crisis / death / project
-> memory (with intensity / decay / interpretation / generation)
-> interpretation
-> trust / support / proposal
-> project success or failure (store_food, dig_well, tea_house, hunt_group)
-> fear / hunger / food / death / birth
-> back into memory
```

The heart of the model is `_support_proposals()`. Whether someone supports a proposal is determined by a mixture of trust, charisma, voice, project relevance, fear, and randomness. **In v1.4, the interpretation nudge adds only +0.03 here.** A person with a compatible interpretation bias, such as blame, becomes just slightly more likely to support a matching proposal. That is all.

There are no explicit variables for religion, factions, or authority. Yet when reading the logs, one can start seeing things that resemble storytellers, people who carry failure, or villages that quietly shrink. That is what makes the model interesting, and also what makes it easy to overread.

---

## What Happened — Three Acts

### Act 1: The Apparent Effect

With coupled RNG — a naive implementation where all events share a single random stream — running 100 seeds produced divergence in **38/100 seeds** between nudge ON and OFF, with a maximum population difference of 14. In seed1003, a large, noisy village seemed to branch into a smaller, quieter village tilted toward blame. A seemingly minor person named Hana, with charisma 0.478, little trust, and death in Year 28, appeared to sit at a turning point in history.

### Act 2: Collapse

A placebo test then added only one extra random draw instead of the interpretation nudge. It caused **100/100 seeds to diverge**. That means most of the coupled-RNG divergence was not causal. It was a **bookkeeping artifact caused by shifted random-number consumption**. The dramatic numbers and seed stories from Act 1 had to be discarded as evidence.

### Act 3: Path Residue

The experiment was rebuilt with RNG stream separation. Support, death, birth, and other random streams are drawn independently using `hash(seed, year, stream)`, blocking the bookkeeping artifact. The model was then tested again.

| Test | Result |
|---|---|
| Nudge ON vs OFF | **25/100 seeds diverged** |
| Support placebo (one draw) | **7/100 seeds diverged** |
| Population difference among diverged seeds | **average 0.52, maximum 2** over 80 years |
| seed1036 | fully identical — a control case where coupled-RNG divergence was pure bookkeeping |
| seed1096 | **causal ladder**: Y46 project difference -> Y52 food difference -> Y55 death difference. Population remains identical until death probability changes under the same random draw. |

The remaining differences are small. But they are distinguishable from the support placebo, and their entry path follows the same skeleton:

```text
interpretation -> support -> project choice -> resource -> death
```

This skeleton converged across two independent implementations (Claude and Grok). Across 10 inspected seeds, the starting actor did not repeat. Hana was not special. The residue passes only when a high-impact node — for example charisma >= 0.65 or voice_weight >= 0.08 — happens to sit near a support threshold.

---

## Reproducibility

The central experiment, "nudge 25/100 vs placebo 7/100," was rerun in an independent environment using four frozen files with SHA-256 records. The output JSON SHA-256 matched the original **byte for byte**, not merely numerically. Because randomness is drawn from `hash(seed, year, stream)` rather than consumption order, the same history is reproduced across environments.

- Experiment script: `src/stream_separation.py`
- Base model: `src/society_lab_v1_4.py`
- Bridge: `src/bridge.py`
- Original result: `results/stream_separation_results.json`
- Rerun result: `results/stream_separation_results_rerun_2026-06-11.json` (SHA-256 identical to the original)
- Audit record: `results/audit_stream_separation_2026-06-11.md`
- Seed range: 1000-1099, 80 years each

---

## Please Do Not Overread This

This model is good at tempting narrative interpretation, so the limits need to be stated clearly.

1. **"A residue exists" does not mean "interpretation has strong social causal power."** The remaining difference is at most 2 people over 80 years. It is a residue, not a driving force.
2. **Divergence rates such as 25% are not robust quantities.** They depend on the RNG separation method. The robust part is the entry-path skeleton, not the exact rate.
3. **The coupled-RNG numbers (38/100, population difference 14) should not be used as evidence.** They were confirmed as bookkeeping artifacts.
4. **If you dissect only diverged seeds, you will always find a story.** A readable story is not itself causal evidence. During this project, we nearly built a "seed1003 cult" ourselves.
5. **Derived v2.x branches that add amplifiers such as infrastructure accumulation or cooperation norms are excluded from the main line.** Their effects reflect the added design, not the v1.4 claim.

---

## How to Read This Repository

```text
.
├── src/        Model and experiment code
│   ├── society_lab_v1_4.py      <- base model; start here
│   ├── society_lab_v1_4_1.py    observation-enhanced variant
│   ├── stream_separation.py     central experiment: RNG separation + placebo
│   └── bridge.py
├── results/    Results and audit records
│   ├── stream_separation_results.json
│   ├── stream_separation_results_rerun_2026-06-11.json
│   └── audit_stream_separation_2026-06-11.md
├── docs/       Documentation
├── ja/         Japanese version
└── archives/   Raw logs and excluded branches
```

Start with this README and `src/society_lab_v1_4.py`. The model is small enough to read as a single file.

To follow the verification, run `src/stream_separation.py` (usually several tens of seconds). If the output JSON hash matches the original, the history has replayed exactly in your environment. The audit procedure and judgment are documented in `results/audit_stream_separation_2026-06-11.md`.

For a concrete example, inspect seed1096. It shows the Y46 -> Y52 -> Y55 causal ladder: the same random draw is used, but interpretation changes a project path, food changes later, death probability changes, and life/death flips.

---

*A civilization simulation built and audited by one human and several AIs, about whether a 3% difference in how people interpret events can ever reach who lives and who dies. Mostly, it can't. But not entirely — and the "not entirely" has a shape.*
