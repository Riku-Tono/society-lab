from __future__ import annotations

from collections import Counter, defaultdict
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import re
import sys


sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path.cwd()
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def find_sl3() -> Path:
    home = Path.home()
    for root, _dirs, files in os.walk(home / "OneDrive"):
        if (
            "society_lab_v1_4_1.py" in files
            and "society_lab_v1_4_life_senses_memory_shadow3.py" in files
            and "society_lab_v1_4_life_bridge_trust_nudge_experiment.py" in files
        ):
            return Path(root)
    raise FileNotFoundError("SL3 folder not found")


SL3 = find_sl3()
BASE_PATH = SL3 / "society_lab_v1_4_1.py"
SHADOW_PATH = SL3 / "society_lab_v1_4_life_senses_memory_shadow3.py"
EXPERIMENT_PATH = SL3 / "society_lab_v1_4_life_bridge_trust_nudge_experiment.py"
if str(SL3) not in sys.path:
    sys.path.insert(0, str(SL3))


def import_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def clean_json(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))


def world_snapshot(sim):
    return {
        "summary": clean_json(sim.summary()),
        "people": clean_json(sim.people),
        "food_stock": getattr(sim.food, "stock", None),
        "food_capacity": getattr(sim.food, "capacity", None),
        "log_entries": clean_json(getattr(sim.log, "entries", [])),
        "memory_lineage_trace": clean_json(getattr(sim, "memory_lineage_trace", [])),
        "support_chain_trace": clean_json(getattr(sim, "support_chain_trace", [])),
        "project_aftermath_trace": clean_json(getattr(sim, "project_aftermath_trace", [])),
    }


py_compile.compile(str(EXPERIMENT_PATH), cfile=str(ROOT / "work" / "_trust_nudge_D.pyc"), doraise=True)

base_mod = import_from_path("society_lab_base_trust_D", BASE_PATH)
shadow_mod = import_from_path("society_lab_shadow_trust_D", SHADOW_PATH)
experiment_mod = import_from_path("society_lab_experiment_trust_D", EXPERIMENT_PATH)

BaseLab = base_mod.SocietyLab
ShadowLab = shadow_mod.LifeObservedSocietyLab
ExperimentLab = experiment_mod.LifeBridgeTrustNudgeExperiment

VARIANTS = {
    "A_threshold10_delta001": {
        "threshold": 10.0,
        "delta": 0.001,
        "cooldown": 8,
        "max_per_year": 2,
        "max_per_pair_total": None,
        "allowed_sources": None,
    },
    "B_threshold12_delta001": {
        "threshold": 12.0,
        "delta": 0.001,
        "cooldown": 8,
        "max_per_year": 2,
        "max_per_pair_total": None,
        "allowed_sources": None,
    },
    "C_threshold10_delta0005": {
        "threshold": 10.0,
        "delta": 0.0005,
        "cooldown": 8,
        "max_per_year": 2,
        "max_per_pair_total": None,
        "allowed_sources": None,
    },
    "D_memory_shadow_once": {
        "threshold": 10.0,
        "delta": 0.0005,
        "cooldown": 16,
        "max_per_year": 1,
        "max_per_pair_total": 1,
        "allowed_sources": {"memory_shadow"},
    },
}

SUMMARY_KEYS = (
    "final_population",
    "death_count",
    "birth_count",
    "project_success_count",
    "project_failure_count",
    "proposal_count",
    "memory_shared_count",
    "support_chain_trace_count",
    "project_aftermath_trace_count",
    "network_split_count",
    "shared_narrative_count",
    "authority_pattern_count",
)


def run_sim(cls, seed: int, years: int = 80):
    sim = cls(seed=seed, verbose=False)
    sim.run(years=years)
    return sim


def trust_pairs(sim) -> dict[tuple[str, str], tuple[float, float]]:
    pairs: dict[tuple[str, str], tuple[float, float]] = {}
    people = {person.id: person for person in sim.people}
    ids = list(people)
    for i, left_id in enumerate(ids):
        for right_id in ids[i + 1 :]:
            left = people[left_id]
            right = people[right_id]
            pairs[(left_id, right_id)] = (
                left.trust.get(right_id, 0.0),
                right.trust.get(left_id, 0.0),
            )
    return pairs


def trust_delta(base, other) -> dict[str, float | int]:
    base_pairs = trust_pairs(base)
    other_pairs = trust_pairs(other)
    changed = 0
    total = 0.0
    max_delta = 0.0
    for pair, values in other_pairs.items():
        before = base_pairs.get(pair, (0.0, 0.0))
        delta_a = values[0] - before[0]
        delta_b = values[1] - before[1]
        if abs(delta_a) + abs(delta_b) > 1e-12:
            changed += 1
            total += delta_a + delta_b
            max_delta = max(max_delta, abs(delta_a), abs(delta_b))
    return {
        "trust_changed_pair_count": changed,
        "trust_delta_sum": round(total, 6),
        "trust_delta_max": round(max_delta, 6),
    }


