from __future__ import annotations

import os
from pathlib import Path


def find_sl3() -> Path:
    home = Path.home()
    for root, _dirs, files in os.walk(home / "OneDrive"):
        if "society_lab_v1_4_life_bridge_trust_nudge_experiment.py" in files:
            return Path(root)
    raise FileNotFoundError("SL3 folder not found")


sl3 = find_sl3()
path = sl3 / "society_lab_v1_4_life_bridge_trust_nudge_experiment.py"
text = path.read_text(encoding="utf-8")

text = text.replace(
    '''    life_trust_nudge_threshold = 10.0
    life_trust_nudge_delta = 0.001
    life_trust_nudge_cooldown = 8
    life_trust_nudge_max_per_year = 2
''',
    '''    # D proposal: a narrow, controlled body-intervention experiment.
    # Only memory_shadow-sourced bridge potential can touch trust.
    life_trust_nudge_threshold = 10.0
    life_trust_nudge_delta = 0.0005
    life_trust_nudge_cooldown = 16
    life_trust_nudge_max_per_year = 1
    life_trust_nudge_max_per_pair_total: int | None = 1
    life_trust_nudge_allowed_sources: set[str] | None = {"memory_shadow"}
''',
)

text = text.replace(
    '''        if potential < self.life_trust_nudge_threshold:
            return
        if self.life_trust_nudges_by_year.get(self.year, 0) >= self.life_trust_nudge_max_per_year:
            return
        last_year = self.life_trust_nudge_last_year.get(pair)
''',
    '''        if potential < self.life_trust_nudge_threshold:
            return
        allowed_sources = self.life_trust_nudge_allowed_sources
        if allowed_sources is not None and source not in allowed_sources:
            return
        max_pair_total = self.life_trust_nudge_max_per_pair_total
        if max_pair_total is not None and self.life_trust_nudge_counts.get(pair, 0) >= max_pair_total:
            return
        if self.life_trust_nudges_by_year.get(self.year, 0) >= self.life_trust_nudge_max_per_year:
            return
        last_year = self.life_trust_nudge_last_year.get(pair)
''',
)

text = text.replace(
    '''                f"threshold={self.life_trust_nudge_threshold:.1f}; "
                f"cooldown={self.life_trust_nudge_cooldown}; source={source}; "
                f"place={place}; weather={weather}; "
''',
    '''                f"threshold={self.life_trust_nudge_threshold:.1f}; "
                f"cooldown={self.life_trust_nudge_cooldown}; "
                f"max_per_year={self.life_trust_nudge_max_per_year}; "
                f"max_per_pair_total={self.life_trust_nudge_max_per_pair_total}; "
                f"source={source}; place={place}; weather={weather}; "
''',
)

path.write_text(text, encoding="utf-8", newline="\n")
print(path)
