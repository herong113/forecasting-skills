# forecasting-skills

**把「我觉得大概能成」变成可检验的数字概率，并跟踪到底。**

两个预测类 Agent Skill 的合集，方法论源自 Philip Tetlock《超预测》与 Good Judgment Project。

> 没有概率就没有校准，没有记分就没有学习。

---

## 包含的技能

| 技能 | 干什么 | 独立可用 |
|---|---|---|
| **[superforecasting](skills/superforecasting/SKILL.md)** | 把模糊问题变成可检验的数字概率，登记入档，长期跟踪更新，到期用 Brier 分数校准。10 步流程覆盖「值不值得预测 → 定价 → 追踪结算」全程 | ✅ 是（RCF 缺失时自动降级） |
| **[reference-class-forecasting](skills/reference-class-forecasting/SKILL.md)** | 参考类预测（RCF，外部视角）——用同类**已完结案例**的统计分布，修正内部估计的乐观偏差（规划谬误） | ✅ 是 |

超预测在第 3 步会**调用** RCF 的方法、数据源白名单与基线库，两个技能同仓安装效果最佳。
RCF 不可用时超预测会自动走**降级路径**（D2：纯公开检索），仍能独立完成外部视角。

---

## 安装

```bash
npx skills add herong113/forecasting-skills
```

装单个技能：

```bash
npx skills add herong113/forecasting-skills --skill superforecasting
```

---

## 快速上手

### 超预测：判断一件事会不会发生

```
我打算跳槽去一家现在的创业公司，两年后它还活着的概率有多大？
```

它会做这些事（而不是直接甩一个数字）：

1. **先筛值不值得预测** —— 影响多大？可不可预测？时间跨度多长？四出口分流（规则答案 / 走全套 / 情景规划 / 劝退），**多数问题应当死在这一步**。
2. **先锁你的直觉估计并封存** —— 防止后面被结构化结果污染，最后用来做叙事谬误诊断。
3. **费米分解** —— 把问题拆成可检验的叶子，但不做计算。
4. **找外部基线** —— 同类事情历史上发生率是多少？（调用 RCF）
5. **总概率锚定 + 瓶颈诊断** —— **不逐叶相乘**（见下文 C+ 方案）。
6. **输出** —— 一个数字 + 敏感区间 + 直觉对照，重大决策另出双层 HTML 报告（大白话 + 专业解读）。
7. **入档 → 触发式更新 → 到期结算 → 复盘校准** —— 累积到 20 条后产出校准报告。

### 参考类预测：修正你的乐观偏差

```
我这个项目要多久能做完？
```

它会问「同类项目历史上平均超时多少」，用分布而不是感觉来回答。

---

## 关键设计（不可动摇的决策）

这些是刻意做的取舍，不是随意选择：

- **D1 · 锁直觉估计上移到第 1 步** —— 在三筛之后、费米分解之前。既做叙事谬误诊断，又吸收 RCF 自带的「锁内部估计」步骤，消除「两套锁先验」冲突。
- **D2 · 外部视角先于内部视角** —— 顺序不可颠倒。先拿同类基线，再看本案例的特殊性。
- **D3 · C+ 方案：禁止逐叶相乘** —— 总概率锚定上位参考类，费米树退回做「找差异点 + 诊断瓶颈」。逐叶相乘忽略共因失效，且制造虚假精确。
- **限幅双口径** —— 基线 ≥10% 用百分点制（单因素 ≤±10、累计 ≤±20）；基线 <10% 改用倍数制（单因素 ≤×2、累计 ≤×3、下限 ≥×0.5）。小概率题用百分点制会一次跳到荒谬区间。
- **报告双层结构** —— 重大决策报告先「大白话」再「专业解读」。白话层不得稀释结论、不得删掉不利信息，两层信息必须一致。
- **档案只追加不覆盖** —— `.md` 是内容权威，永不覆盖；HTML 报告是可再生的呈现层，可用新版替代。
- **档位命名必须对齐权威标准** —— 涉及量化档位（伤残等级、疾病分期等）时，名称与数值区间必须取自国标 / WHO / ISO。同名档位在不同标准下可能指不同区间。

---

## 质量记录

两个技能都经过独立优化迭代，评分与过程全部留档：

| 技能 | 版本 | 优化评分轨迹 | 台账 |
|---|---|---|---|
| superforecasting | 1.2 | 77.0 → 97.0（8 轮） | [results.tsv](skills/superforecasting/results.tsv) |
| reference-class-forecasting | 1.5 | — | [results.tsv](skills/reference-class-forecasting/results.tsv) |

每个技能都带 `test-prompts.json`（典型 / 歧义 / 出口分流三类用例），可用于回归验证。

---

## 仓库结构

```
.
├── .claude-plugin/marketplace.json   Claude Code 插件市场清单
├── README.md
├── CHANGELOG.md
├── LICENSE                           MIT
├── PUBLISH.md                        发布与自验清单
└── skills/
    ├── superforecasting/
    │   ├── SKILL.md                  主入口（10 步流程 + 硬停点）
    │   ├── references/               01 准入…06 更新结算、90 红线与反例库
    │   ├── assets/                   ledger 模板 / 档案模板 / 报告模板
    │   ├── scripts/                  brier.py / archive_io.py / init_archive.py
    │   ├── results.tsv               优化评分台账
    │   └── test-prompts.json         回归用例
    └── reference-class-forecasting/
        ├── SKILL.md
        ├── references/               base-rates.md（经典基线数据集）/ question-bank.md
        ├── assets/report-template.html
        ├── results.tsv
        └── test-prompts.json
```

---

## 运行环境

技能面向 **WorkBuddy / Claude Code** 类型的 Agent 宿主（`SKILL.md` + `references/` 组织方式，走 `skills/<name>/` 发现）。

预测档案默认落在 `~/.workbuddy/forecast-archive/`，脚本用 Python 3 标准库，无第三方依赖。

---

## License

[MIT](LICENSE)
