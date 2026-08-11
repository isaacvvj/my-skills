---
name: project-to-obsidian-kb
description: Build or incrementally organize a linked Obsidian knowledge base from the real contents of the current embedded, robotics, firmware, hardware, or edge-AI project. Use when Codex must first inspect an existing project, map its source into reusable-reference modules for AI reading, document build/configuration/hardware evidence, convert selected manuals to Markdown, or distill MCU and board records without changing the original project.
---

# 工程转 Obsidian 嵌入式知识库

将当前工程变成两层可追溯的 AI 工作上下文：

```text
原工程（唯一黄金基线，保留不动）
├── 工程参照层：结构、构建、配置、调用关系、模块入口
└── 可复用候选层：模块卡、API、依赖、复用边界、验证状态
```

这不是按目录复制代码，也不是把现有工程物理拆散。它应让 AI 能先定位到某个模块，再沿模块卡中的相对链接阅读原工程的 `.c/.h/.cpp/.py` 文件，并理解该模块能否安全迁移。

## 强制边界

- 从当前目录向上定位 `PROJECT_ROOT`；使用 `README.md`、`AGENTS.md`、`.git`、构建文件、源码目录和硬件资料证明判断。
- 写入前必须先完成只读盘点并给出计划。没有明确写入授权时，停在计划阶段。
- 只在 `PROJECT_ROOT\Obsidian嵌入式知识库` 写入；不要修改、移动、删除、重命名或覆盖原工程。
- 读取并尊重项目中的 `README.md`、`AGENTS.md`、任务上下文、构建/烧录脚本、原理图、BOM、接口约束和版本说明。文件缺失时明确说明。
- 不从文件名、记忆或 AI 推测补全芯片、引脚、电平、供电、模块功能或验证状态。
- 代码笔记只保留摘要、API、依赖、关键函数签名和原工程链接；默认不复制完整源码。原工程仍是 AI 参照的唯一基线。
- 资料/源码存在只表示 L0 参考；构建、上板和整机验证必须分开记录。

## 一、只读盘点与计划

1. 确定 `PROJECT_ROOT`，只扫描它及子目录；识别子项目并分别建立索引。
2. 阅读而不是只列出以下实际文件：
   - `README.md`、`AGENTS.md`、项目说明和实验/故障记录；
   - 构建、烧录、调试脚本和依赖配置；
   - `.ioc`、`.syscfg`、`CMakeLists.txt`、`Makefile`、`platformio.ini` 等；
   - 原理图、PCB、BOM、接线说明、数据手册和引脚资料。
3. 执行盘点脚本，先得到文件树、技术栈候选和**代码模块候选**：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --report <临时报告路径>
```

4. 输出简短计划，至少说明：工程根目录、识别依据、拟创建笔记、可复用候选模块、受保护/生成文件、资料转换范围、风险、验证和回退方式。

脚本使用同名源文件/头文件、显式 `#include`、函数声明和实现名生成模块候选。它只是阅读入口；模块职责、并发上下文和复用范围必须结合真实代码与调用方确认。

## 二、创建工程参照层和可复用候选层

获得授权后运行：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --create
```

默认创建的核心目录如下；根据实际项目增量扩展，空目录可不创建：

```text
Obsidian嵌入式知识库/
├── 00_总览/                    # 项目总览、技术栈、扫描报告、协作规则
├── 10_嵌入式工程/              # 工程结构、配置、构建和代码模块地图
├── 20_芯片与开发板/
├── 30_硬件模块与接口/
├── 50_项目记录与验证/
├── 60_可复用代码与工程模板/    # 参照模块卡，不移动原代码
├── 60_故障排查与经验/
├── 98_资料索引/
└── 99_待确认/
```

生成后先读：

```text
00_总览/项目总览.md
10_嵌入式工程/代码模块索引.md
60_可复用代码与工程模板/代码模块/
50_项目记录与验证/验证状态.md
99_待确认/待确认.md
```

默认不覆盖已有笔记。只有人工确认差异后，才使用 `--overwrite-generated` 更新自动生成内容。

## 三、把现有代码变成 AI 可读的模块参照

每个识别模块都应生成一张模块卡，而不是只在“源码文件清单”中出现。模块卡必须包含：

```yaml
type: 代码模块
source_files: [原工程相对路径]
module_type: 驱动/算法/协议/控制/应用入口/厂商依赖/待确认
interfaces: [从头文件获得的 API 候选]
verified_compile: false
verified_hardware: false
trust_level: L0
reuse_status: 候选/仅供参照/待确认
```

模块卡的正文必须提供：

1. 原工程 `.h`、实现文件和调用方的相对链接；
2. 从头文件提取的公共 API 候选、关键宏/数据结构和直接 `#include` 依赖；
3. 函数定义候选，用于快速定位实现；
4. AI 阅读顺序：**头文件 → 实现 → 调用方 → 构建/芯片配置 → 硬件资料**；
5. 复用边界：全局变量、中断/任务上下文、HAL/BSP、PinMux、初始化顺序、异常安全状态和项目专用耦合；
6. 验证边界：现有工程的代码不能自动升级为独立模块已构建、已上板或可稳定复用。

