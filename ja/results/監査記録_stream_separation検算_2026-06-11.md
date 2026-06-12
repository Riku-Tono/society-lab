# 監査記録：RNG分離実験「ナッジ25/100 vs プラセボ7/100」の再現確認

- 実施日: 2026-06-11
- 実施者: Claude (Fable 5) / claude.ai サンドボックス環境
- 種別: 論文化前の検算（再現確認）。新実装・パラメータ変更・増幅器追加は一切なし。

## 1. 目的

論文エッセイ本線の柱である以下の数値が、同一コード・同一seed範囲で再現するかを確認する。

> RNGストリーム分離モデル（毎年 hash(seed, year, stream) 再シード方式）において、
> 解釈ナッジ ON vs OFF は 25/100 seed で分岐（hard diverged）、
> supportストリームへのプラセボ1ドロー（Y30）は 7/100 seed で分岐する。

## 2. 対象コードと成果物（すべて無編集）

| ファイル | SHA-256 | 備考 |
|---|---|---|
| society_lab_v1_4.py | 19ca44967bf3a4edc20b3f054deddf4c916c5cf9a946052069af229ea67efa41 | v1.4本体。48,814 bytes / 1,265行 |
| society_lab_v1_4_1.py | b7795f248f27a82eb699aae775f9f9d32d739b0d9e4079bdc275ef081c0897c8 | 観測強化版（本検算では未使用） |
| bridge.py | b2cb0da772e7c19e223df258a6b31a469c348d6ee29c3b5fa1a507d5a42aca5b | ConfigurableSocietyLab 定義 |
| stream_separation.py | 939c69d55d1a38655f9dd4b2662b22e98b81e8b06a1965d78f9cd24614f9a6bc | 実験本体（E1/E2/E3） |
| stream_separation_results.json（原本） | 4998b6d51393f58bb14ef03f4a3660b2212130e12171fa279593465d1ba5adee | 照合対象の原成果物 |

## 3. 実行環境

- Python 3.12.3（乱数は標準ライブラリ random / hashlib.md5 のみ）
- numpy 2.4.4（bridge.py のimport解決にのみ必要。検算経路の計算には未使用）
- OS: Ubuntu 24 (Linux サンドボックス)

## 4. 環境充当（開示事項）

bridge.py は `society_lab` / `rivalry_ca` / `moat_stage2d` をモジュールレベルでimportする。
検算対象の計算経路（ConfigurableSocietyLab → StreamSeparatedSocietyLab）が使用するのは
`society_lab.SocietyLab` のみであるため、以下の充当を行った。

1. `society_lab.py` := `society_lab_v1_4.py` のバイト同一コピー（SHA-256一致を確認。リネームのみ）
2. `rivalry_ca.py` / `moat_stage2d.py` := 不活性スタブ（呼び出された場合は即 RuntimeError を
   送出する実装とし、計算への混入を構造的に不可能にした）。実行中にスタブ起因の例外は発生せず。

充当(1)の妥当性は §5 の来歴照合により支持される。

## 5. 事前検証（v1.4本体の来歴照合）

凍結版 society_lab_v1_4.py を無編集で実行し、会話ログに記録された v1.4 既知数値と照合した。

| 項目（seed1003, 80年） | ログ記録値 | 再実行値 | 一致 |
|---|---|---|---|
| birth_count | 18 | 18 | ✓ |
| project_failure_count | 9 | 9 | ✓ |
| memory_shared_count | 323 | 323 | ✓ |

また seed1000 / 1003 / 1096 で同一seed2回走行のsummary完全一致（決定論性）を確認した。

## 6. 再現実行

- コマンド: `python3 stream_separation.py`（無編集）
- seed範囲: range(1000, 1100)、80年（コード記載のまま）
- 実行時間: 27秒

### 結果照合

| 項目 | ログ報告値 | 原本JSON | 今回再実行 | 一致 |
|---|---|---|---|---|
| E1 diverged | 25/100 | 25 | 25 | ✓ |
| E1 support_only / identical | 14 / 61 | 14 / 61 | 14 / 61 | ✓ |
| E1 diverged平均\|人口差\| / 最大 | 0.52 / 2 | 0.52 / 2 | 0.52 / 2 | ✓ |
| E2 supportプラセボ（Y30, 1ドロー） | 7/100 | 7 | 7 | ✓ |
| E2 mortalityプラセボ（Y30, 1ドロー） | （見出し記載なし） | 36 | 36 | ✓ |
| E3 seed1036 | identical | identical | identical | ✓ |
| E3 seed1096 因果階段 | Y46→Y52→Y55 | 同 | Y46:failure/started → Y52:food → Y55:death/pop | ✓ |

### バイト一致

再実行が出力した stream_separation_results.json の SHA-256 は
`4998b6d51393f58bb14ef03f4a3660b2212130e12171fa279593465d1ba5adee` であり、
**原本と完全同一**。数値一致を超えたバイト単位の再現である。乱数を消費順に依存しない
hash(seed, year, stream) 方式で引く設計のため、環境差があっても同一出力となる——
設計主張どおりの挙動が実証された。

## 7. 判定

**「ナッジ25/100 vs プラセボ7/100」は再現確認済み。論文本線の柱として採用可。**

## 8. 採用時に併記すべき限界（監査からの持ち越し）

1. **ストリーム依存のプラセボ感度**: mortalityストリームへの同一プラセボは36/100分岐する。
   supportプラセボ(7/100)が対照として妥当なのは、ナッジの侵入点がsupportであるため。
   「同年・同ストリーム内の消費ずれは残存」というコード明記の限界とともに限界節へ記載のこと。
2. **別世界比較の限定**: 分離モデルは毎年再シードのため v1.4 結合モデルとは別世界。
   結合モデルの38/100との比較は「ON vs OFF の差分構造の比較」に限る（原本JSON note記載どおり）。
3. **効果量**: diverged seedの最終人口差は平均0.52人・最大2人。主張は「経路残渣の実在」で
   あり、「効果の大きさ」ではない。
4. **出典の重複**: 当該報告テキストはログ7とログ10に一字一句同一で重複収録されている。
   引用時は単一報告（1報）として扱うこと。

## 9. 監査チェーンの現状

1. v1.4本体の来歴確定（seed1003既知値3項目の独立一致） — 済
2. 成果物JSONとログ報告値の静的一致 — 済
3. 同一コード・同一seed範囲での実行再現（バイト一致） — 済（本記録）

未了: 第三者（Codex / Grok / ChatGPT 等の別環境）による同手順の相互検収。
本記録と下記ファイル一式を渡せば実施可能。

## 10. 同梱ファイル

- stream_separation_results_rerun_2026-06-11.json（今回の再実行出力。原本とバイト同一）
