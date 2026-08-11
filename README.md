# My Skills｜我的 AI 技能集合

个人可复用 AI Skills 集合仓库。每个 skill 独立存放于一个子目录，包含 `SKILL.md`（技能定义）及其辅助文件。

## 仓库结构

```
my-skills/
├── README.md                      # 本说明
├── board-manual-distiller/        # 板卡手册与引脚资料蒸馏器
│   ├── SKILL.md                   # 技能主文件
│   ├── README.md                  # 技能说明
│   └── references/                # 子场景模板
│       ├── 主档案模板.md
│       ├── 芯片PinMux模板.md
│       ├── 板级接口模板.md
│       ├── 供电调试启动模板.md
│       └── 总索引模板.md
├── project-to-obsidian-kb/        # 工程转 Obsidian 嵌入式知识库
│   ├── SKILL.md                   # 技能主文件
│   ├── agents/                    # 界面信息
│   ├── scripts/                   # 盘点与转换脚本
│   └── references/                # 输出契约、模块抽取与蒸馏约束
│       ├── board-distillation.md
│       ├── module-extraction.md
│       └── project-kb-construction.md
└── <新skill>/                     # 后续新增 skill 放在这里
    └── SKILL.md
```

## 技能列表

| Skill | 说明 | 状态 |
|---|---|---|
| [board-manual-distiller](board-manual-distiller/) | 板卡手册与引脚资料蒸馏器：将 MCU 数据手册/原理图/Wiki 蒸馏为结构化 Obsidian Markdown 档案（主档案+PinMux+板级接口三层结构） | ✅ v1.0 |
| [project-to-obsidian-kb](project-to-obsidian-kb/) | 工程转 Obsidian 嵌入式知识库：扫描嵌入式/机器人/固件/硬件工程，构建工程参照层与可复用候选层，生成模块卡、API 索引和板卡蒸馏笔记，不修改原工程文件 | ✅ v2.0 |

## 如何添加新 Skill

1. 在本仓库创建新目录：`<skill-name>/`
2. 编写 `SKILL.md`（含 YAML frontmatter：`name` + `description`）
3. 按需添加辅助文件（`references/`、脚本等）
4. 更新本 README 的技能列表
5. 提交并推送

## Skill 编写规范

- `SKILL.md` 必须包含 YAML frontmatter：`name`（唯一标识）与 `description`（功能 + 触发场景，200字符内）
- `description` 需明确说明**何时触发**（例："用户提出XX需求时调用"）
- 复杂技能建议拆分 `references/` 子场景模板

## 安装到 Trae / Codex

将任意 skill 目录复制到：
- **Trae / TraeWork**：`C:\Users\<你的用户>\.trae-cn\skills\<skill-name>\`
- **Codex**：`~/.codex/skills/<skill-name>/`