### 模块分类与抽取规则

- `.c/.h`、`.cpp/.hpp` 或同功能脚本形成一个候选模块；名字冲突、跨目录多实现或职责不清时标记“待确认”。
- `main.*`、顶层状态机、项目初始化属于**项目编排**：可供 AI 理解调用关系，但不默认迁移。
- `Drivers/`、`Startup/`、SDK、CMSIS、HAL、自动生成文件、链接脚本、`.ioc`、`.syscfg` 和 IDE 核心配置属于**受保护依赖**：只记录边界，不擅自拆分或复制。
- 只有明确公共 API、可分离依赖、最小构建条件和验证计划后，才能把“候选模块”迁入真正模板仓库。
- 不将整个源码文件夹复制进知识库；如需跨环境交接，连同原工程一并交付，或只摘录必要的 API/关键片段并标注 SHA256 与来源。

详细约束见 `references/module-extraction.md`。

## 四、手册转换与板卡蒸馏

只处理与当前项目或已选硬件直接相关的 PDF、DOCX、PPTX、XLSX、HTML 等资料；不要批量转换整个资料盘。

1. 在资料索引中记录来源路径、版本、用途和转换范围。
2. 优先使用可访问的 `document-to-markdown` Skill。它需要 Docker 或 Podman；拉取镜像或启动容器前先征得用户同意。
3. 随附脚本只转换明确选中的资料：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/convert_selected_documents.ps1 `
  -InputFile <资料1>, <资料2> `
  -OutputDirectory <PROJECT_ROOT>\Obsidian嵌入式知识库\98_资料索引\转换稿 `
  -ProjectRoot <PROJECT_ROOT>
```

4. 阅读 `references/board-distillation.md` 后，再生成“开发板主档案 + 芯片 PinMux + 板级接口”三层笔记。

资料转换稿和手册结论默认 L0；原理图缺失时不编造板级连接；资料冲突时保留双方来源并写入待确认。

## 五、验证与最终报告

创建后检查：

1. Markdown 可读取、YAML 可解析、Obsidian 内部链接指向存在的笔记；
2. 模块卡均能链接到原工程文件，且没有把完整源码无差别复制进知识库；
3. 所有技术栈、硬件参数、验证结果都有来源；无来源项进入 `99_待确认`；
4. 对比原工程 Git 状态或文件哈希，确认仅新增知识库；
5. 不擅自构建。只有项目自带命令明确安全且不修改源码/配置时，才在用户授权后执行一次构建，并将结果记录为 L1，不等同于上板。

最终用简体中文说明：项目根目录、知识库位置、读取的文件、识别的技术栈和模块、创建的笔记、链接关系、资料转换、是否构建、L0/L1/L2/L3 证据、未验证项、待确认项、原工程是否改动，以及如何回退（删除新建知识库目录即可）。

## 附带资源

- `scripts/build_project_inventory.py`：只读工程盘点，创建不覆盖的知识库骨架、模块索引和模块卡。
- `scripts/convert_selected_documents.ps1`：通过 Docker 或 Podman 转换明确选中的资料。
- `references/project-kb-construction.md`：项目自适应知识库的输出契约。
- `references/module-extraction.md`：现有工程转模块参照的规则。
- `references/board-distillation.md`：芯片、开发板和 PinMux 蒸馏约束。