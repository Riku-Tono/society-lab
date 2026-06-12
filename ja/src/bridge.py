"""
bridge.py — MOAT × SocietyLab × RivalryCA 統合層
=================================================

設計思想:
  MOAT Stage 2d は「世界」ではなく「測定装置」である。
  2つの仮説条件 (H_B / H_Q) の下で生成されたトラジェクトリを受け取り、
  linear + RFF 分類器の AUC で「観測量から条件を識別できるか」を測る。

  SocietyLab と RivalryCA はどちらも観測可能メトリクスの時系列を吐く
  「世界」なので、WorldAdapter という共通インターフェースで包めば、
  MOAT の分類器スタックをそのまま3世界すべてに適用できる。

各世界の仮説ペア:
  moat     H_B: B方向ドリフトあり        / H_Q: Q方向共分散ノイズ
  society  H_B: 解釈ナッジON (scale=1)   / H_Q: 解釈ナッジOFF (scale=0)
  rivalry  H_B: 非対称LIKES (競争あり)   / H_Q: 対称LIKES (全員両想い)

重要な設計判断:
  RivalryCA では rivalry_rate / pair_rate を特徴量から除外する。
  これらは LIKES 構造の定義そのものなので入れると識別が自明になる。
  問うのは「圧力場の集計統計だけから隠れた関係構造が漏れるか」。

  SocietyLab では年次スナップショット (人口・恐怖・飢餓・声の重み・食料)
  とイベント件数の年次差分を特徴量にする。状態変数に宗教や権威を
  持たない v1.4 の設計ルールはそのまま守られる。

出力 (世界 × 時間窓ごと):
  - mean_auc      繰り返しランダム分割の平均 AUC
  - ci_low/high   2.5% / 97.5% パーセンタイル区間
  - per_clf       linear / rff の内訳
  - early → late の AUC 推移 (Stage 2e 的な「適応が識別性を潰すか」の曲線)
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

import numpy as np

import rivalry_ca
import society_lab
from moat_stage2d import Stage2dCfg, mean_auc, run_sra_ep, sample_geom, split_eval
from rivalry_ca import RivalryCA
from society_lab import SocietyLab

Array = np.ndarray


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class BridgeCfg:
    seed: int = 42
    n_ep: int = 60          # 条件ごとのエピソード数 (シードは seed+i でペア化)
    T: int = 60             # 時系列長 (society=年, rivalry=世代, moat=ステップ)
    n_boot: int = 25        # 繰り返しランダム分割の回数 (CI 用)
    clf: Stage2dCfg = field(default_factory=lambda: Stage2dCfg(train_steps=150, rff_dim=120))

    def windows(self) -> Dict[str, Tuple[int, int]]:
        third = max(1, self.T // 3)
        return {
            "early": (0, third),
            "mid": (third, 2 * third),
            "late": (2 * third, self.T),
            "full": (0, self.T),
        }


# ---------------------------------------------------------------------------
# World 1: MOAT (既存 SRA エピソードをそのまま包む)
# ---------------------------------------------------------------------------

class MoatWorld:
    name = "moat"
    feature_names = ("res_x", "res_y")
    featurize_raw = True  # 残差は低次元なので窓を flatten してそのまま使う

    def __init__(self, cfg: BridgeCfg):
        self.cfg = cfg

    def run_episode(self, seed: int, hyp: str) -> Array:
        rng = np.random.default_rng(seed)
        moat_cfg = Stage2dCfg(seed=seed, T=self.cfg.T)
        v_b, v_q = sample_geom(rng, moat_cfg)
        ep = run_sra_ep(rng, moat_cfg, "B" if hyp == "B" else "Q", v_b, v_q)
        return ep["res"]  # (T, 2)


# ---------------------------------------------------------------------------
# World 2: SocietyLab (解釈ナッジを条件としてスケール可能に)
# ---------------------------------------------------------------------------

class ConfigurableSocietyLab(SocietyLab):
    """v1.4 のハードコードされた 3% ナッジを実験条件として切替可能にする。

    本体ファイルは一切変更しない。ナッジ経路 2 本だけをオーバーライドする。
    """

    def __init__(self, seed: int | None, nudge_scale: float = 1.0):
        self.nudge_scale = nudge_scale
        super().__init__(seed=seed, verbose=False)

    def _interpretation_action_nudge(self, interpretation: str, action: str) -> float:
        return super()._interpretation_action_nudge(interpretation, action) * self.nudge_scale

    def _interpretation_support_nudge(self, person, problem, proposal, proposer) -> float:
        # 親クラス実装は action_nudge を内部で呼ぶため、二重スケールを避けて再実装。
        interpretation = self._recent_interpretation_for_problem(person, problem)
        if interpretation == "none":
            return 0.0
        if interpretation in {"spiritual", "practical"}:
            return self._interpretation_action_nudge(interpretation, proposal.action)
        if interpretation == "blame":
            base = -0.03 if proposer.voice_weight >= 0.08 else 0.03
            return base * self.nudge_scale
        return 0.0


SOCIETY_DELTA_EVENTS = (
    "crisis",
    "problem_detected",
    "project_success",
    "project_failure",
    "memory_shared",
    "behavior_copied",
)


class SocietyWorld:
    name = "society"
    feature_names = (
        "pop_ratio", "avg_fear", "avg_hunger", "avg_voice_weight", "food_ratio",
    ) + tuple(f"d_{e}" for e in SOCIETY_DELTA_EVENTS)
    featurize_raw = False  # 高次元なので窓ごとに mean+std へ集約

    def __init__(self, cfg: BridgeCfg):
        self.cfg = cfg

    def run_episode(self, seed: int, hyp: str) -> Array:
        scale = 1.0 if hyp == "B" else 0.0
        lab = ConfigurableSocietyLab(seed=seed, nudge_scale=scale)
        prev = {e: 0 for e in SOCIETY_DELTA_EVENTS}
        rows: List[List[float]] = []
        for _ in range(self.cfg.T):
            if lab.population > 0:
                lab.step()
            row = [
                lab.population / max(1, lab.initial_population),
                lab._avg("fear"),
                lab._avg("hunger"),
                lab._avg("voice_weight"),
                lab.food.stock / max(1e-6, lab.initial_food_stock),
            ]
            for e in SOCIETY_DELTA_EVENTS:
                c = lab.log.count(e)
                row.append(float(c - prev[e]))
                prev[e] = c
            rows.append(row)
        return np.array(rows)  # (T, 11)


# ---------------------------------------------------------------------------
# World 3: RivalryCA (LIKES 構造を仮説として差し替え)
# ---------------------------------------------------------------------------

ASYMMETRIC_LIKES = dict(rivalry_ca.LIKES)                       # 競争が発生する元の構造
SYMMETRIC_LIKES = {"A": "B", "B": "A", "C": "D", "D": "C"}      # 全ペア両想い・競争ゼロ

# 答えそのもの (rivalry_rate / pair_rate / kind_*) は除外した観測量のみ。
RIVALRY_FIELD_KEYS = ("pressure_entropy", "avg_pressure", "peace_rate", "collapse_risk")


@contextmanager
def patched_likes(mapping: Dict[str, str]):
    original = dict(rivalry_ca.LIKES)
    rivalry_ca.LIKES.clear()
    rivalry_ca.LIKES.update(mapping)
    try:
        yield
    finally:
        rivalry_ca.LIKES.clear()
        rivalry_ca.LIKES.update(original)


class RivalryWorld:
    name = "rivalry"
    feature_names = RIVALRY_FIELD_KEYS + ("pop_density",)
    featurize_raw = False

    def __init__(self, cfg: BridgeCfg):
        self.cfg = cfg

    def run_episode(self, seed: int, hyp: str) -> Array:
        mapping = ASYMMETRIC_LIKES if hyp == "B" else SYMMETRIC_LIKES
        rows: List[List[float]] = []
        with patched_likes(mapping):
            ca = RivalryCA(width=44, height=22, seed=seed)
            ca.randomize(density=0.32, base_pressure=0.08)
            area = ca.w * ca.h
            for _ in range(self.cfg.T):
                if ca.population() > 0:
                    ca.step()
                m = ca.metrics()
                rows.append(
                    [float(m[k]) for k in RIVALRY_FIELD_KEYS]
                    + [m["ca_population"] / area]
                )
        return np.array(rows)  # (T, 5)


# ---------------------------------------------------------------------------
# 特徴量化と bootstrap AUC
# ---------------------------------------------------------------------------

def featurize(eps: List[Array], t0: int, t1: int, raw: bool) -> Array:
    if raw:
        return np.array([ep[t0:t1].reshape(-1) for ep in eps])
    out = []
    for ep in eps:
        w = ep[t0:t1]
        out.append(np.r_[w.mean(axis=0), w.std(axis=0)])
    return np.array(out)


def bootstrap_auc(XB: Array, XQ: Array, rng: np.random.Generator,
                  clf_cfg: Stage2dCfg, n_boot: int) -> Dict[str, float]:
    """繰り返しランダム分割 (repeated random subsampling) による AUC 分布。

    エピソード順をシャッフルして train/test を引き直し、linear+RFF の
    平均 AUC を n_boot 回計算する。区間はパーセンタイル。
    """
    vals, lin_vals, rff_vals = [], [], []
    for _ in range(n_boot):
        xb = XB[rng.permutation(len(XB))]
        xq = XQ[rng.permutation(len(XQ))]
        d = split_eval(xb, xq, rng, clf_cfg)
        vals.append(mean_auc(d))
        lin_vals.append(d["linear"])
        rff_vals.append(d["rff"])
    vals = np.array(vals)
    return {
        "mean_auc": float(vals.mean()),
        "ci_low": float(np.percentile(vals, 2.5)),
        "ci_high": float(np.percentile(vals, 97.5)),
        "linear_mean": float(np.nanmean(lin_vals)),
        "rff_mean": float(np.nanmean(rff_vals)),
    }


# ---------------------------------------------------------------------------
# 評価ランナー
# ---------------------------------------------------------------------------

WORLDS: Dict[str, Callable[[BridgeCfg], object]] = {
    "moat": MoatWorld,
    "society": SocietyWorld,
    "rivalry": RivalryWorld,
}


def evaluate_world(world_name: str, cfg: BridgeCfg, verbose: bool = True) -> Dict:
    world = WORLDS[world_name](cfg)
    rng = np.random.default_rng(cfg.seed)

    eps_B, eps_Q = [], []
    for i in range(cfg.n_ep):
        s = cfg.seed + i
        eps_B.append(world.run_episode(s, "B"))
        eps_Q.append(world.run_episode(s, "Q"))
        if verbose and (i + 1) % max(1, cfg.n_ep // 4) == 0:
            print(f"  [{world.name}] episodes {i + 1}/{cfg.n_ep}")

    result: Dict[str, object] = {
        "world": world.name,
        "hypotheses": _hypothesis_labels(world.name),
        "n_ep_per_condition": cfg.n_ep,
        "T": cfg.T,
        "n_boot": cfg.n_boot,
        "features": list(world.feature_names),
        "windows": {},
    }
    for wname, (t0, t1) in cfg.windows().items():
        XB = featurize(eps_B, t0, t1, world.featurize_raw)
        XQ = featurize(eps_Q, t0, t1, world.featurize_raw)
        result["windows"][wname] = bootstrap_auc(XB, XQ, rng, cfg.clf, cfg.n_boot)

    wd = result["windows"]
    result["auc_drift_early_to_late"] = round(
        wd["late"]["mean_auc"] - wd["early"]["mean_auc"], 4
    )
    result["separable_full"] = bool(wd["full"]["ci_low"] > 0.55)
    return result


def _hypothesis_labels(world_name: str) -> Dict[str, str]:
    return {
        "moat": {"B": "B-direction drift", "Q": "Q-direction covariance noise"},
        "society": {"B": "interpretation nudge ON", "Q": "interpretation nudge OFF"},
        "rivalry": {"B": "asymmetric LIKES (rivalry)", "Q": "symmetric LIKES (all mutual)"},
    }[world_name]


def print_world_summary(r: Dict) -> None:
    hyp = r["hypotheses"]
    print(f"\n── {r['world']} ──  H_B: {hyp['B']}  vs  H_Q: {hyp['Q']}")
    print(f"   n_ep={r['n_ep_per_condition']}/condition  T={r['T']}  splits={r['n_boot']}")
    print(f"   {'window':<7} {'AUC':>6}  {'95% CI':>16}  {'linear':>7} {'rff':>7}")
    for wname in ("early", "mid", "late", "full"):
        w = r["windows"][wname]
        ci = f"[{w['ci_low']:.3f}, {w['ci_high']:.3f}]"
        print(f"   {wname:<7} {w['mean_auc']:>6.3f}  {ci:>16}  "
              f"{w['linear_mean']:>7.3f} {w['rff_mean']:>7.3f}")
    drift = r["auc_drift_early_to_late"]
    trend = "↑ 識別性が時間とともに増大" if drift > 0.03 else (
        "↓ 識別性が時間とともに減衰" if drift < -0.03 else "→ ほぼ一定")
    sep = "YES" if r["separable_full"] else "no"
    print(f"   early→late drift: {drift:+.3f}  ({trend})")
    print(f"   full-window separable (CI下限 > 0.55): {sep}")


def run_all(cfg: BridgeCfg, worlds: List[str]) -> Dict:
    results = {}
    for w in worlds:
        print(f"\nRunning world: {w}")
        results[w] = evaluate_world(w, cfg)
        print_world_summary(results[w])
    return results
