---
name: project-to-obsidian-kb
description: Scan an embedded, robotics, firmware, or hardware project and create a linked Obsidian knowledge base beside it without modifying source files. Use when Codex must inventory an existing project, map code/configuration/hardware documents into traceable notes, convert selected manuals to Markdown, or distill board and MCU records from project evidence. Also for Chinese queries about 工程转 Obsidian 知识库、扫描工程结构、建立项目知识库、转换数据手册、蒸馏开发板与芯片资料。
---

# 工程转 Obsidian 嵌入式知识库

基于当前工程的真实文件创建项目旁的 Obsidian 知识库。将工程结构、构建入口、配置文件、硬件资料和验证边界链接为 Markdown 笔记；不要把个人 Vault 的固定芯片、目录、工具链或验证结论套入陌生工程。

## 不可违反的边界

- 先从当前目录向上定位 `PROJECT_ROOT`；用 `README.md`、`AGENTS.md`、`.git`、构建文件和源码目录证明判断。
- 先只读扫描并输出计划；没有写入授权时，停在计划阶段。
- 只在 `PROJECT_ROOT\Obsidian嵌入式知识库` 写入。不要修改、移动、删除、重命名或覆盖原工程文件。
- 不复制源码、SDK、生成文件、原理图源、PCB 源、BOM 或整包资料；笔记以 `source_path` / `repo_relative_path` 指回它们。
- 只记录从文件和已转换资料中得到的事实。未知写“待确认”，资料结论默认 `trust_level: L0`。
- 不把本机构建写成上板验证，不把烧录写成整机验证。

## 工作流

### 1. 定位与只读盘点

1. 阅读项目的 `README.md`、`AGENTS.md`、任务上下文、构建/烧录脚本和已有设计说明；不存在时明确说明未找到。
2. 向上寻找工程根目录，优先用 `.git`、`CMakeLists.txt`、`platformio.ini`、`*.ioc`、`*.syscfg`、`Makefile`、`Core/Drivers/App/BSP/src/include/tools` 等证据判断。
3. 运行盘点脚本生成报告，不写入项目：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --report <临时报告路径>
```

若本机没有 `python`，使用实际可用的 Python 可执行文件。盘点脚本只读取路径和文件名；不要把它的技术栈候选当成已验证事实。

4. 输出计划：拟创建目录、拟转换的资料、识别到的技术栈证据、风险、验证方法和回退方法。若用户尚未授权写入，等待确认。

### 2. 创建项目旁知识库

获得授权后运行：

```powershell
python scripts/build_project_inventory.py --project-root <PROJECT_ROOT> --create
```

默认创建：

```text
Obsidian嵌入式知识库/
├── 00_总览/
├── 10_嵌入式工程/
├── 20_芯片与开发板/
├── 30_硬件模块与接口/
├── 50_项目记录与验证/
├── 60_故障排查与经验/
├── 98_资料索引/
└── 99_待确认/
```

脚本只创建缺失的生成文件，默认不覆盖已有笔记。正式写入前先运行 `--create --dry-run` 展示将新建/覆盖的文件清单；使用 `--overwrite-generated` 前也必须人工检查差异。

随后阅读生成的 `00_总览/扫描清单.md` 和 `98_资料索引/资料清单.md`，补充真正与当前工程有关的模块关系、构建入口和接口说明。不要仅凭文件名推断具体引脚、供电、电平、外设实例或硬件状态。

### 3. 处理手册、原理图导出和引脚资料

只转换与当前工程或当前选板直接相关的 PDF、DOCX、PPTX、XLSX、HTML 等资料；不要批量转换整个资料盘。

1. 在 `98_资料索引/资料清单.md` 中选择资料，并记录版本、来源路径、用途和待确认项。
2. 优先使用已可访问的 `document-to-markdown` Skill。它依赖 Docker 或 Podman；先检查运行时，再征求用户许可拉取镜像或执行容器。
3. 可使用随附辅助脚本转换已明确选中的文件：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/convert_selected_documents.ps1 `
  -InputFile <资料1>, <资料2> `
  -OutputDirectory <PROJECT_ROOT>\Obsidian嵌入式知识库\98_资料索引\转换稿 `
  -ProjectRoot <PROJECT_ROOT>
```

转换稿是资料镜像，不是验证结论。转换失败时保留原资料索引，在 `99_待确认` 说明原因；不要伪造转换成功。

### 4. 蒸馏芯片和开发板资料

需要从手册、原理图、引脚图或 Wiki 制作板卡档案时，先读取 `references/board-distillation.md`。遵循“主档案 + 芯片 PinMux + 板级接口”三层结构：

```text
20_芯片与开发板/
├── <板卡名><芯片型号>开发板档案.md
├── <芯片型号>-芯片资源与PinMux速查.md
└── <板卡名>-板级引脚与接口.md
```

- 芯片级事实优先引用官方数据手册/参考手册。
- 板级连接优先引用官方 Wiki、用户手册、原理图和 BOM。
- 每条关键结论写明 `source_path`、版本、页码或章节；冲突进入“待确认与冲突”。
- 原理图缺失时，允许只创建主档案和芯片级笔记；不要编造板级引脚映射。
- 同一 MCU 的多块开发板共享一份芯片 PinMux 笔记，每块板保留独立板级接口笔记。

### 5. 连接工程与知识库

用 Obsidian `[[链接]]` 连接：

```text
项目总览
→ 工程结构 / 构建与配置
→ 芯片与开发板 / 外设模块
→ 原理图、PCB、BOM、手册索引
→ 验证记录 / 故障记录 / 待确认
```

每篇项目笔记的 YAML 至少使用：

```yaml
source_path: <项目相对路径或资料相对路径>
status: 草案
trust_level: L0
verification_scope: 未验证
```

只在存在构建日志、静态检查、上板记录或回归记录时提升相应范围的证据等级。

### 6. 验收与最终说明

完成后：

1. 检查所有生成 Markdown 可读取、YAML 可解析、内部 Wiki 链接无明显失效目标。
2. 对比原工程 Git 状态或文件清单，证明没有改动源工程。
3. 说明实际扫描的文件、创建的笔记、转换的资料、未转换原因、L0/L1/L2/L3 证据和未验证项。
4. 提供回退方式：删除整个新建 `Obsidian嵌入式知识库` 文件夹即可；不要影响原工程。

## 附带资源

- `scripts/build_project_inventory.py`：读取工程树，输出只读报告或创建不覆盖的知识库骨架。
- `scripts/convert_selected_documents.ps1`：通过 Docker 或 Podman 转换明确选中的资料。
- `references/vault-layout.md`：生成目录和笔记职责。
- `references/board-distillation.md`：板卡、芯片和 PinMux 蒸馏约束与模板。