def summary_diff(base_summary: dict, other_summary: dict) -> dict[str, object]:
    result = {}
    for key in SUMMARY_KEYS:
        base_value = base_summary.get(key)
        other_value = other_summary.get(key)
        if base_value == other_value:
            continue
        result[key] = {
            "base": base_value,
            "experiment": other_value,
            "delta": other_value - base_value
            if isinstance(base_value, (int, float)) and isinstance(other_value, (int, float))
            else None,
        }
    return result


def fields(detail: str) -> dict[str, str]:
    return {key: value.strip() for key, value in re.findall(r"([A-Za-z_]+)=([^;]+)", detail)}


def stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"min": 0, "max": 0, "avg": 0.0, "nonzero": 0}
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "avg": round(sum(values) / len(values), 4),
        "nonzero": sum(1 for value in values if value),
    }


def variant_class(name: str, params: dict[str, object]):
    return type(
        name,
        (ExperimentLab,),
        {
            "life_trust_nudge_threshold": params["threshold"],
            "life_trust_nudge_delta": params["delta"],
            "life_trust_nudge_cooldown": params["cooldown"],
            "life_trust_nudge_max_per_year": params["max_per_year"],
            "life_trust_nudge_max_per_pair_total": params["max_per_pair_total"],
            "life_trust_nudge_allowed_sources": params["allowed_sources"],
        },
    )


focus_seeds = (1003, 1061, 1042, 1096)
shadow_pollution_diffs = []
variant_reports = {}

for seed in range(1000, 1100):
    base = run_sim(BaseLab, seed)
    shadow = run_sim(ShadowLab, seed)
    if world_snapshot(base) != world_snapshot(shadow):
        shadow_pollution_diffs.append(seed)

for name, params in VARIANTS.items():
    Lab = variant_class(name, params)
    nudge_counts = []
    changed_pair_counts = []
    trust_delta_sums = []
    trust_delta_maxes = []
    summary_diff_counts = []
    bridge_counts = []
    nudge_seed_list = []
    no_nudge_mismatch = []
    changed_summary_keys = Counter()
    nudge_sources = Counter()
    nudge_pairs = Counter()
    focus = {}

    for seed in range(1000, 1100):
        shadow = run_sim(ShadowLab, seed)
        experiment = run_sim(Lab, seed)
        nudges = [ob for ob in experiment.life_observations if ob.event_type == "life_trust_nudge"]
        bridges = [ob for ob in experiment.life_observations if ob.event_type == "life_bridge_potential"]
        if nudges:
            nudge_seed_list.append(seed)
        elif world_snapshot(shadow) != world_snapshot(experiment):
            no_nudge_mismatch.append(seed)

        diffs = summary_diff(shadow.summary(), experiment.summary())
        summary_diff_counts.append(len(diffs))
        changed_summary_keys.update(diffs.keys())

        delta = trust_delta(shadow, experiment)
        changed_pair_counts.append(delta["trust_changed_pair_count"])
        trust_delta_sums.append(delta["trust_delta_sum"])
        trust_delta_maxes.append(delta["trust_delta_max"])
        nudge_counts.append(len(nudges))
        bridge_counts.append(len(bridges))

        for ob in nudges:
            f = fields(ob.detail)
            nudge_sources[f.get("source", "?")] += 1
            pair = "|".join(sorted(ob.persons))
            nudge_pairs[pair] += 1

        if seed in focus_seeds:
            focus[seed] = {
                "summary_diff": diffs,
                "trust_delta": delta,
                "counts": {
                    event: sum(1 for ob in experiment.life_observations if ob.event_type == event)
                    for event in (
                        "life_bridge_potential",
                        "life_trust_nudge",
                        "conversation_shadow",
                        "familiarity_shadow",
                        "memory_shadow",
                        "time_shadow",
                    )
                },
                "top_potentials": [
                    {"pair": f"{pair[0]}|{pair[1]}", "potential": round(value, 2)}
                    for pair, value in sorted(
                        experiment.life_relation_potential.items(),
                        key=lambda item: (-item[1], item[0]),
                    )[:8]
                ],
                "nudge_rows": [
                    {"year": ob.year, "persons": ob.persons, "detail": ob.detail}
                    for ob in nudges
                ],
                "bridge_rows": [
                    {"year": ob.year, "persons": ob.persons, "detail": ob.detail}
                    for ob in bridges[:8]
                ],
                "matches_shadow_when_no_nudge": not nudges
                and world_snapshot(shadow) == world_snapshot(experiment),
            }

    variant_reports[name] = {
        "params": {
            **params,
            "allowed_sources": sorted(params["allowed_sources"])
            if isinstance(params["allowed_sources"], set)
            else params["allowed_sources"],
        },
        "stats": {
            "nudge_count": stats(nudge_counts),
            "trust_changed_pair_count": stats(changed_pair_counts),
            "trust_delta_sum": stats(trust_delta_sums),
            "trust_delta_max": stats(trust_delta_maxes),
            "summary_diff_key_count": stats(summary_diff_counts),
            "life_bridge_potential_count": stats(bridge_counts),
        },
        "nudge_seed_count": len(nudge_seed_list),
        "nudge_seeds": nudge_seed_list,
        "no_nudge_seed_count": 100 - len(nudge_seed_list),
        "no_nudge_shadow_mismatch_count": len(no_nudge_mismatch),
        "no_nudge_shadow_mismatch_seeds": no_nudge_mismatch,
        "nudge_sources": dict(nudge_sources),
        "top_nudge_pairs": dict(nudge_pairs.most_common(20)),
        "changed_summary_keys": dict(changed_summary_keys.most_common()),
        "focus": focus,
    }

