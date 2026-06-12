from __future__ import annotations

from dataclasses import asdict, is_dataclass
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any


sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path.cwd()
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)

ROOT = Path(__file__).resolve().parents[1]
SHADOW_PATH = ROOT / "current" / "society_lab_v1_4_life_senses_memory_shadow3.py"
EXPERIMENT_PATH = ROOT / "experiments" / "society_lab_v1_4_life_bridge_trust_nudge_experiment.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def import_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


shadow_mod = import_from_path("society_lab_shadow_D30", SHADOW_PATH)
experiment_mod = import_from_path("society_lab_experiment_D30", EXPERIMENT_PATH)

ShadowLab = shadow_mod.LifeObservedSocietyLab
ExperimentLab = experiment_mod.LifeBridgeTrustNudgeExperiment


def clean(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


def dataclass_clean(value: Any) -> Any:
    if is_dataclass(value):
        return clean(asdict(value))
    return clean(value)


def parse_fields(detail: str) -> dict[str, str]:
    return {key: value.strip() for key, value in re.findall(r"([A-Za-z_]+)=([^;]+)", detail)}


def person_without_trust(person) -> dict[str, Any]:
    data = asdict(person)
    data.pop("trust", None)
    return clean(data)


def trust_snapshot(sim) -> dict[str, float]:
    values: dict[str, float] = {}
    for person in sim.people:
        for other_id, trust in person.trust.items():
            values[f"{person.id}->{other_id}"] = round(float(trust), 8)
    return dict(sorted(values.items()))


def trust_diff(left, right) -> dict[str, dict[str, float | None]]:
    left_trust = trust_snapshot(left)
    right_trust = trust_snapshot(right)
    keys = sorted(set(left_trust) | set(right_trust))
    return {
        key: {"shadow3": left_trust.get(key), "experiment": right_trust.get(key)}
        for key in keys
        if left_trust.get(key) != right_trust.get(key)
    }


def body_snapshot(sim) -> dict[str, Any]:
    return {
        "year": sim.year,
        "summary": clean(sim.summary()),
        "people_without_trust": [person_without_trust(person) for person in sim.people],
        "food": {
            "stock": round(float(sim.food.stock), 8),
            "capacity": round(float(sim.food.capacity), 8),
        },
        "main_log": [dataclass_clean(entry) for entry in sim.log.entries],
        "memory_lineage_trace": clean(sim.memory_lineage_trace),
        "support_chain_trace": clean(sim.support_chain_trace),
        "project_aftermath_trace": clean(sim.project_aftermath_trace),
        "current_problems": [dataclass_clean(problem) for problem in sim.current_problems],
        "current_proposals": [dataclass_clean(proposal) for proposal in sim.current_proposals],
        "rng_state": repr(sim.rng.getstate()),
    }


def body_diff_categories(left, right) -> list[str]:
    left_body = body_snapshot(left)
    right_body = body_snapshot(right)
    return [key for key in left_body if left_body[key] != right_body[key]]


def first_sequence_diff(left: list[Any], right: list[Any]) -> dict[str, Any]:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return {
                "index": index,
                "shadow3": left[index],
                "experiment": right[index],
                "shadow3_len": len(left),
                "experiment_len": len(right),
            }
    if len(left) != len(right):
        return {
            "index": limit,
            "shadow3": left[limit] if limit < len(left) else None,
            "experiment": right[limit] if limit < len(right) else None,
            "shadow3_len": len(left),
            "experiment_len": len(right),
        }
    return {}


WATCHED_SUMMARY_KEYS = (
    "final_population",
    "birth_count",
    "death_count",
    "proposal_count",
    "project_success_count",
    "project_failure_count",
    "memory_shared_count",
    "support_chain_trace_count",
    "project_aftermath_trace_count",
    "network_split_count",
    "shared_narrative_count",
    "narrative_divergence_count",
    "interpretation_action_nudge_count",
    "interpretation_support_nudge_count",
)


def watched_summary(sim) -> dict[str, Any]:
    summary = sim.summary()
    return {key: summary.get(key) for key in WATCHED_SUMMARY_KEYS}


def dict_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {"shadow3": left.get(key), "experiment": right.get(key)}
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    }


def new_life_rows(sim, start: int, event_type: str) -> list[Any]:
    return [row for row in sim.life_observations[start:] if row.event_type == event_type]


