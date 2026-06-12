# trust nudge D 30 seed check

- seeds: `1000-1029` (30 consecutive seeds)
- years: `80`
- fixed baseline: `society_lab_v1_4_life_senses_memory_shadow3.py`
- experiment: D default in `society_lab_v1_4_life_bridge_trust_nudge_experiment.py`

## Aggregate

- nudge seeds: `8/30` (26.67%)
- no-nudge seeds: `22`
- nudged seeds with body divergence by Y80: `7/8`
- pre-nudge mismatch seeds: `0`
- no-nudge shadow mismatches: `0`
- first-nudge trust-only confirmed: `8/8`
- total memory_shadow: `20`
- total life_bridge_potential: `19`
- total life_trust_nudge: `9`
- first body divergence delay: min/avg/max = `2` / `11.71` / `36` years

## First Body Divergence Type

Broad classes normalize `memory_shared` and `shared_narrative` as `memory_lineage`.

| broad type | seeds |
| --- | ---: |
| `birth` | 1 |
| `memory_lineage` | 2 |
| `memory_lineage_vs_birth` | 1 |
| `memory_lineage_vs_death` | 1 |
| `narrative_divergence_vs_death` | 1 |
| `none` | 1 |
| `problem` | 1 |

Raw first visible log/event classes:

| type | seeds |
| --- | ---: |
| `birth` | 1 |
| `memory_shared` | 2 |
| `narrative_divergence_vs_death` | 1 |
| `none` | 1 |
| `problem_detected` | 1 |
| `shared_narrative_vs_birth` | 1 |
| `shared_narrative_vs_death` | 1 |

## Seed Table

| seed | nudge | pre mismatch | first nudge | trust-only | first body divergence | delay | broad type | raw type | memory_shadow | bridge_potential | final summary diff keys |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| 1000 | 0 | 0 | - | - | - | - | `none` | `none` | 2 | 3 | - |
| 1001 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1002 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1003 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1004 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1005 | 0 | 0 | - | - | - | - | `none` | `none` | 2 | 1 | - |
| 1006 | 1 | 0 | Y53 | yes | Y62 | 9 | `memory_lineage` | `memory_shared` | 1 | 1 | - |
| 1007 | 0 | 0 | - | - | - | - | `none` | `none` | 1 | 1 | - |
| 1008 | 0 | 0 | - | - | - | - | `none` | `none` | 1 | 1 | - |
| 1009 | 2 | 0 | Y43 | yes | Y67 | 24 | `memory_lineage_vs_death` | `shared_narrative_vs_death` | 3 | 2 | interpretation_action_nudge_count, interpretation_support_nudge_count, memory_shared_count, project_aftermath_trace_count, project_success_count, proposal_count, shared_narrative_count, support_chain_trace_count |
| 1010 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1011 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1012 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1013 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 1 | - |
| 1014 | 1 | 0 | Y45 | yes | - | - | `none` | `none` | 1 | 1 | - |
| 1015 | 1 | 0 | Y44 | yes | Y46 | 2 | `memory_lineage_vs_birth` | `shared_narrative_vs_birth` | 1 | 1 | death_count, final_population, interpretation_action_nudge_count, interpretation_support_nudge_count, memory_shared_count, narrative_divergence_count, network_split_count, project_aftermath_trace_count, project_failure_count, proposal_count, shared_narrative_count, support_chain_trace_count |
| 1016 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1017 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1018 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1019 | 1 | 0 | Y42 | yes | Y48 | 6 | `memory_lineage` | `memory_shared` | 2 | 1 | birth_count, death_count, final_population, interpretation_action_nudge_count, interpretation_support_nudge_count, memory_shared_count, narrative_divergence_count, network_split_count, proposal_count, support_chain_trace_count |
| 1020 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1021 | 1 | 0 | Y39 | yes | Y41 | 2 | `narrative_divergence_vs_death` | `narrative_divergence_vs_death` | 3 | 2 | interpretation_action_nudge_count, interpretation_support_nudge_count, memory_shared_count, proposal_count, shared_narrative_count, support_chain_trace_count |
| 1022 | 1 | 0 | Y49 | yes | Y52 | 3 | `problem` | `problem_detected` | 2 | 1 | birth_count, death_count, final_population, interpretation_action_nudge_count, interpretation_support_nudge_count, memory_shared_count, network_split_count, project_aftermath_trace_count, project_success_count, proposal_count, shared_narrative_count, support_chain_trace_count |
| 1023 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 1 | - |
| 1024 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1025 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1026 | 1 | 0 | Y40 | yes | Y76 | 36 | `birth` | `birth` | 1 | 1 | - |
| 1027 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |
| 1028 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 1 | - |
| 1029 | 0 | 0 | - | - | - | - | `none` | `none` | 0 | 0 | - |

## Nudge Rows

### seed1006

- Y53 life_trust_nudge       p013,p028     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=storehouse; weather=clear; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1009

- Y43 life_trust_nudge       p017,p018     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=tea_house; weather=light_mist; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005
- Y61 life_trust_nudge       p004,p030     potential=13.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=tea_house; weather=clear; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1014

- Y45 life_trust_nudge       p008,p055     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=well; weather=heavy_rain; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1015

- Y44 life_trust_nudge       p005,p008     potential=13.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=tea_house; weather=rain_on_roof; trust_before=0.0000,0.7385; trust_after=0.0005,0.7390

### seed1019

- Y42 life_trust_nudge       p011,p023     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=hearth; weather=rain_on_roof; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1021

- Y39 life_trust_nudge       p026,p039     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=tea_house; weather=heavy_rain; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1022

- Y49 life_trust_nudge       p000,p007     potential=12.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=storehouse; weather=rain_on_roof; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

### seed1026

- Y40 life_trust_nudge       p002,p024     potential=10.0; delta=0.0005; threshold=10.0; cooldown=16; max_per_year=1; max_per_pair_total=1; source=memory_shadow; place=hearth; weather=light_mist; trust_before=0.0000,0.0000; trust_after=0.0005,0.0005

## Reading

In this 30-seed window, D keeps all pre-nudge states contained: there were no pre-nudge mismatches, and no no-nudge seed drifted away from shadow3.

The bridge remains sparse. `memory_shadow` is common enough to create candidates, fewer cases become `life_bridge_potential`, and only a smaller subset reaches `life_trust_nudge`.

When a nudge appears, the first nudge year is still trust-only in every nudged seed in this run. Body divergence appears later, so the branch reads as a delayed intervention effect rather than a hidden RNG mismatch before the bridge.
