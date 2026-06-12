"""
stream_separation.py — RNG Stream Separation Experiment (Final Gate)
====================================================================

Question:
  Is the "nudge -> long-term divergence" observed in v1.4 a genuine
  amplification through social channels (support -> project -> food ->
  death), or an artifact of shared-PRNG consumption-order shifts
  (bookkeeping artifact)?

Design:
  StreamSeparatedSocietyLab
  - Separates RNG into per-subsystem streams:
      resource / problem / proposal / support / project /
      memory / action / mortality / birth / detect / misc
  - Each stream is reseeded every year via hash(seed, year, stream).
    -> Cross-year bookkeeping propagation and within-year cross-stream
       propagation are structurally eliminated.
    -> The only pathway for divergence to propagate across years is
       through model state (population, food, memory, trust, support,
       project outcomes).
  - Residual coupling: within-year, within-stream consumption shifts
    remain (noted as a limitation).
  - Initialization uses the parent class's single RNG (identical for
    both conditions, so not a concern).

Experiments:
  E1: Separated model, nudge ON vs OFF x 100 seeds.
      Compare against the coupled model's 38/100 divergence rate.
      Also record which observation channel diverged first.
  E2: Placebo (inject one meaningless draw into the support stream @Y30).
      In the coupled model, any single extra draw caused 100/100 divergence.
      How far does this drop in the separated model?  That delta quantifies
      the bookkeeping-artifact contribution.
  E3: Causal-ladder trace for key seeds (1003/1043/1036/1096).
      Line up the year each observation channel first diverged and check
      whether the support -> project -> food -> death ordering appears.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from contextlib import contextmanager

sys.path.insert(0, ".")
from bridge import ConfigurableSocietyLab

STREAMS = ("resource", "problem", "proposal", "support", "project",
           "memory", "action", "mortality", "birth", "detect", "misc")


def _hseed(master_seed: int, year: int, name: str) -> int:
    h = hashlib.md5(f"{master_seed}|{year}|{name}".encode()).hexdigest()
    return int(h[:16], 16)


class RngRouter:
    """random.Random-compatible facade. Delegates to the active stream."""

    def __init__(self):
        self.streams: dict[str, random.Random] = {}
        self.stack: list[str] = ["misc"]

    def reseed(self, master_seed: int, year: int) -> None:
        for name in STREAMS:
            self.streams[name] = random.Random(_hseed(master_seed, year, name))

    @contextmanager
    def use(self, name: str):
        self.stack.append(name)
        try:
            yield
        finally:
            self.stack.pop()

    def _cur(self) -> random.Random:
        return self.streams[self.stack[-1]]

    # Delegate the 7 methods used by society_lab.py
    def random(self):                    return self._cur().random()
    def uniform(self, a, b):             return self._cur().uniform(a, b)
    def randint(self, a, b):             return self._cur().randint(a, b)
    def choice(self, seq):               return self._cur().choice(seq)
    def choices(self, *a, **kw):         return self._cur().choices(*a, **kw)
    def sample(self, *a, **kw):          return self._cur().sample(*a, **kw)
    def betavariate(self, a, b):         return self._cur().betavariate(a, b)


class StreamSeparatedSocietyLab(ConfigurableSocietyLab):
    def __init__(self, seed: int, nudge_scale: float = 1.0):
        super().__init__(seed=seed, nudge_scale=nudge_scale)  # 初期化は単一乱数 (両条件同一)
        self._master_seed = seed
        self.router = RngRouter()
        self.rng = self.router  # 以後の全ドローはルーター経由

    def step(self) -> None:
        self.router.reseed(self._master_seed, self.year + 1)
        self._inject_hook()
        super().step()

    def _inject_hook(self) -> None:
        pass

    # ---- Per-phase stream assignment -----------------------------------
    def _resource_phase(self):
        with self.router.use("resource"):
            super()._resource_phase()

    def _problem_phase(self):
        with self.router.use("problem"):
            super()._problem_phase()

    def _make_proposals(self, problem):
        with self.router.use("proposal"):
            return super()._make_proposals(problem)

    def _support_proposals(self, problem, proposals):
        with self.router.use("support"):
            return super()._support_proposals(problem, proposals)

    def _execute_project(self, problem, proposal):
        with self.router.use("project"):
            return super()._execute_project(problem, proposal)

    def _dialogue_phase(self):
        with self.router.use("memory"):
            super()._dialogue_phase()

    def _action_phase(self):
        with self.router.use("action"):
            super()._action_phase()

    def _update_phase(self):
        with self.router.use("mortality"):
            super()._update_phase()

    def _generation_phase(self):
        with self.router.use("birth"):
            super()._generation_phase()

    def _detect_patterns(self):
        with self.router.use("detect"):
            super()._detect_patterns()


class PlaceboLab(StreamSeparatedSocietyLab):
    """Perturbation: draws one meaningless random value from a given stream at a given year."""

    def __init__(self, seed: int, inject_year: int, inject_stream: str):
        self._iy, self._is = inject_year, inject_stream
        super().__init__(seed=seed, nudge_scale=0.0)

    def _inject_hook(self) -> None:
        if self.year + 1 == self._iy:
            self.router.streams[self._is].random()


# ---------------------------------------------------------------------------
# Fingerprinting with observation channels
# ---------------------------------------------------------------------------

CHANNELS = ("supported", "started", "success", "failure",
            "food", "pop", "death", "birth", "memory_shared", "trust_changed")
EVENT_OF = {"supported": "proposal_supported", "started": "project_started",
            "success": "project_success", "failure": "project_failure",
            "death": "death", "birth": "birth",
            "memory_shared": "memory_shared", "trust_changed": "trust_changed"}


def run_channels(lab_factory, years: int = 80):
    lab = lab_factory()
    rows = []
    for _ in range(years):
        if lab.population > 0:
            lab.step()
        row = {"food": round(lab.food.stock, 6), "pop": lab.population}
        for ch, ev in EVENT_OF.items():
            row[ch] = lab.log.count(ev)
        rows.append(row)
    return rows, lab.summary()


def first_diff_by_channel(rows1, rows0):
    out = {}
    for ch in CHANNELS:
        y = next((i + 1 for i in range(len(rows1))
                  if rows1[i][ch] != rows0[i][ch]), None)
        out[ch] = y
    return out


def hard_diverged(fd: dict) -> bool:
    hard = [v for k, v in fd.items() if k != "supported" and v is not None]
    return len(hard) > 0


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

def e1_nudge_in_separated(seeds=range(1000, 1100)) -> dict:
    print("E1: Separated model, nudge ON vs OFF (100 seeds)")
    n_div, n_sup_only, n_ident = 0, 0, 0
    entry_channels, details = {}, []
    base_cache = {}
    for seed in seeds:
        r1, s1 = run_channels(lambda: StreamSeparatedSocietyLab(seed, 1.0))
        r0, s0 = run_channels(lambda: StreamSeparatedSocietyLab(seed, 0.0))
        base_cache[seed] = (r0, s0)
        fd = first_diff_by_channel(r1, r0)
        if hard_diverged(fd):
            n_div += 1
            firsts = {k: v for k, v in fd.items() if v is not None}
            ymin = min(firsts.values())
            entry = sorted(k for k, v in firsts.items() if v == ymin)
            entry_channels[",".join(entry)] = entry_channels.get(",".join(entry), 0) + 1
            details.append({"seed": seed, "first_diff": fd,
                            "pop_diff": s1["final_population"] - s0["final_population"]})
        elif fd["supported"] is not None:
            n_sup_only += 1
        else:
            n_ident += 1
    print(f"  diverged={n_div}  support_only={n_sup_only}  identical={n_ident}"
          f"   (coupled model: 38 / 6 / 56)")
    print(f"  entry channels: {entry_channels}")
    return {"diverged": n_div, "support_only": n_sup_only, "identical": n_ident,
            "entry_channels": entry_channels, "details": details,
            "_base_cache": base_cache}


def e2_placebo_in_separated(base_cache, inject_stream="support",
                            inject_year=30, seeds=range(1000, 1100)) -> dict:
    print(f"E2: Separated model placebo ({inject_stream} stream, 1 draw @Y{inject_year})")
    n_div, popdiffs = 0, []
    for seed in seeds:
        r0, s0 = base_cache[seed]
        rp, sp = run_channels(lambda: PlaceboLab(seed, inject_year, inject_stream))
        fd = first_diff_by_channel(rp, r0)
        if hard_diverged(fd):
            n_div += 1
            popdiffs.append(abs(sp["final_population"] - s0["final_population"]))
    mean_pd = sum(popdiffs) / len(popdiffs) if popdiffs else 0.0
    print(f"  diverged={n_div}/100  mean|pop_diff|={mean_pd:.1f}"
          f"   (coupled model same test: 100/100, mean 4-5)")
    return {"stream": inject_stream, "year": inject_year,
            "diverged": n_div, "mean_abs_pop_diff": mean_pd}


def e3_chain_trace(seeds=(1003, 1043, 1036, 1096)) -> list:
    print("E3: Causal-ladder trace for key seeds (separated model, nudge ON vs OFF)")
    out = []
    for seed in seeds:
        r1, s1 = run_channels(lambda: StreamSeparatedSocietyLab(seed, 1.0))
        r0, s0 = run_channels(lambda: StreamSeparatedSocietyLab(seed, 0.0))
        fd = first_diff_by_channel(r1, r0)
        ladder = sorted([(y, ch) for ch, y in fd.items() if y is not None])
        pop_diff = s1["final_population"] - s0["final_population"]
        status = "diverged" if hard_diverged(fd) else (
            "support_only" if fd["supported"] is not None else "identical")
        print(f"  seed{seed}: {status}  pop_diff={pop_diff:+d}")
        if ladder:
            print("    ladder: " + " → ".join(f"Y{y}:{ch}" for y, ch in ladder[:8]))
        out.append({"seed": seed, "status": status, "pop_diff": pop_diff,
                    "ladder": ladder})
    return out


if __name__ == "__main__":
    t0 = time.time()
    e1 = e1_nudge_in_separated()
    base_cache = e1.pop("_base_cache")
    e2a = e2_placebo_in_separated(base_cache, "support", 30)
    e2b = e2_placebo_in_separated(base_cache, "mortality", 30)
    e3 = e3_chain_trace()
    result = {"e1": e1, "e2_support": e2a, "e2_mortality": e2b, "e3": e3,
              "residual_coupling": "Within-year, within-stream consumption shifts remain",
              "note": "The separated model reseeds every year with (seed,year,stream), "
                      "so it is a different world from the v1.4 coupled model. "
                      "Comparison is limited to the ON-vs-OFF difference structure."}
    json.dump(result, open("stream_separation_results.json", "w"),
              indent=2, ensure_ascii=False)
    print(f"\n{time.time()-t0:.0f}s — wrote stream_separation_results.json")