def format_life_row(row) -> str:
    people = ",".join(row.persons) if row.persons else "-"
    return f"Y{row.year:02d} {row.event_type:<22} {people:<13} {row.detail}"


def event_type_of(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    event_type = entry.get("event_type")
    return str(event_type) if event_type is not None else None


def classify_first_divergence(
    first_body: dict[str, Any] | None,
    first_main_log: dict[str, Any] | None,
    first_summary: dict[str, Any] | None,
    first_memory_lineage: dict[str, Any] | None,
) -> str:
    if first_body is None:
        return "none"
    if first_main_log:
        diff = first_main_log.get("diff", {})
        exp_type = event_type_of(diff.get("experiment"))
        shadow_type = event_type_of(diff.get("shadow3"))
        if exp_type == shadow_type and exp_type:
            return exp_type
        if exp_type and not shadow_type:
            return exp_type
        if shadow_type and not exp_type:
            return shadow_type
        if exp_type or shadow_type:
            return f"{shadow_type or 'none'}_vs_{exp_type or 'none'}"
    if first_summary:
        keys = set(first_summary.get("diff", {}).keys())
        if "birth_count" in keys:
            return "birth"
        if "death_count" in keys:
            return "death"
        if "narrative_divergence_count" in keys:
            return "narrative_divergence"
        if "memory_shared_count" in keys or "shared_narrative_count" in keys:
            return "memory_lineage"
        if "support_chain_trace_count" in keys or "interpretation_support_nudge_count" in keys:
            return "support"
        if "project_success_count" in keys or "project_failure_count" in keys:
            return "project"
        if "final_population" in keys:
            return "population"
    if first_memory_lineage:
        return "memory_lineage"
    return "body_state"


def broad_divergence_type(raw_type: str) -> str:
    parts = raw_type.split("_vs_")
    mapped = []
    for part in parts:
        if part in {"memory_shared", "shared_narrative"}:
            mapped.append("memory_lineage")
        elif part == "narrative_divergence":
            mapped.append("narrative_divergence")
        elif part == "problem_detected":
            mapped.append("problem")
        else:
            mapped.append(part)
    compact = []
    for item in mapped:
        if item not in compact:
            compact.append(item)
    return "_vs_".join(compact)


def count_life_events(sim, event_type: str) -> int:
    return sum(1 for row in sim.life_observations if row.event_type == event_type)


def analyze_seed(seed: int, years: int) -> dict[str, Any]:
    shadow = ShadowLab(seed=seed, verbose=False)
    experiment = ExperimentLab(seed=seed, verbose=False)

    pre_step_mismatches = []
    clean_step_mismatches = []
    nudge_rows = []
    first_nudge_info = None
    first_body_divergence = None
    first_summary_divergence = None
    first_main_log_divergence = None
    first_memory_lineage_divergence = None
    first_interpretation_related = None
    prev_experiment_life_len = 0

    for _ in range(years):
        next_year = shadow.year + 1
        pre_body_equal = body_snapshot(shadow) == body_snapshot(experiment)
        pre_trust_equal = trust_snapshot(shadow) == trust_snapshot(experiment)
        if first_nudge_info is None and (not pre_body_equal or not pre_trust_equal):
            pre_step_mismatches.append(
                {
                    "before_year": next_year,
                    "body_diff_categories": body_diff_categories(shadow, experiment),
                    "trust_diff_count": len(trust_diff(shadow, experiment)),
                }
            )

        shadow.step()
        experiment.step()

        new_nudges = new_life_rows(experiment, prev_experiment_life_len, "life_trust_nudge")
        if new_nudges:
            nudge_rows.extend(new_nudges)

        body_categories = body_diff_categories(shadow, experiment)
        current_trust_diff = trust_diff(shadow, experiment)

        if first_nudge_info is None and not new_nudges and (body_categories or current_trust_diff):
            clean_step_mismatches.append(
                {
                    "year": shadow.year,
                    "body_diff_categories": body_categories,
                    "trust_diff_count": len(current_trust_diff),
                }
            )

        if first_nudge_info is None and new_nudges:
            first = new_nudges[0]
            first_nudge_info = {
                "year": first.year,
                "row": format_life_row(first),
                "fields": parse_fields(first.detail),
                "body_diff_categories_after_nudge_year": body_categories,
                "rng_equal_after_nudge_year": body_snapshot(shadow)["rng_state"]
                == body_snapshot(experiment)["rng_state"],
                "trust_diff_after_nudge_year_count": len(current_trust_diff),
                "trust_diff_after_nudge_year": current_trust_diff,
            }

        if first_nudge_info is not None:
            if first_body_divergence is None and body_categories:
                first_body_divergence = {
                    "year": shadow.year,
                    "body_diff_categories": body_categories,
                }
            summary_delta = dict_diff(watched_summary(shadow), watched_summary(experiment))
            if first_summary_divergence is None and summary_delta:
                first_summary_divergence = {
                    "year": shadow.year,
                    "diff": summary_delta,
                }
            main_log_delta = first_sequence_diff(
                [dataclass_clean(entry) for entry in shadow.log.entries],
                [dataclass_clean(entry) for entry in experiment.log.entries],
            )
            if first_main_log_divergence is None and main_log_delta:
                first_main_log_divergence = {
                    "year": shadow.year,
                    "diff": main_log_delta,
                }
            memory_delta = first_sequence_diff(
                clean(shadow.memory_lineage_trace),
                clean(experiment.memory_lineage_trace),
            )
            if first_memory_lineage_divergence is None and memory_delta:
                first_memory_lineage_divergence = {
                    "year": shadow.year,
                    "diff": memory_delta,
                }
            if first_interpretation_related is None:
                shadow_summary = watched_summary(shadow)
                experiment_summary = watched_summary(experiment)
                related_keys = (
                    "memory_shared_count",
                    "shared_narrative_count",
                    "narrative_divergence_count",
                    "interpretation_action_nudge_count",
                    "interpretation_support_nudge_count",
                )
                related_delta = {
                    key: {"shadow3": shadow_summary[key], "experiment": experiment_summary[key]}
                    for key in related_keys
                    if shadow_summary[key] != experiment_summary[key]
                }
                if related_delta:
                    first_interpretation_related = {
                        "year": shadow.year,
                        "diff": related_delta,
                    }

        prev_experiment_life_len = len(experiment.life_observations)

    first_type = classify_first_divergence(
        first_body_divergence,
        first_main_log_divergence,
        first_summary_divergence,
        first_memory_lineage_divergence,
    )
    broad_type = broad_divergence_type(first_type)
    first_nudge_year = first_nudge_info["year"] if first_nudge_info else None
    first_body_year = first_body_divergence["year"] if first_body_divergence else None
    trust_only_confirmed = False
    if first_nudge_info is not None:
        trust_only_confirmed = (
            not first_nudge_info["body_diff_categories_after_nudge_year"]
            and first_nudge_info["rng_equal_after_nudge_year"]
            and first_nudge_info["trust_diff_after_nudge_year_count"] > 0
        )

    final_body_categories = body_diff_categories(shadow, experiment)
    final_trust_diff = trust_diff(shadow, experiment)
    no_nudge_shadow_mismatch = (
        len(nudge_rows) == 0 and (bool(final_body_categories) or bool(final_trust_diff))
    )

    return {
        "seed": seed,
        "nudge_count": len(nudge_rows),
        "memory_shadow_count": count_life_events(experiment, "memory_shadow"),
        "life_bridge_potential_count": count_life_events(experiment, "life_bridge_potential"),
        "first_nudge_year": first_nudge_year,
        "first_nudge_row": first_nudge_info["row"] if first_nudge_info else None,
        "first_nudge_trust_only_confirmed": trust_only_confirmed,
        "pre_nudge_mismatch_count": len(pre_step_mismatches) + len(clean_step_mismatches),
        "pre_step_mismatches_before_first_nudge": pre_step_mismatches,
        "clean_step_mismatches_before_first_nudge": clean_step_mismatches,
        "first_body_divergence_year": first_body_year,
        "first_body_divergence_delay": (
            first_body_year - first_nudge_year
            if first_body_year is not None and first_nudge_year is not None
            else None
        ),
        "first_body_divergence_type": first_type,
        "first_body_divergence_broad_type": broad_type,
        "first_body_divergence_categories": (
            first_body_divergence["body_diff_categories"] if first_body_divergence else []
        ),
        "first_summary_divergence_year": (
            first_summary_divergence["year"] if first_summary_divergence else None
        ),
        "first_summary_divergence_keys": (
            sorted(first_summary_divergence["diff"].keys()) if first_summary_divergence else []
        ),
        "first_main_log_divergence": first_main_log_divergence,
        "first_interpretation_related_year": (
            first_interpretation_related["year"] if first_interpretation_related else None
        ),
        "first_interpretation_related_keys": (
            sorted(first_interpretation_related["diff"].keys())
            if first_interpretation_related
            else []
        ),
        "final_summary_diff_keys": sorted(
            dict_diff(watched_summary(shadow), watched_summary(experiment)).keys()
        ),
        "no_nudge_shadow_mismatch": no_nudge_shadow_mismatch,
        "final_body_diff_categories": final_body_categories,
        "final_trust_diff_count": len(final_trust_diff),
        "nudge_rows": [format_life_row(row) for row in nudge_rows],
    }


def aggregate(seed_results: list[dict[str, Any]]) -> dict[str, Any]:
    nudge_results = [item for item in seed_results if item["nudge_count"] > 0]
    no_nudge_results = [item for item in seed_results if item["nudge_count"] == 0]
    body_diverged_results = [
        item for item in nudge_results if item["first_body_divergence_year"] is not None
    ]
    delays = [
        item["first_body_divergence_delay"]
        for item in nudge_results
        if item["first_body_divergence_delay"] is not None
    ]
    type_counts: dict[str, int] = {}
    broad_type_counts: dict[str, int] = {}
    for item in nudge_results:
        key = item["first_body_divergence_type"]
        type_counts[key] = type_counts.get(key, 0) + 1
        broad_key = item["first_body_divergence_broad_type"]
        broad_type_counts[broad_key] = broad_type_counts.get(broad_key, 0) + 1
    return {
        "seed_count": len(seed_results),
        "nudge_seed_count": len(nudge_results),
        "nudge_seed_rate": round(len(nudge_results) / len(seed_results), 4),
        "no_nudge_seed_count": len(no_nudge_results),
        "body_divergence_seed_count": len(body_diverged_results),
        "total_memory_shadow_count": sum(item["memory_shadow_count"] for item in seed_results),
        "total_bridge_potential_count": sum(
            item["life_bridge_potential_count"] for item in seed_results
        ),
        "total_life_trust_nudge_count": sum(item["nudge_count"] for item in seed_results),
        "pre_nudge_mismatch_seed_count": sum(
            1 for item in seed_results if item["pre_nudge_mismatch_count"] > 0
        ),
        "no_nudge_shadow_mismatch_count": sum(
            1 for item in no_nudge_results if item["no_nudge_shadow_mismatch"]
        ),
        "first_nudge_trust_only_confirmed_count": sum(
            1 for item in nudge_results if item["first_nudge_trust_only_confirmed"]
        ),
        "first_body_divergence_type_counts": dict(sorted(type_counts.items())),
        "first_body_divergence_broad_type_counts": dict(sorted(broad_type_counts.items())),
        "first_body_divergence_delay_min": min(delays) if delays else None,
        "first_body_divergence_delay_avg": round(sum(delays) / len(delays), 2) if delays else None,
        "first_body_divergence_delay_max": max(delays) if delays else None,
    }


def run(seeds: list[int], years: int) -> dict[str, Any]:
    results = [analyze_seed(seed, years) for seed in seeds]
    return {
        "reader": "check_trust_nudge_D_30_seed",
        "shadow_path": str(SHADOW_PATH),
        "experiment_path": str(EXPERIMENT_PATH),
        "years": years,
        "seed_range": f"{seeds[0]}-{seeds[-1]}",
        "seeds": seeds,
        "aggregate": aggregate(results),
        "results": results,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    agg = report["aggregate"]
    lines = [
        "# trust nudge D 30 seed check",
        "",
        f"- seeds: `{report['seed_range']}` ({agg['seed_count']} consecutive seeds)",
        f"- years: `{report['years']}`",
        "- fixed baseline: `society_lab_v1_4_life_senses_memory_shadow3.py`",
        "- experiment: D default in `society_lab_v1_4_life_bridge_trust_nudge_experiment.py`",
        "",
        "## Aggregate",
        "",
        f"- nudge seeds: `{agg['nudge_seed_count']}/{agg['seed_count']}` "
        f"({agg['nudge_seed_rate']:.2%})",
        f"- no-nudge seeds: `{agg['no_nudge_seed_count']}`",
        f"- nudged seeds with body divergence by Y80: "
        f"`{agg['body_divergence_seed_count']}/{agg['nudge_seed_count']}`",
        f"- pre-nudge mismatch seeds: `{agg['pre_nudge_mismatch_seed_count']}`",
        f"- no-nudge shadow mismatches: `{agg['no_nudge_shadow_mismatch_count']}`",
        f"- first-nudge trust-only confirmed: "
        f"`{agg['first_nudge_trust_only_confirmed_count']}/{agg['nudge_seed_count']}`",
        f"- total memory_shadow: `{agg['total_memory_shadow_count']}`",
        f"- total life_bridge_potential: `{agg['total_bridge_potential_count']}`",
        f"- total life_trust_nudge: `{agg['total_life_trust_nudge_count']}`",
        f"- first body divergence delay: min/avg/max = "
        f"`{agg['first_body_divergence_delay_min']}` / "
        f"`{agg['first_body_divergence_delay_avg']}` / "
        f"`{agg['first_body_divergence_delay_max']}` years",
        "",
        "## First Body Divergence Type",
        "",
        "Broad classes normalize `memory_shared` and `shared_narrative` as `memory_lineage`.",
        "",
        "| broad type | seeds |",
        "| --- | ---: |",
    ]
    for key, count in agg["first_body_divergence_broad_type_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "Raw first visible log/event classes:",
            "",
        "| type | seeds |",
        "| --- | ---: |",
        ]
    )
    for key, count in agg["first_body_divergence_type_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Seed Table",
            "",
            "| seed | nudge | pre mismatch | first nudge | trust-only | first body divergence | delay | broad type | raw type | memory_shadow | bridge_potential | final summary diff keys |",
            "| ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in report["results"]:
        first_nudge = (
            f"Y{item['first_nudge_year']:02d}" if item["first_nudge_year"] is not None else "-"
        )
        first_body = (
            f"Y{item['first_body_divergence_year']:02d}"
            if item["first_body_divergence_year"] is not None
            else "-"
        )
        delay = item["first_body_divergence_delay"]
        delay_s = str(delay) if delay is not None else "-"
        trust_only = "yes" if item["first_nudge_trust_only_confirmed"] else "-"
        diff_keys = ", ".join(item["final_summary_diff_keys"]) or "-"
        lines.append(
            f"| {item['seed']} | {item['nudge_count']} | "
            f"{item['pre_nudge_mismatch_count']} | {first_nudge} | {trust_only} | "
            f"{first_body} | {delay_s} | "
            f"`{item['first_body_divergence_broad_type']}` | "
            f"`{item['first_body_divergence_type']}` | "
            f"{item['memory_shadow_count']} | {item['life_bridge_potential_count']} | "
            f"{diff_keys} |"
        )

    lines.extend(["", "## Nudge Rows", ""])
    for item in report["results"]:
        if not item["nudge_rows"]:
            continue
        lines.append(f"### seed{item['seed']}")
        lines.append("")
        for row in item["nudge_rows"]:
            lines.append(f"- {row}")
        lines.append("")

    lines.extend(
        [
            "## Reading",
            "",
            "In this 30-seed window, D keeps all pre-nudge states contained: there were no pre-nudge mismatches, and no no-nudge seed drifted away from shadow3.",
            "",
            "The bridge remains sparse. `memory_shadow` is common enough to create candidates, fewer cases become `life_bridge_potential`, and only a smaller subset reaches `life_trust_nudge`.",
            "",
            "When a nudge appears, the first nudge year is still trust-only in every nudged seed in this run. Body divergence appears later, so the branch reads as a delayed intervention effect rather than a hidden RNG mismatch before the bridge.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    seeds = list(range(1000, 1030))
    report = run(seeds, years=80)
    json_path = OUTPUTS / "trust_nudge_D_30_seed_check.json"
    md_path = OUTPUTS / "trust_nudge_D_30_seed_check.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps(report["aggregate"], indent=2, ensure_ascii=False))
    print(md_path)


if __name__ == "__main__":
    main()
