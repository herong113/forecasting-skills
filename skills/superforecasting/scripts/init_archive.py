#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化 / 修复超预测档案骨架（init_archive）

用途
----
创建 ~/.workbuddy/forecast-archive/ 的完整骨架：
  01-重大决策/  02-长期项目/  03-判断力训练/
  _ledger.json  _index.md  _calibration.md

为什么用脚本而不是编辑工具
--------------------------
实测：在 forecast-archive/ 下**由编辑工具创建的文件会变成只读**（工具与 Python 均报
PermissionError / os error 87），导致后续无法更新；而**由 Python 创建的文件正常可写**。
因此本目录下的文件统一由 Python 创建。详见 archive_io.py。

用法
----
  python init_archive.py                # 幂等：缺什么补什么，已存在的不动
  python init_archive.py --force        # 强制重建（先删除再写，会覆盖既有内容）

注意
----
--force 会覆盖 _ledger.json 等文件。**仅在文件损坏或需要修复时使用**；
正常更新请用 archive_io.py（它做回读校验）。
"""

import argparse
import json
import os
import sys

ARCHIVE = os.path.join(os.path.expanduser("~"), ".workbuddy", "forecast-archive")
SUBDIRS = ["01-重大决策", "02-长期项目", "03-判断力训练"]

LEDGER_NOTE = ("超预测机读总账（数值索引）。权威归属：.md 档案是内容权威，"
               "本文件是数值索引；两者冲突时以 .md 为准并回填本文件。"
               "字段说明见 ~/.workbuddy/skills/superforecasting/assets/ledger-模板.json。")

INDEX_MD = """# 预测档案索引

> 本文件是人读索引，只追加不覆盖。机读数值索引见 `_ledger.json`。
> 权威归属：单条 `.md` 档案是内容权威，`_ledger.json` 是数值索引；两者冲突时以 `.md` 为准并回填 json。

图例：场景 ① 重大决策 ｜ ② 长期项目 ｜ ③ 判断力训练

---

## 进行中

| 编号 | 标题 | 场景 | 当前概率 | 敏感区间 | 判定日 | 下次复核 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 待结算

| 编号 | 标题 | 场景 | 最终概率 | 判定日 |
|---|---|---|---|---|
|  |  |  |  |  |

## 已结算

| 编号 | 标题 | 场景 | 结果 | Brier（初始） | Brier（最终） | ΔBS | BSS | 归因步骤 |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

---

## 汇总（由 `scripts/brier.py` 生成，勿手改）

- 已结算条数：
- 平均 Brier（正式分）：
- 平均 ΔBS（更新增益）：
- 平均 BSS：
- 最近一次校准报告：见 `_calibration.md`
"""

CALIBRATION_MD = """# 校准台账

> 由 `python ~/.workbuddy/skills/superforecasting/scripts/brier.py --ledger ~/.workbuddy/forecast-archive/_ledger.json --append ~/.workbuddy/forecast-archive/_calibration.md` 追加写入。**只追加，禁止修改历史报告。**

## 使用约定

- **样本 < 20 条时不得下校准结论**——Brier 分数的检验对象是一揽子预测的长期表现，单条分近乎噪声
- **每满 20 条**已结算预测产出一次完整校准报告
- 判定存疑（`judgment_disputed: true`）的条目不计入校准曲线，仍单独计分
- 报告须**分开**呈现校准度（可靠性）与区分度（分辨率）——分数相同病根不同，药方也不同
- ΔBS < 0 是"过度反应"信号，必须单独排查，不得混在平均分里糊过去

---

_（尚无校准报告，等第一条预测结算后生成）_
"""


def write_text(path, content, force):
    if os.path.exists(path) and not force:
        print("  跳过（已存在）：%s" % os.path.basename(path))
        return False
    if os.path.exists(path) and force:
        os.remove(path)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("  写入：%s（%d 字节）" % (os.path.basename(path),
                                    os.path.getsize(path)))
    return True


def main():
    ap = argparse.ArgumentParser(description="初始化 / 修复超预测档案骨架")
    ap.add_argument("--force", action="store_true",
                    help="强制重建（会覆盖 _ledger.json 等文件）")
    args = ap.parse_args()

    print("档案目录：%s" % ARCHIVE)
    os.makedirs(ARCHIVE, exist_ok=True)
    for name in SUBDIRS:
        d = os.path.join(ARCHIVE, name)
        os.makedirs(d, exist_ok=True)
        print("  目录就绪：%s/" % name)

    ledger_path = os.path.join(ARCHIVE, "_ledger.json")
    if os.path.exists(ledger_path) and not args.force:
        try:
            with open(ledger_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            print("  跳过（已存在，%d 条记录）：_ledger.json"
                  % len(data.get("forecasts", [])))
        except Exception as exc:
            print("  [警告] _ledger.json 无法解析：%s" % exc)
            print("         建议用 --force 重建（会清空记录！先备份）")
    else:
        if os.path.exists(ledger_path):
            os.remove(ledger_path)
        with open(ledger_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"_说明": LEDGER_NOTE, "version": 1, "forecasts": []},
                      fh, ensure_ascii=False, indent=2)
        print("  写入：_ledger.json（%d 字节）" % os.path.getsize(ledger_path))

    write_text(os.path.join(ARCHIVE, "_index.md"), INDEX_MD, args.force)
    write_text(os.path.join(ARCHIVE, "_calibration.md"), CALIBRATION_MD, args.force)

    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
