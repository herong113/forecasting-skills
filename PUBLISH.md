# 发布与自验清单

本仓库已结构完整、可安装、可自验。发布只差「建仓库 + 推送」。

## 0. 发布前状态（已实测）

| 检查 | 结果 |
|---|---|
| 技能目录结构 | 2 个技能，22 个文件 |
| 开发残留清理 | `.bak` / `.bak2` / `.bak3` / `.baseline` / `diagnostics.tsv` / `__pycache__` **全部排除** |
| 脚本语法 | `brier.py` / `archive_io.py` / `init_archive.py` 编译通过 |
| 脚本行为 | `brier.py --ledger <空台账>` 正确返回「没有已结算的预测」而非报错 |
| JSON 合法性 | `marketplace.json` / `test-prompts.json` / `ledger-模板.json` 均可解析 |
| **私有内容扫描** | 0 命中——**无**真实私人预测档案、**无**本机绝对路径、**无**真实项目名 |
| 引用完整性 | 技能内 `references/` 引用 7/7 命中，0 断链、0 未引用 |

## 1. 本地仓库初始化

```bash
git init
git add -A
git -c user.name="<你的名字>" -c user.email="<你的邮箱>" commit -m "feat: forecasting-skills 1.0.0 - superforecasting + reference-class-forecasting"
```

> 本机**没有配置全局 git 身份**（`user.name` / `user.email` 均为空），所以上面用 `-c` 显式传入。
> 建议用 GitHub 的 noreply 邮箱，避免公开私人邮箱：
> `<你的数字ID>+<用户名>@users.noreply.github.com`

## 2. 推到 GitHub

```bash
gh repo create herong113/forecasting-skills --public --source=. --push
```

若仓库已存在，改用：

```bash
git remote add origin https://github.com/herong113/forecasting-skills.git
git branch -M main
git push -u origin main
```

## 3. 验证「一行装」（这一步不通过就不算发布完成）

```bash
npx skills add herong113/forecasting-skills
```

期望输出：`Found 2 skills` → `Installed 2 skills`。

装单个：

```bash
npx skills add herong113/forecasting-skills --skill superforecasting
```

## 4. 上 skills.sh

skills.sh（Vercel）**从公开 GitHub 仓库自动发现**，无需注册或投递。

前提：
1. 仓库为 public
2. `skills/<name>/SKILL.md` 能被匿名访问

## 5. 后续迭代流程

本仓库遵循「**每次修改都是新版本，绝不覆盖**」：

1. 改技能文件 → 同步升 `SKILL.md` 的 `version`
2. 追加 `CHANGELOG.md` 条目
3. 重新自验（上表各项）
4. 提交并推送

> **不要把 `.bak` / `.baseline` / `diagnostics.tsv` 提交进来** —— 它们是本机优化过程的备份与诊断记录，已在 `.gitignore` 中排除。
