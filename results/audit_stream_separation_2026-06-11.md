# Audit Record: Reproduction of RNG Stream Separation Experiment "Nudge 25/100 vs Placebo 7/100"

- Date: 2026-06-11
- Conducted by: Claude (Fable 5) / claude.ai sandbox environment
- Type: Pre-publication verification (reproduction check). No new implementations, parameter changes, or amplifier additions.

## 1. Purpose

Verify that the following numbers — the central pillar of the essay — reproduce with the same code and same seed range.

> In the RNG-stream-separated model (reseeded every year via hash(seed, year, stream)),
> interpretation nudge ON vs OFF diverges in 25/100 seeds (hard diverged),
> and a placebo single draw into the support stream (@Y30) diverges in 7/100 seeds.

## 2. Code and Artifacts Under Test (all unmodified)

| File | SHA-256 | Notes |
|---|---|---|
| society_lab_v1_4.py | 19ca44967bf3a4edc20b3f054deddf4c916c5cf9a946052069af229ea67efa41 | v1.4 core. 48,814 bytes / 1,265 lines |
| society_lab_v1_4_1.py | b7795f248f27a82eb699aae775f9f9d32d739b0d9e4079bdc275ef081c0897c8 | Observation-enhanced build (not used in this audit) |
| bridge.py | b2cb0da772e7c19e223df258a6b31a469c348d6ee29c3b5fa1a507d5a42aca5b | ConfigurableSocietyLab definition |
| stream_separation.py | 939c69d55d1a38655f9dd4b2662b22e98b81e8b06a1965d78f9cd24614f9a6bc | Experiment runner (E1/E2/E3) |
| stream_separation_results.json (original) | 4998b6d51393f58bb14ef03f4a3660b2212130e12171fa279593465d1ba5adee | Reference artifact to check against |

## 3. Execution Environment

- Python 3.12.3 (RNG uses only stdlib random / hashlib.md5)
- numpy 2.4.4 (required only for bridge.py import resolution; not used in any computation on the audit path)
- OS: Ubuntu 24 (Linux sandbox)

## 4. Environment Provisioning (disclosure)

bridge.py imports `society_lab` / `rivalry_ca` / `moat_stage2d` at module level.
The computation path under audit (ConfigurableSocietyLab → StreamSeparatedSocietyLab) uses only `society_lab.SocietyLab`, so the following provisions were made:

1. `society_lab.py` := byte-identical copy of `society_lab_v1_4.py` (SHA-256 match confirmed; rename only)
2. `rivalry_ca.py` / `moat_stage2d.py` := inert stubs (raise RuntimeError immediately if called, making computation contamination structurally impossible). No stub-related exceptions occurred during execution.

The validity of provision (1) is supported by the provenance check in §5.

## 5. Pre-verification (v1.4 core provenance check)

The frozen society_lab_v1_4.py was executed unmodified and checked against known v1.4 values recorded in conversation logs.

| Item (seed 1003, 80 years) | Logged value | Re-execution value | Match |
|---|---|---|---|
| birth_count | 18 | 18 | ✓ |
| project_failure_count | 9 | 9 | ✓ |
| memory_shared_count | 323 | 323 | ✓ |

Additionally, determinism was confirmed by running seeds 1000 / 1003 / 1096 twice each and verifying complete summary identity.

## 6. Reproduction Run

- Command: `python3 stream_separation.py` (unmodified)
- Seed range: range(1000, 1100), 80 years (as coded)
- Execution time: 27 seconds

### Result Comparison

| Item | Logged value | Original JSON | This re-run | Match |
|---|---|---|---|---|
| E1 diverged | 25/100 | 25 | 25 | ✓ |
| E1 support_only / identical | 14 / 61 | 14 / 61 | 14 / 61 | ✓ |
| E1 diverged mean\|pop_diff\| / max | 0.52 / 2 | 0.52 / 2 | 0.52 / 2 | ✓ |
| E2 support placebo (Y30, 1 draw) | 7/100 | 7 | 7 | ✓ |
| E2 mortality placebo (Y30, 1 draw) | (not in heading) | 36 | 36 | ✓ |
| E3 seed 1036 | identical | identical | identical | ✓ |
| E3 seed 1096 causal ladder | Y46→Y52→Y55 | same | Y46:failure/started → Y52:food → Y55:death/pop | ✓ |

### Byte-level Identity

The SHA-256 of the re-run's stream_separation_results.json is
`4998b6d51393f58bb14ef03f4a3660b2212130e12171fa279593465d1ba5adee`,
**identical to the original**. This is byte-level reproduction, beyond mere numerical agreement. Because all random draws use the consumption-order-independent hash(seed, year, stream) design, the output is identical even across different environments — confirming the design claim.

## 7. Verdict

**"Nudge 25/100 vs Placebo 7/100" is confirmed as reproduced. Approved as a pillar of the main essay.**

## 8. Limitations to Note Alongside Adoption (carried over from audit)

1. **Stream-dependent placebo sensitivity**: The same placebo injected into the mortality stream diverges 36/100 seeds. The support placebo (7/100) is the appropriate control because the nudge's entry point is the support channel. This should be noted in the limitations section alongside the code's own caveat that "within-year, within-stream consumption shifts remain."
2. **Cross-world comparison is limited**: The separated model reseeds every year, making it a different world from the v1.4 coupled model. Comparison with the coupled model's 38/100 is valid only for the ON-vs-OFF difference structure (as noted in the original JSON).
3. **Effect size**: The final population difference among diverged seeds is mean 0.52, max 2. The claim is about "the existence of path residue," not "the magnitude of the effect."
4. **Source duplication**: This audit text appears verbatim in both Log 7 and Log 10. When citing, treat as a single report (1 source).

## 9. Audit Chain Status

1. v1.4 core provenance confirmed (3 known values for seed 1003 independently matched) — done
2. Static match between artifact JSON and logged report values — done
3. Execution reproduction with same code and same seed range (byte-identical) — done (this record)

Outstanding: Cross-verification by a third party (Codex / Grok / ChatGPT in a separate environment) using the same procedure. This record and the accompanying files are sufficient to carry it out.

## 10. Accompanying Files

- stream_separation_results_rerun_2026-06-11.json (this re-run's output; byte-identical to the original)
