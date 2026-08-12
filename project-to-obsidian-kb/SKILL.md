---
name: project-to-obsidian-kb
description: Build a categorized embedded engineering library and linked Obsidian knowledge base from a real firmware, robotics, hardware, or edge-AI workspace. Use when Codex must discover multiple subprojects, identify technology-stack evidence from project files, stage full projects into platform-and-board-classified archives, create template candidates separately, proactively distill project manuals and board documents, and keep source code out of Obsidian.
---

# 工程工作区 → 工程库与 Obsidian 知识库

以当前工作区的真实项目文件为依据，建立三层资产：

```text
原始工作区（黄金基线）
→ 嵌入式工程库（完整工程、模板候选、资料归档）
→ Obsidian嵌入式知识库（导航、证据、资料蒸馏、项目和验证记录）
```

不要把完整源码复制到 Obsidian。完整工程先进入工程库的 `项目归档`；只有边界、依赖、独立构建与验证明确后，才提升为 `模板仓库` 资产。

## 0. 安全迁移边界

- 先只读扫描、输出迁移计划，再写入。
- 默认迁移是：**复制 → SHA256 校验 → 保留原工程**。
- 不自动删除、移动、重命名或覆盖原始工程。旧路径处理必须在校验、链接和构建入口复查后，由用户明确授权。
- 不修改 `.ioc`、`.syscfg`、启动文件、链接脚本、厂商 SDK、原理图、PCB、BOM、构建脚本或原 README/AGENTS。
- 所有自动识别、源码、手册、原理图结论初始均为 `trust_level: L0`。

## 1. 先确定工作区与子项目

1. 使用当前目录为 `WORKSPACE_ROOT`；只扫描该目录及子目录。
2. 阅读实际存在的 `README.md`、`AGENTS.md`、任务上下文、构建/烧录/调试脚本、配置、实验记录、故障记录和硬件资料。
3. 识别工程组与子项目：
   - 子项目标记包括 `CMakeLists.txt`、`Makefile`、`platformio.ini`、`.ioc`、`.syscfg`、`.uvprojx`、`.ewp`，或 `tools/build.ps1`、`tools/flash.ps1`、`tools/validate.ps1`；
   - 一个双板项目可以作为完整工程组归档，同时分别为 STM32、MSPM0、K230 等子项目建档；
   - 仅含手册、原理图和资料包的目录进入资料归档，不当作代码工程。
4. 运行只读扫描：

```powershell
python scripts/build_workspace_library.py --project-root <WORKSPACE_ROOT> --report <报告路径>
```

报告必须列出每项判断的来源文件和相对路径；无法确认时写“待确认”或“缺失，需手动实现”。

## 2. 识别实际技术栈并分域，不集中到模块页

必须从项目内容和配置中识别并记录证据：

```text
MCU / SoC / 具体器件 / 开发板
C / C++ / Python / MicroPython / Rust / Shell
STM32 / MSPM0 / ESP32 / K230 / Arduino / RP2040 / Linux
HAL / LL / DriverLib / ESP-IDF / Arduino / CanMV / RT-Thread / FreeRTOS / 裸机
CMake / Make / CubeIDE / Keil / CCS / PlatformIO / idf.py / 脚本工具
UART / I2C / SPI / CAN / ADC / DMA / PWM / 定时器 / 编码器 / USB / 网络 / 摄像头
PID / 滤波 / 视觉识别 / 运动控制 / 通信协议 / 状态机
```

不要把全部内容放在单一 `模块导航`。按实际证据分布到：

```text
20-芯片与开发板/
30-硬件模块与接口/
40-外设与驱动/
50-软件设计与算法/
60-通信协议/
70-构建与烧录/
80-项目与实验记录/
98-资料索引/
```

每个领域索引必须回链 `项目导航` 和 `技术栈地图`；模块候选只出现在对应领域的聚合表中，不默认一模块一笔记。

## 3. 创建工程库和知识库

经用户确认后执行：

```powershell
python scripts/build_workspace_library.py `
  --project-root <WORKSPACE_ROOT> `
  --engineering-root <工程库目录> `
  --vault-root <知识库目录> `
  --create
```

工程库结构必须是：

```text
嵌入式工程库/
├── 模板仓库/
│   ├── stm32/<板卡或器件>/<模板名>/
│   ├── mspm0/<板卡或器件>/<模板名>/
│   ├── k230/<板卡或器件>/<模板名>/
│   └── common/<通用模块>/
├── 项目归档/
│   └── <平台>/<板卡或具体器件>/<工程组>/<子项目>/
├── 资料归档/
└── 工程迁移计划.md
```

