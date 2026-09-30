#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超预测 · Brier 评分与校准分析

读取 _ledger.json，输出：
  1. 逐条分数表（BS 初始 / BS 最终 / ΔBS / BSS）
  2. 汇总（平均 BS、平均 BSS、平均 ΔBS、条数）
  3. Murphy 分解（可靠性 − 区分度 + 不确定性）
  4. 校准曲线（默认 10 桶；已结算样本 < 40 自动降为 5 桶）
  5. 区分度指标（概率标准差 / 极差 / 50% 使用率）
  6. 四象限定位与样本量提醒

用法：
  python brier.py --ledger ~/.workbuddy/forecast-archive/_ledger.json
  python brier.py --ledger ... --append ~/.workbuddy/forecast-archive/_calibration.md

约定：
  - 正式分用【最终概率】（final_probability，缺省取 probability_history 末项）
  - 初始分用【直觉估计】（initial_intuition）
  - 更新增益 ΔBS = BS_初始 − BS_最终；为负说明更新在帮倒忙（过度反应）
  - 标记 "judgment_disputed": true 的条目【不进】校准曲线与 Murphy 分解，仍单独计分
  - BSS 需要 "baseline_probability"（上位参考类基线概率）；缺失则该条不参与 BSS
"""

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime

MIN_SAMPLE_FOR_CONCLUSION = 20
BINS_FULL = 10
BINS_REDUCED = 5
REDUCE_BELOW = 40
CONSTANT_BASELINE = 0.5  # 恒定 50% 基准，其 Brier 恒为 0.25


# ---------------------------------------------------------------- 数据读取

def load_ledger(path):
    if not os.path.exists(path):
        sys.exit("[错误] 找不到总账文件：%s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "forecasts" not in data or not isinstance(data["forecasts"], list):
        sys.exit("[错误] 总账格式异常：缺少 forecasts 数组")
    return data


def final_probability(item):
    if isinstance(item.get("final_probability"), (int, float)):
        return float(item["final_probability"])
    hist = item.get("probability_history") or []
    if hist and isinstance(hist[-1].get("p"), (int, float)):
        return float(hist[-1]["p"])
    return None


def collect(ledger):
    """返回 (已结算条目, 跳过统计)"""
    resolved, skipped = [], {"未结算": 0, "缺概率": 0}
    for item in ledger["forecasts"]:
        outcome = item.get("resolved")
        if outcome not in (0, 1):
            skipped["未结算"] += 1
            continue
        p_final = final_probability(item)
        if p_final is None:
            skipped["缺概率"] += 1
            continue
        p_init = item.get("initial_intuition")
        p_init = float(p_init) if isinstance(p_init, (int, float)) else None
        base = item.get("baseline_probability")
        base = float(base) if isinstance(base, (int, float)) else None
        resolved.append({
            "id": item.get("id", "?"),
            "title": item.get("title", ""),
            "p_init": p_init,
            "p_final": p_final,
            "o": int(outcome),
            "p_base": base,
            "disputed": bool(item.get("judgment_disputed", False)),
        })
    return resolved, skipped


# ---------------------------------------------------------------- 计算

def brier(p, o):
    return (p - o) ** 2


def per_item_rows(items):
    rows = []
    for it in items:
        bs_final = brier(it["p_final"], it["o"])
        bs_init = brier(it["p_init"], it["o"]) if it["p_init"] is not None else None
        delta = (bs_init - bs_final) if bs_init is not None else None
        bss = None
        if it["p_base"] is not None:
            bs_base = brier(it["p_base"], it["o"])
            bss = (1 - bs_final / bs_base) if bs_base > 0 else None
        rows.append({**it, "bs_init": bs_init, "bs_final": bs_final,
                     "delta": delta, "bss": bss})
    return rows


def murphy(items, bins):
    """BS ≈ 可靠性 − 区分度 + 不确定性

    注意：该分解式对【分桶后】的 Brier 严格成立——即用桶内预测均值 p_k
    代替桶内每条各自的概率来计分（binned_bs）。逐条原始概率的 Brier
    与分桶 Brier 会有小幅差异（桶内方差被抹平），属正常现象。
    """
    n = len(items)
    if n == 0:
        return None
    o_bar = sum(i["o"] for i in items) / n

    # 分桶
    buckets = {}
    for idx, it in enumerate(items):
        buckets.setdefault(bin_index(it["p_final"], bins), []).append(idx)

    reliability = resolution = 0.0
    binned_bs = 0.0
    for k, idxs in buckets.items():
        nk = len(idxs)
        p_bar = sum(items[i]["p_final"] for i in idxs) / nk
        o_k = sum(items[i]["o"] for i in idxs) / nk
        reliability += nk * (p_bar - o_k) ** 2 / n
        resolution += nk * (o_k - o_bar) ** 2 / n
        for i in idxs:
            binned_bs += (p_bar - items[i]["o"]) ** 2 / n

    uncertainty = o_bar * (1 - o_bar)
    return {"n": n, "o_bar": o_bar, "reliability": reliability,
            "resolution": resolution, "uncertainty": uncertainty,
            "binned_bs": binned_bs,
            "reconstructed": reliability - resolution + uncertainty}


def bin_index(p, bins):
    """统一分桶：桶 k 覆盖 [k/bins, (k+1)/bins)，最后一个桶含 1.0。"""
    return min(int(p * bins), bins - 1)


def calibration_table(items, bins):
    rows = []
    for k in range(bins):
        bucket = [i for i in items if bin_index(i["p_final"], bins) == k]
        lo, hi = k * 100 // bins, (k + 1) * 100 // bins
        name = f"{lo}–{hi}%"
        if not bucket:
            rows.append((name, 0, None, None, None))
            continue
        p_bar = sum(i["p_final"] for i in bucket) / len(bucket)
        o_k = sum(i["o"] for i in bucket) / len(bucket)
        rows.append((name, len(bucket), p_bar, o_k, o_k - p_bar))
    return rows


def resolution_metrics(items):
    ps = [i["p_final"] for i in items]
    if not ps:
        return None
    exact_50 = sum(1 for p in ps if abs(p - 0.5) < 1e-9)
    return {"stdev": statistics.pstdev(ps) if len(ps) > 1 else 0.0,
            "range": max(ps) - min(ps),
            "use_50": exact_50 / len(ps)}


# ---------------------------------------------------------------- 报告

def fmt_pct(x, digits=1):
    return "—" if x is None else f"{x*100:.{digits}f}%"


def fmt_num(x, digits=4):
    return "—" if x is None else f"{x:.{digits}f}"


def build_report(items, skipped, bins):
    rows = per_item_rows(items)
    valid = [r for r in rows if not r["disputed"]]
    out = []
    out.append("## 超预测校准报告")
    out.append("")
    out.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"已结算条数：**{len(rows)}**（其中参与校准 {len(valid)}，判定存疑 {len(rows)-len(valid)}）")
    if any(skipped.values()):
        out.append("跳过：" + "；".join(f"{k} {v} 条" for k, v in skipped.items() if v))
    out.append("")

    if len(valid) < MIN_SAMPLE_FOR_CONCLUSION:
        out.append(f"> ⚠️ **样本量提醒**：参与校准的已结算预测仅 {len(valid)} 条，**低于 {MIN_SAMPLE_FOR_CONCLUSION} 条**。")
        out.append("> 按红线规定，此时**不得对校准水平下任何结论**——Brier 分数的检验对象是一揽子预测的长期表现，单条分近乎噪声。以下数据仅供台账留痕。")
        out.append("")

    # 1 逐条
    out.append("### 1. 逐条分数")
    out.append("")
    out.append("| 编号 | 标题 | 初始概率 | 最终概率 | 结果 | BS 初始 | BS 最终 | ΔBS | BSS |")
    out.append("|---|---|---:|---:|:--:|---:|---:|---:|---:|")
    for r in rows:
        flag = " ⚠️存疑" if r["disputed"] else ""
        out.append("| {id}{f} | {t} | {pi} | {pf} | {o} | {bi} | {bf} | {d} | {bss} |".format(
            id=r["id"], f=flag, t=r["title"], pi=fmt_pct(r["p_init"]),
            pf=fmt_pct(r["p_final"]), o=r["o"], bi=fmt_num(r["bs_init"]),
            bf=fmt_num(r["bs_final"]), d=fmt_num(r["delta"]), bss=fmt_num(r["bss"], 3)))
    out.append("")

    if not valid:
        out.append("_没有可参与校准的条目_")
        return "\n".join(out), None

    bs_mean = sum(r["bs_final"] for r in valid) / len(valid)
    deltas = [r["delta"] for r in valid if r["delta"] is not None]
    bsss = [r["bss"] for r in valid if r["bss"] is not None]

    # 2 汇总
    out.append("### 2. 汇总")
    out.append("")
    out.append("| 指标 | 值 | 读法 |")
    out.append("|---|---:|---|")
    out.append(f"| 平均 Brier（正式分） | {bs_mean:.4f} | 越小越好；恒定 50% 基准为 0.25 |")
    out.append(f"| 与抛硬币比较 | {'优于' if bs_mean < 0.25 else '差于' if bs_mean > 0.25 else '持平'} 0.25 | "
               f"{'合格' if bs_mean < 0.25 else '⚠️ 比一直说 50% 还差'} |")
    if deltas:
        d_mean = sum(deltas) / len(deltas)
        verdict = "更新提升了准确度" if d_mean > 0 else ("⚠️ 更新在帮倒忙（疑似过度反应）" if d_mean < 0 else "更新无净效果")
        out.append(f"| 平均更新增益 ΔBS | {d_mean:+.4f} | {verdict}；负值必须单独排查 |")
    if bsss:
        bss_mean = sum(bsss) / len(bsss)
        verdict = "强于直接照抄参考类基线" if bss_mean > 0 else "⚠️ 不如直接照抄参考类基线"
        out.append(f"| 平均 BSS（对参考类基线） | {bss_mean:+.3f} | {verdict}；>0 为优 |")
    else:
        out.append("| 平均 BSS | — | 总账中缺少 baseline_probability，无法计算 |")
    out.append("")

    # 3 Murphy
    m = murphy(valid, bins)
    out.append("### 3. Murphy 分解（校准度与区分度分开看）")
    out.append("")
    out.append("```")
    out.append("Brier = 可靠性(校准度) − 区分度 + 不确定性")
    out.append("```")
    out.append("")
    out.append("| 项 | 公式 | 数值 | 方向 |")
    out.append("|---|---|---:|---|")
    out.append(f"| 可靠性（校准度） | Σ n_k(p_k − ō_k)² / N | {m['reliability']:.4f} | **越小越好**（越接近 0 越准）|")
    out.append(f"| 区分度（Resolution） | Σ n_k(ō_k − ō)² / N | {m['resolution']:.4f} | **越大越好**（越敢分级越有用）|")
    out.append(f"| 不确定性（Uncertainty） | ō(1 − ō)，ō = {m['o_bar']:.3f} | {m['uncertainty']:.4f} | 与预测无关（事件本身难度）|")
    out.append(f"| **重构校验** | 可靠性 − 区分度 + 不确定性 | **{m['reconstructed']:.4f}** | 应等于分桶 Brier {m['binned_bs']:.4f} |")
    out.append("")
    out.append(f"分母桶数：**{bins}**（已结算 {len(rows)} 条{'，低于 40 已自动降桶' if bins == BINS_REDUCED else ''}）")
    out.append("")
    out.append(f"说明：分解式对**分桶后**的 Brier 严格成立（分桶 Brier {m['binned_bs']:.4f}）；"
               f"逐条原始概率的平均 Brier 为 {bs_mean:.4f}，两者的小幅差异来自桶内方差被抹平，属正常现象。")
    out.append("")
    out.append("> 两个预测者可以有**完全相同的 Brier 分数**，但一个「校准不准但敢下注」，另一个「校准挺准但永远说 50%」。")
    out.append("> 分数一样，病根不同，药方也不同——所以必须分开看。")
    out.append("")

    # 4 校准曲线
    table = calibration_table(valid, bins)
    out.append("### 4. 校准曲线")
    out.append("")
    out.append("| 概率桶 | 条数 | 预测均值 | 实际发生率 | 偏差 |")
    out.append("|---|---:|---:|---:|---:|")
    for name, cnt, p_bar, o_k, bias in table:
        out.append(f"| {name} | {cnt} | {fmt_pct(p_bar)} | {fmt_pct(o_k)} | {('+' if (bias or 0) >= 0 else '') + fmt_pct(bias) if bias is not None else '—'} |")
    out.append("")
    out.append("这张表的意思：说 70% 的那批事，实际发生了多少？靠得越近越准；说 70% 只发生 50% 是过度自信，反过来是过度保守。")
    out.append("")

    # 5 区分度
    rm = resolution_metrics(valid)
    out.append("### 5. 区分度指标")
    out.append("")
    out.append("| 指标 | 值 | 警戒 |")
    out.append("|---|---:|---|")
    out.append(f"| 概率标准差 | {rm['stdev']:.3f} | 越小越「和稀泥」 |")
    out.append(f"| 极差 | {rm['range']*100:.1f} 点 | 长期 < 40 点 = 不敢区分 |")
    out.append(f"| 50% 使用率 | {rm['use_50']*100:.1f}% | 偏高 = 三档思维未破除 |")
    out.append("")

    # 6 四象限
    calib_ok = m["reliability"] <= 0.05
    resol_ok = rm["range"] >= 0.4 and rm["use_50"] <= 0.2
    quadrant = {
        (True, True): "🎯 目标状态：校准好 + 区分好",
        (True, False): "⚠️ 和稀泥选手：校准好但不敢区分——分数不难看，但没有决策价值",
        (False, True): "⚠️ 敢下注但方向偏：优先怀疑参考类选错（回 Step 3）",
        (False, False): "❌ 双重失败：先修校准（回 Step 3/4），再练区分",
    }[(calib_ok, resol_ok)]
    out.append("### 6. 四象限定位")
    out.append("")
    out.append(f"- 校准判定：可靠性 {m['reliability']:.4f}（阈值 0.05）→ {'好' if calib_ok else '差'}")
    out.append(f"- 区分判定：极差 {rm['range']*100:.1f} 点、50% 使用率 {rm['use_50']*100:.1f}% → {'好' if resol_ok else '差'}")
    out.append(f"- **定位：{quadrant}**")
    out.append("")
    out.append("下一步：按归因表把失败定位到具体步骤（直觉 / 分解 / 参考类 / 差异点 / 更新），"
               "并单独统计「归因到运气」的次数——运气占比长期偏高，说明方法本身有问题。")
    out.append("")

    return "\n".join(out), bs_mean


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="超预测 Brier 评分与校准分析")
    ap.add_argument("--ledger", required=True, help="_ledger.json 路径")
    ap.add_argument("--append", help="把报告追加写入该文件（如 _calibration.md）")
    ap.add_argument("--bins", type=int, choices=[5, 10], help="覆盖自动桶数")
    args = ap.parse_args()

    ledger = load_ledger(args.ledger)
    items, skipped = collect(ledger)

    if not items:
        print("没有已结算的预测，暂无可分析数据。")
        if skipped:
            print("跳过：" + "；".join(f"{k} {v} 条" for k, v in skipped.items() if v))
        return

    if args.bins:
        bins = args.bins
    else:
        bins = BINS_REDUCED if len(items) < REDUCE_BELOW else BINS_FULL

    report, _ = build_report(items, skipped, bins)
    print(report)

    if args.append:
        with open(args.append, "a", encoding="utf-8") as fh:
            fh.write("\n\n---\n\n" + report + "\n")
        print(f"\n[已追加到] {args.append}")


if __name__ == "__main__":
    main()