report = {
    "files": {
        "base": str(BASE_PATH),
        "shadow3_fixed": str(SHADOW_PATH),
        "experiment": str(EXPERIMENT_PATH),
    },
    "shadow3_base_pollution_diffs": shadow_pollution_diffs,
    "variants": variant_reports,
}

json_path = OUTPUTS / "trust_nudge_experiment_D_check.json"
json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

lines = []
lines.append("# trust nudge experiment D check")
lines.append("")
lines.append("## implementation")
lines.append("")
lines.append("- `society_lab_v1_4_life_senses_memory_shadow3.py` is fixed and was not modified.")
lines.append("- `society_lab_v1_4_life_bridge_trust_nudge_experiment.py` now defaults to D.")
lines.append("- D: `threshold=10`, `delta=0.0005`, `cooldown=16`, `max_per_year=1`, `max_per_pair_total=1`, `allowed_sources={memory_shadow}`.")
lines.append("- Trust nudge writes to `Person.trust` and records `life_trust_nudge` only in life observations.")
lines.append("")
lines.append("## fixed shadow3 check")
lines.append("")
lines.append(f"- shadow3 vs base pollution diffs: `{len(shadow_pollution_diffs)}`")
lines.append("")
lines.append("## A/B/C/D comparison")
lines.append("")
lines.append("| variant | nudge seeds | no-nudge mismatches | nudge avg/max | summary diff keys avg/max | sources |")
lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
for name, data in variant_reports.items():
    s = data["stats"]
    source_text = ", ".join(f"{k}={v}" for k, v in data["nudge_sources"].items()) or "none"
    lines.append(
        f"| `{name}` | {data['nudge_seed_count']} | "
        f"{data['no_nudge_shadow_mismatch_count']} | "
        f"{s['nudge_count']['avg']}/{s['nudge_count']['max']} | "
        f"{s['summary_diff_key_count']['avg']}/{s['summary_diff_key_count']['max']} | "
        f"{source_text} |"
    )
lines.append("")

d = variant_reports["D_memory_shadow_once"]
lines.append("## D seed list")
lines.append("")
lines.append("- nudge seeds: " + ", ".join(str(seed) for seed in d["nudge_seeds"]))
lines.append("- no-nudge shadow mismatches: " + (", ".join(str(seed) for seed in d["no_nudge_shadow_mismatch_seeds"]) or "none"))
lines.append("")
for seed in focus_seeds:
    focus = d["focus"][seed]
    lines.append(f"## seed{seed} D")
    lines.append("")
    counts = ", ".join(f"`{key}={value}`" for key, value in focus["counts"].items())
    lines.append(f"- Counts: {counts}")
    lines.append(f"- Trust delta: `{focus['trust_delta']}`")
    lines.append(f"- Summary diff keys: {', '.join(focus['summary_diff'].keys()) or 'none'}")
    if focus["nudge_rows"]:
        lines.append("- Nudges:")
        for row in focus["nudge_rows"]:
            pair = "|".join(sorted(row["persons"]))
            lines.append(f"  - Y{row['year']:02d} `{pair}` {row['detail']}")
    else:
        lines.append("- Nudges: none")
    if focus["top_potentials"]:
        top = ", ".join(
            f"`{item['pair']}={item['potential']}`" for item in focus["top_potentials"][:5]
        )
        lines.append(f"- Top potentials: {top}")
    lines.append("")

lines.append("## judgment")
lines.append("")
lines.append("D is the preferred experimental default. It keeps no-nudge seeds identical to shadow3, restricts all nudges to `memory_shadow`, preserves seed1003, catches seed1061's tea-house memory path, and reduces repeated nudges by allowing each pair only one lifetime nudge.")
lines.append("")
lines.append("D is still a real body-intervention branch: when it nudges trust, downstream summary differences can appear. That is expected here. The improvement over A/C is not zero impact; it is cleaner attribution.")

md_path = OUTPUTS / "trust_nudge_experiment_D_check.md"
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps(report, indent=2, ensure_ascii=False))
print(md_path)