### 归档完整工程

用户确认迁移计划后，执行：

```powershell
python scripts/build_workspace_library.py `
  --project-root <WORKSPACE_ROOT> `
  --engineering-root <工程库目录> `
  --vault-root <知识库目录> `
  --create --stage-archives
```

此操作只复制完整工程组和资料组到工程库，并逐文件 SHA256 校验；不会删除原工作区。校验后的归档目录生成 `归档校验.json`。

### 模板提升规则

- 项目归档默认保存完整已知工程；不要自动把整个比赛项目放进模板仓库。
- 模板候选必须明确：公共接口、数据所有权、HAL/BSP/SDK、PinMux、DMA、中断、任务、构建依赖、安全状态和最小验证。
- 先复制到模板候选新副本并独立构建，再记录 L1；硬件功能验证后才可记录 L2。

## 4. 知识库必须建立连接图

最少连接关系：

```text
README
→ 项目导航
  → 技术栈地图
  → 工程库导航
  → 子项目索引 / 项目文件地图
  → 芯片、接口、外设、算法、协议、构建领域索引
  → 项目总览 / 构建与验证状态
  → 资料清单 / 硬件资料蒸馏任务
  → 待确认
```

所有生成笔记必须有入口和回链；不要留下无入口孤立文件。项目档案按真实子项目创建，不按每个 `.c/.h` 文件创建。

工程模板和项目归档对应的知识库笔记必须记录：

```yaml
repo_name:
repo_relative_path:
repo_path:
platform:
mcu:
board:
toolchain:
verified_compile:
verified_hardware:
trust_level:
```

## 5. 按目标项目实际内容生成语义模块索引与模块笔记

本 Skill 面向任意嵌入式开发者，不能把某个用户的芯片、板卡、模块名称或目录结构当作固定输出。用户已有知识库只能作为组织形式参考，不能作为目标项目事实来源。

### 目标

在完成目标项目文件阅读后，生成一个明确的模块入口：

```text
60-可复用代码与工程模板/代码模块索引.md
```

再根据目标项目实际存在的功能，创建少量语义模块笔记。模块名称必须从目标项目的真实职责、数据流、调用关系和技术栈中来；不得预设任何固定模块名称。

### 通用生成步骤

1. 对每个子项目分别读取 README、AGENTS、入口文件、用户代码、调用方、构建配置、测试、硬件资料和实验记录。
2. 先建立私有代码扫描清单，记录文件、类、函数、API、依赖和来源路径；该清单放工程库，不进入 Obsidian 图谱。
3. 根据功能职责、数据流、控制流、硬件所有权、线程/中断上下文、输入输出和复用边界归并模块。
4. 每个子项目建议生成 3~8 个高价值语义模块；项目很小则按实际减少，项目复杂则按功能域分组，不要强行套固定数量。
5. 模块标题使用目标项目自己的功能语义。例如视觉项目可生成目标检测与坐标标定；电机项目可生成轮速测量与底盘速度控制；传感器项目可生成 IMU 数据解析与零偏处理；网络项目可生成设备发现与控制报文；FPGA 项目可生成采样通道与时序控制；上位机项目可生成串口设备管理与实时曲线。
6. 如果实际项目没有某个功能，不创建该类笔记；未知职责进入 `99-待确认`。

### 模块笔记契约

每张模块笔记必须记录：

```yaml
type: 代码模块
status: 自动识别后待人工确认
trust_level: L0
platform: []
mcu: []
language: []
module_type: 驱动/算法/通信协议/控制/工具/应用/待确认
source_project: <目标子项目>
source_files: [普通文本来源路径，不建立源码 Wiki 链接]
repo_name: <目标工程库>
repo_relative_path: <项目归档或模板候选路径；未迁移则待确认>
interfaces: []
dependencies: []
verified_compile: false
verified_hardware: false
unverified_items: []
related_notes: []
```

正文至少写清功能目标、模块职责、输入输出、单位、协议字段、状态、时序、API、类、函数、宏、结构体、芯片、外设、框架、HAL/BSP、PinMux、DMA、中断、任务、模型或网络依赖，调用与数据流，纯逻辑与硬件入口边界，移植和复用条件，构建/测试/上板/整机验证，限制、风险、冲突和待确认项，以及与项目、芯片、接口、算法、协议、构建、验证和故障笔记的 Wiki 链接。

### 图谱规则

