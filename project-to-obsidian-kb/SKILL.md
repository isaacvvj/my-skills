---
name: project-to-obsidian-kb
description: Build or incrementally organize a linked embedded engineering library and Obsidian knowledge base from the real contents of the current firmware, robotics, hardware, or edge-AI project. Use when Codex must inspect an existing project, keep source code out of Obsidian, create a connected project map and reusable-module index, proactively convert and distill project manuals or hardware documents, or record build and board-verification evidence without modifying the original project.
---

# 工程转嵌入式工程库与 Obsidian 知识库

对当前工程建立三个明确层次：

```text
原工程（唯一黄金基线，绝不自动修改）
├── 嵌入式工程库（工程参照、模块机器清单、模板候选入口；不自动剪切代码）
└── Obsidian嵌入式知识库（导航、资料蒸馏、决策、验证、故障；不存完整源码）
```

目标不是批量生成很多孤立笔记，而是建立少量**中心导航页**，让 AI 能沿着链接进入原工程、工程库清单、硬件资料和验证记录。

## 强制边界

- 从当前目录向上确定 `PROJECT_ROOT`；以 `README.md`、`AGENTS.md`、`.git`、构建配置、源码目录和硬件资料为依据。
- 先只读扫描、阅读项目关键文件并输出计划；没有写入授权时停止在计划阶段。
- 只在 `PROJECT_ROOT\嵌入式工程库` 和 `PROJECT_ROOT\Obsidian嵌入式知识库` 写入。
- 不修改、移动、删除、重命名或覆盖原工程源码、配置、构建脚本、SDK、原理图、PCB、BOM 或资料源文件。
- 原工程代码不复制到 Obsidian。知识库仅保存摘要、API/依赖候选、关键结论和指向真实源文件的链接。
- 所有扫描、源码、手册和原理图结论默认 `trust_level: L0`；构建、上板、整机和稳定复用必须分开记录。

## 一、只读发现与计划

1. 确定 `PROJECT_ROOT`，只扫描该目录与子目录；识别子项目，分别记录来源。
2. 阅读项目实际存在的：
   - `README.md`、`AGENTS.md`、任务上下文、项目说明、实验/故障记录；
   - 构建、烧录、调试、验证脚本和依赖配置；
   - `CMakeLists.txt`、`Makefile`、`platformio.ini`、`.ioc`、`.syscfg` 等；
   - 原理图、PCB、BOM、接线说明、PDF、开发板资料和数据手册。
3. 运行只读盘点：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --report <临时报告路径>
```

4. 输出计划：工程根目录和证据、拟创建的双库目录、聚合模块清单、待蒸馏资料、风险、验证方式和回退方式。

脚本的模块识别仅用于阅读入口；函数指针、宏、跨文件全局变量、中断、RTOS、DMA、PinMux 和硬件状态必须由 Agent 阅读真实工程后确认。

## 二、同时创建工程库与知识库

经授权后运行：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --create
```

默认输出：

```text
PROJECT_ROOT/
├── 原工程文件……                       # 完全保留
├── 嵌入式工程库/
│   ├── 工程参照/<项目名>/工程清单.md
│   ├── 工程参照/<项目名>/模块索引.json
│   └── 模板候选/README.md
└── Obsidian嵌入式知识库/
    ├── README.md
    ├── 00-首页与导航/
    │   ├── 项目导航.md
    │   ├── 工程库导航.md
    │   └── 模块导航.md
    ├── 20-芯片与开发板/
    ├── 60-可复用代码与工程模板/
    ├── 80-项目与实验记录/
    ├── 98-资料索引/
    └── 99-待确认.md
```

### 工程库职责

工程库不自动复制代码，更不从原工程剪切代码。它集中保存：

- 工程入口、构建入口和模块机器清单；
- 每个模块候选的源文件、SHA256、API、函数名和 include 依赖；
- 后续抽取为真正模板前的迁移门槛。

只有用户明确要求并批准迁移计划后，才能把确定的模块复制到新的模板候选工程中独立构建。

### 知识库职责

