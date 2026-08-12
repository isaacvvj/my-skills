# project-to-obsidian-kb｜工程工作区转嵌入式工程库与 Obsidian 知识库

以当前嵌入式/固件/机器人/硬件工作区的**真实项目文件**为依据，构建职责分离的三层资产：原始工作区（黄金基线）→ 嵌入式工程库（完整工程归档、模板候选、资料归档）→ Obsidian 嵌入式知识库（导航、证据、资料蒸馏、项目与验证记录）。

## 功能特性

- **多子项目识别**：自动识别 `CMakeLists.txt`、`Makefile`、`platformio.ini`、`.ioc`、`.syscfg`、`.uvprojx`、`tools/build.ps1` 等工程标记，双板/多芯片工程分别建档
- **技术栈证据化**：从文件内容提取 MCU/SoC、开发板、语言、框架、构建系统、接口与算法证据，输出到 `技术栈地图`
- **工程归档可校验**：`--stage-archives` 将完整工程复制到项目归档并逐文件 SHA256 校验，生成 `归档校验.json`，绝不删除原工程
- **语义模块蒸馏**：按目标项目真实职责生成 3~8 个功能模块笔记（如"目标检测与坐标标定"），不按 `.c/.h` 文件建孤立笔记
- **硬件资料主动蒸馏**：扫描 PDF/原理图/PCB/BOM 并进入 `硬件资料蒸馏任务`，按 L0~L3 记录来源与页码
- **知识库强连接图**：所有生成笔记从 `README → 项目导航` 可达并回链，无孤立文件

## 目录结构

```
project-to-obsidian-kb/
├── SKILL.md                        # 技能主文件（工作流/边界/一键模式/验收清单）
├── README.md                       # 本说明文件
├── agents/
│   └── openai.yaml                 # 界面信息（display_name / short_description / default_prompt）
├── scripts/
│   ├── build_workspace_library.py  # 工作区扫描、子项目识别、双库生成、归档复制与 SHA256 校验
│   └── convert_selected_documents.ps1  # 选定资料的 Docker/Podman Markdown 转换
└── references/
    ├── project-kb-construction.md  # 双库结构、连接图与证据契约
    ├── module-extraction.md        # 模板候选提取边界
    └── board-distillation.md       # 芯片、开发板与 PinMux 蒸馏规则
```

## 安装

将 `project-to-obsidian-kb/` 整个目录放入：

- **Trae / TraeWork**：`C:\Users\<你的用户>\.trae-cn\skills\project-to-obsidian-kb\`
- **Codex**：`~/.codex/skills/project-to-obsidian-kb/`
- 或任意支持 skills 的 Agent 工作目录

## 使用方式

直接向 Agent 描述需求即可自动触发：

> "把当前工程整理成知识库" / "一键生成项目知识库" / "把工作区归档到工程库并建 Obsidian 知识库"

只读扫描（先出计划）：

```powershell
python scripts/build_workspace_library.py --project-root <WORKSPACE_ROOT> --report <报告路径>
```

经确认后创建双库：

```powershell
python scripts/build_workspace_library.py `
  --project-root <WORKSPACE_ROOT> `
  --engineering-root <工程库目录> `
  --vault-root <知识库目录> `
  --create
```

## 安全边界

- 默认迁移是**复制 → SHA256 校验 → 保留原工程**，不自动删除、移动、重命名或覆盖原始工程
- 不修改 `.ioc`、`.syscfg`、启动文件、链接脚本、厂商 SDK、原理图、PCB、BOM 或构建脚本
- 完整源码不复制进 Obsidian；`.c/.h/.cpp/.hpp/.py` 不创建为 Obsidian 节点
- 自动识别结论默认 `trust_level: L0`；构建、烧录、目标板、整机证据分开记录
- 未经授权不运行构建、烧录、容器或硬件操作

## 输出示例

```
嵌入式工程库/
├── 模板仓库/<平台>/<板卡或器件>/<模板名>/
├── 项目归档/<平台>/<板卡或器件>/<工程组>/<子项目>/
└── 资料归档/<资料组>/

Obsidian嵌入式知识库/
├── 00-首页与导航/（项目导航、技术栈地图、工程库导航、语义模块蒸馏任务）
├── 01-项目地图/（子项目索引、项目文件地图、项目档案）
├── 20-芯片与开发板/ 40-外设与驱动/ 50-软件设计与算法/
├── 60-通信协议/ 60-可复用代码与工程模板/（代码模块索引）
├── 70-构建与烧录/ 80-项目与实验记录/ 95-AI协作规范/
└── 98-资料索引/（资料清单、硬件资料蒸馏任务）
```

## 版本状态

- 当前为 **v1**：核心扫描、双库生成、技术栈识别、语义模块、归档校验逻辑已实现并通过基础冒烟测试
- 尚未在真实嵌入式工程上完整跑通 `--create --stage-archives` 全流程；归档迁移、模板提升和硬件蒸馏需在目标项目上实测后回写结论

## License

MIT
