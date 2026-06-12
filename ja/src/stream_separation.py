"""
stream_separation.py — RNGストリーム分離実験 (最後の関門)
==========================================================

問い:
  v1.4 の「ナッジ → 長期分岐」は、社会的チャネル (支持→プロジェクト→
  食料→死亡) を通った本物の増幅か、それとも共有PRNGストリームの
  消費ずれ (簿記) によるアーティファクトか。

設計:
  StreamSeparatedSocietyLab
  - 乱数をサブシステム別ストリームに分離:
      resource / problem / proposal / support / project /
      memory / action / mortality / birth / detect / misc
  - 各ストリームは毎年 hash(seed, year, stream) で再シード。
    → 年をまたぐ簿記伝播と、年内のストリーム間伝播が構造的に消える。
    → 分岐が翌年以降に伝わる経路は「モデル状態」(人口・食料・記憶・
      信頼・支持・プロジェクト) のみになる。
  - 残留する結合: 同年・同ストリーム内の消費ずれのみ (限界として明記)。
  - 初期化は親クラスの単一乱数で行う (両条件で同一なので問題なし)。

実験:
  E1: 分離モデルで nudge ON vs OFF ×100seed。
      結合モデルの 38/100 と比較。最初に割れた観測チャネルも記録。
  E2: プラセボ (supportストリームに無意味な1ドロー注入 @Y30)。
      結合モデルでは任意の1ドローで 100/100 分岐した。
      分離モデルでどこまで下がるかが「簿記アーティファクトの寄与」の定量。
  E3: 主要seed (1003/1043/1036/1096) の因果階段トレース。
      各観測チャネルが最初に割れた年を並べ、
      support → project → food → death の順序が出るかを見る。
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
    """random.Random 互換の窓口。アクティブなストリームへ委譲する。"""

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

    # society_lab.py が使う7メソッドを委譲
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

    # ---- フェーズごとのストリーム割り当て -------------------------------
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
    """指定年に指定ストリームから無意味な1ドローを引くだけの摂動。"""

    def __init__(self, seed: int, inject_year: int, inject_stream: str):
        self._iy, self._is = inject_year, inject_stream
        super().__init__(seed=seed, nudge_scale=0.0)

    def _inject_hook(self) -> None:
        if self.year + 1 == self._iy:
            self.router.streams[self._is].random()


# ---------------------------------------------------------------------------
# 観測チャネル付きフィンガープリント
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
# 実験
# ---------------------------------------------------------------------------

def e1_nudge_in_separated(seeds=range(1000, 1100)) -> dict:
    print("E1: 分離モデルで nudge ON vs OFF (100 seeds)")
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
          f"   (結合モデル: 38 / 6 / 56)")
    print(f"  分岐の入口チャネル: {entry_channels}")
    return {"diverged": n_div, "support_only": n_sup_only, "identical": n_ident,
            "entry_channels": entry_channels, "details": details,
            "_base_cache": base_cache}


def e2_placebo_in_separated(base_cache, inject_stream="support",
                            inject_year=30, seeds=range(1000, 1100)) -> dict:
    print(f"E2: 分離モデルでプラセボ ({inject_stream}ストリームに1ドロー @Y{inject_year})")
    n_div, popdiffs = 0, []
    for seed in seeds:
        r0, s0 = base_cache[seed]
        rp, sp = run_channels(lambda: PlaceboLab(seed, inject_year, inject_stream))
        fd = first_diff_by_channel(rp, r0)
        if hard_diverged(fd):
            n_div += 1
            popdiffs.append(abs(sp["final_population"] - s0["final_population"]))
    mean_pd = sum(popdiffs) / len(popdiffs) if popdiffs else 0.0
    print(f"  diverged={n_div}/100  平均|人口差|={mean_pd:.1f}"
          f"   (結合モデルの同実験: 100/100, 平均4-5人)")
    return {"stream": inject_stream, "year": inject_year,
            "diverged": n_div, "mean_abs_pop_diff": mean_pd}


def e3_chain_trace(seeds=(1003, 1043, 1036, 1096)) -> list:
    print("E3: 主要seedの因果階段トレース (分離モデル, nudge ON vs OFF)")
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
            print("    階段: " + " → ".join(f"Y{y}:{ch}" for y, ch in ladder[:8]))
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
              "residual_coupling": "同年・同ストリーム内の消費ずれは残存",
              "note": "分離モデルは毎年(seed,year,stream)再シードのため "
                      "v1.4結合モデルとは別世界。比較は ON vs OFF の差分構造のみ。"}
    json.dump(result, open("stream_separation_results.json", "w"),
              indent=2, ensure_ascii=False)
    print(f"\n{time.time()-t0:.0f}s — wrote stream_separation_results.json")