知识库只保留少量互相链接的中心页：

```text
README
 项目导航
 工程库导航
 模块导航（聚合表，不逐模块建孤立笔记）
 项目总览 / 构建与验证状态
 硬件资料与板卡候选
 资料清单 / 硬件资料蒸馏任务
 待确认
```

不得为每个源码文件自动创建 Markdown。只有真正值得长期沉淀、已明确接口和适用边界、或有构建/上板证据的模块，才由 Agent 在用户同意后建立独立模块笔记。

## 三、让 AI 参照现有工程，而不是猜代码

从 `00-首页与导航/模块导航.md` 开始。该页按模块类型聚合列出：

- 模块候选名称；
- 原工程 `.h/.c/.cpp/.py` 相对链接；
- 函数/API 候选；
- 当前复用边界。

AI 的阅读顺序必须是：

```text
模块导航
 原工程头文件
 原工程实现文件
 调用方
 构建/芯片配置
 硬件资料和验证记录
```

对候选模块，只能先生成"抽取计划"：公共 API、数据所有权、全局变量、中断/任务上下文、HAL/BSP、PinMux、初始化顺序、安全状态和独立构建方法。不要把"扫描到模块"写成"可直接复用"。

详细规则见 `references/module-extraction.md`。

## 四、主动蒸馏项目内硬件资料

不能只列出 PDF 文件名。扫描后必须进入：

```text
98-资料索引/硬件资料蒸馏任务.md
```

该页面由扫描器主动列出可能的数据手册、参考手册、开发板用户手册、引脚资料、原理图、PCB 和 BOM，并按优先级排序。

执行方法：

1. 优先读取高优先级硬件资料；中优先级资料先读取标题、目录和正文确认类型。
2. 对 PDF、DOCX、PPTX、XLSX、HTML 等调用可访问的 `document-to-markdown` Skill；转换前确认 Docker/Podman 可用，涉及拉取镜像或运行容器时先征求用户许可。
3. 将转换稿写入 `98-资料索引/转换稿/`，原始资料保持不动。
4. **主动阅读转换稿**，从正文、表格、页码和版本中提取事实；不要仅根据文件名蒸馏。
5. 资料足够时，按需创建并互链：

```text
20-芯片与开发板/<芯片型号>-芯片资源与PinMux速查.md
20-芯片与开发板/<板卡名><芯片型号>开发板档案.md
20-芯片与开发板/<板卡名>-板级引脚与接口.md
```

6. 每条关键结论写 `source_path`、资料版本、页码/章节、`trust_level: L0` 和待确认项。

若文档无法转换、是扫描件、缺少型号，或 Docker/Podman 不可用，明确记录"缺失，需手动实现"或解析限制；不要编造芯片和板卡档案。

板卡蒸馏的三层结构、来源优先级和冲突处理见 `references/board-distillation.md`。

## 五、验证与完成报告

生成后检查：

1. 知识库链接全部指向存在的笔记或真实工程/工程库文件；
2. 知识库没有完整源码副本和大量无入口孤立笔记；
3. 每个中心页能回到 `README.md` 或相邻导航页；
4. 原工程 Git 状态或文件哈希保持不变；
5. 资料、模块和验证结论均有来源；未知项进入 `99-待确认.md`；
6. 不擅自构建。获得授权且项目命令安全时，才执行一次项目自身构建并记录 L1。

最终用简体中文说明：项目根目录、双库位置、读取的项目文件、识别的技术栈、聚合模块、主动蒸馏的资料、创建的芯片/板卡档案、构建/上板证据、待确认项、原工程改动情况与回退方式。

## 附带资源

- `scripts/build_project_inventory.py`：只读扫描并生成双库的聚合入口与工程模块清单。
- `scripts/convert_selected_documents.ps1`：通过 Docker 或 Podman 转换明确选中的资料。
- `references/project-kb-construction.md`：双库职责、核心笔记和证据契约。
- `references/module-extraction.md`：现有工程参照与后续模板抽取规则。
- `references/board-distillation.md`：芯片、开发板和 PinMux 蒸馏约束。
