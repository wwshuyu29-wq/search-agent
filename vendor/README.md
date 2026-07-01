# Vendor 目录 — 离线自包含的外部 skill

本目录内嵌了两个上游 skill 仓库的完整副本，用于**无外网环境**下的离线安装。

## 目录内容

| 目录 | 来源 | 内容 | 大小 |
|---|---|---|---|
| `marketing/` | https://github.com/coreyhaines31/marketingskills | 44 个营销 / 增长 / SEO / CRO / 内容 skill | 3.4 MB |
| `finance/` | https://github.com/himself65/finance-skills | 20+ 个金融 / 估值 / 情绪 / 市场数据 skill（6 个 plugin 分组） | 1.2 MB |

## 快照时间

打包时的最新提交（`.git` 已剥离以减小体积）。

## 安装流程

`install.sh` 会**优先使用本 vendor 目录**，无需联网：

```
Step 3 部署 marketing
  ├── 检测 vendor/marketing/ 存在？→ 直接 cp -R 到 ~/.codex/skills/marketing/
  └── 若不存在 → 回退到 git clone (需要网络)

Step 4 部署 finance
  ├── 检测 vendor/finance/ 存在？→ 直接 cp -R 到 ~/.codex/skills/finance/
  └── 若不存在 → 回退到 git clone (需要网络)
```

## 更新 vendor（有网时执行）

```bash
cd vendor
rm -rf marketing finance
git clone --depth 1 https://github.com/coreyhaines31/marketingskills.git marketing
git clone --depth 1 https://github.com/himself65/finance-skills.git finance
rm -rf marketing/.git finance/.git
```

然后重新打包分发。