- `README → 项目导航 → 代码模块索引 → 语义模块笔记` 必须可达；
- 每个语义模块回链模块索引和所属子项目档案；
- 模块笔记之间按真实依赖互链，不建立全连接；
- `source_files` 只能是 YAML 或普通文本，不创建 `.c/.h/.cpp/.hpp/.py` 文件节点；
- 自动扫描得到的函数/API只是线索，不能直接写成“已经可复用”或提升 trust_level。

### 只扫描与已蒸馏的区别

- 只有文件扫描、正则、类名或函数名时：生成“模块候选待人工蒸馏”索引，不伪造完整结论；
- Agent 已实际阅读代码、调用方、配置和资料时：才生成有功能说明、依赖、边界和链接的语义模块笔记；
- 语义模块必须采用目标项目自己的语言和功能，不复制其他项目的知识库模块名称。
## 5. 主动蒸馏项目内硬件资料

扫描后必须进入 `98-资料索引/硬件资料蒸馏任务.md`，不能仅列 PDF 文件名。

1. 识别高优先级数据手册、参考手册、开发板手册、引脚图、原理图、PCB 和 BOM；并关联其所属项目或资料组。
2. 对需要的 PDF/DOCX/PPTX/XLSX/HTML 调用 `document-to-markdown`。容器拉取、Docker 或 Podman 运行前先获取用户许可。
3. 主动阅读转换稿正文、目录、表格、版本和页码。
4. 资料足够时创建并互链：

```text
<芯片型号>-芯片资源与PinMux速查.md
<板卡名><芯片型号>开发板档案.md
<板卡名>-板级引脚与接口.md
```

5. 每条事实写明 `source_path`、资料版本、页码/章节、L0 和待确认项。资料冲突保留双方来源；不要猜测。

## 6. 一键生成模式

当用户要求“一键生成项目知识库”或直接授权整理当前工作区时，必须按下面顺序一次完成，不要只执行文件扫描：

```text
只读扫描
→ 阅读项目 README / AGENTS / 构建配置 / 入口与测试
→ 创建工程库三层目录
→ 复制完整工程到项目归档并 SHA256 校验（仅在用户授权迁移时）
→ 创建分域知识库导航
→ 创建 代码模块索引.md
→ 根据目标工程实际技术栈和功能创建语义模块笔记，不套用其他项目的固定模块名称
→ 创建硬件资料蒸馏任务
→ 检查 Wiki 链接、孤立笔记和源码链接
→ 输出构建报告与待确认项
```

一键命令：

```powershell
python scripts/build_workspace_library.py `
  --project-root <WORKSPACE_ROOT> `
  --engineering-root <ENGINEERING_ROOT> `
  --vault-root <VAULT_ROOT> `
  --create --stage-archives
```

一键模式仍然不能绕过以下边界：

- 不自动构建、烧录、上板、运行 Docker 或访问硬件；
- 不把 L0 自动模块笔记伪装成 L1/L2/L3；
- 不把 `.c/.h/.cpp/.hpp/.py` 做成 Obsidian 节点；
- 不删除旧工程；
- 不把整个工程自动提升到模板仓库。

### 一键生成的最低结果

必须至少存在并互相连接：

```text
README.md
00-首页与导航/项目导航.md
00-首页与导航/技术栈地图.md
00-首页与导航/工程库导航.md
01-项目地图/子项目索引.md
60-可复用代码与工程模板/代码模块索引.md
98-资料索引/硬件资料蒸馏任务.md
80-项目与实验记录/构建与验证状态.md
99-待确认.md
```

根据目标项目证据，按需生成具体语义模块笔记；没有对应功能时不要创建示例模块。
## 6. 验收和最终报告

检查：

- 工程库与知识库均未覆盖已有资产；
- 归档副本 SHA256 与原工程一致；
- Obsidian 内部链接无不存在目标；
- 不复制完整源码进知识库；
- 技术栈、硬件和验证结论都有来源；
- 构建、烧录、目标板、整机证据分开；
- 未经授权不运行构建、烧录、容器或硬件操作。

最终说明：工程组/子项目、工程归档路径、模板候选、技术栈证据、主动蒸馏资料、构建/上板状态、待确认项、旧路径是否仍保留。

## 随附资源

- `scripts/build_workspace_library.py`：工作区扫描、子项目识别、工程库/知识库生成、归档复制和 SHA256 校验。
- `scripts/convert_selected_documents.ps1`：选定资料的 Docker/Podman Markdown 转换。
- `references/project-kb-construction.md`：双库与链接规则。
- `references/module-extraction.md`：模板候选提取边界。
- `references/board-distillation.md`：芯片、开发板和 PinMux 蒸馏规则。
