# project-to-obsidian-kb

将嵌入式 / 机器人 / 固件 / 硬件工程扫描为项目旁的 Obsidian 知识库，不修改原工程文件。

适用于：盘点已有工程、把代码/配置/硬件资料映射为可追溯笔记、选择性转换数据手册、按“主档案 + 芯片 PinMux + 板级接口”三层结构蒸馏开发板档案。

## 能力边界

- 从当前目录向上定位 `PROJECT_ROOT`（依据 `README.md` / `AGENTS.md` / `.git` / 构建文件 / 源码目录等证据判断）。
- 先只读扫描并输出计划，用户确认后才创建知识库（默认 `PROJECT_ROOT\Obsidian嵌入式知识库`）。
- 不移动、删除、重命名或覆盖原工程文件；不复制源码、SDK、原理图、PCB、BOM 或整包资料；笔记用相对路径指回原文件。
- 只记录文件和已转换资料支持的事实；未知写“待确认”；资料结论默认 `trust_level: L0`。
- 不把本机构建写成上板验证，不把烧录写成整机验证。

## 目录结构

```text
project-to-obsidian-kb/
├── SKILL.md                     # Codex / TRAE Skill 主文件
├── agents/
│   └── openai.yaml              # Codex 界面信息
├── scripts/
│   ├── build_project_inventory.py      # 只读盘点 / 创建知识库骨架 / --dry-run 计划
│   └── convert_selected_documents.ps1  # 经 Docker / Podman 选择性转换资料
└── references/
    ├── vault-layout.md          # 输出目录与元数据契约
    └── board-distillation.md    # 板卡 / 芯片 / PinMux 蒸馏约束
```

## 安装

### Codex

```powershell
# Windows：将本目录放入 Codex 技能目录
Copy-Item -Recurse project-to-obsidian-kb $env:USERPROFILE\.codex\skills\
```

### TRAE（TraeWork）

```powershell
# 将本目录放入 TRAE 技能目录
Copy-Item -Recurse project-to-obsidian-kb C:\Users\<你的用户>\.trae-cn\skills\
```

安装后在新会话中询问“把当前工程转成 Obsidian 知识库”即可触发。

## 使用

```powershell
# 1. 只读盘点，输出报告（不写入工程）
python scripts\build_project_inventory.py --project-root <PROJECT_ROOT> --report <报告路径>

# 2. 计划模式：列出将新建/覆盖的文件，不写入任何内容
python scripts\build_project_inventory.py --project-root <PROJECT_ROOT> --create --dry-run

# 3. 确认后创建知识库骨架
python scripts\build_project_inventory.py --project-root <PROJECT_ROOT> --create

# 4. 选择性转换资料（需要 Docker 或 Podman）
powershell -ExecutionPolicy Bypass -File scripts\convert_selected_documents.ps1 `
  -InputFile <资料1>, <资料2> `
  -OutputDirectory <PROJECT_ROOT>\Obsidian嵌入式知识库\98_资料索引\转换稿 `
  -ProjectRoot <PROJECT_ROOT>
```

完整工作流见 `SKILL.md`；输出契约见 `references/vault-layout.md`。

## 验证状态

已验证：

- `quick_validate.py` 校验通过；
- Python 编译检查、PowerShell 语法解析通过；
- 隔离临时工程冒烟测试：识别 STM32 / CMake 证据、生成预期骨架、原工程样例文件哈希不变；
- `--create --dry-run` 计划模式、ESP-IDF 证据收紧、转换脚本 UTF-8 无 BOM 输出。

未验证：

- 本机无 Docker / Podman，资料转换仅完成语法检查，未实际执行；
- 未在真实 STM32 / MSPM0 / K230 或 EDA 工程上运行；
- 不包含任何个人知识库固定路径、固定芯片或历史验证结论，适合从任意工程开始扫描。

## License

当前未附带 License 文件；公开使用前请自行确认授权方式。