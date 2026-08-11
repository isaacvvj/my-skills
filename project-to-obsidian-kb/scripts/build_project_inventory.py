#!/usr/bin/env python3
"""Create a read-only embedded-project inventory or a non-destructive Obsidian vault skeleton."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".vs", ".settings",
    "node_modules", ".venv", "venv", "__pycache__", "build", "debug", "release",
    "cmake-build-debug", "cmake-build-release", "dist", "out", "target",
    "Obsidian嵌入式知识库",
}

DOC_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".html", ".htm"}
HARDWARE_SUFFIXES = {".kicad_sch", ".kicad_pcb", ".sch", ".brd", ".pcbdoc", ".schdoc", ".bom", ".csv"}
SOURCE_SUFFIXES = {".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".s", ".S", ".py", ".ino", ".rs"}
CONFIG_SUFFIXES = {".ioc", ".syscfg", ".ld", ".sct", ".cfg", ".json", ".yaml", ".yml"}
BUILD_FILENAMES = {
    "cmakelists.txt", "makefile", "platformio.ini", "package.json", "west.yml",
    "build.ps1", "flash.ps1", "validate.ps1", "build.bat", "flash.bat",
}


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base = Path(current)
        for name in names:
            candidate = base / name
            if candidate.is_file():
                files.append(candidate)
    return sorted(files, key=lambda p: relative(p, root).lower())


def find_named(files: Iterable[Path], root: Path, names: set[str], limit: int = 80) -> list[str]:
    found = [relative(p, root) for p in files if p.name.lower() in names]
    return found[:limit]


def find_suffixes(files: Iterable[Path], root: Path, suffixes: set[str], limit: int = 200) -> list[str]:
    found = [relative(p, root) for p in files if p.suffix.lower() in suffixes]
    return found[:limit]


def detect_stack(files: list[Path], root: Path) -> list[dict[str, object]]:
    names = {p.name.lower() for p in files}
    paths = {relative(p, root).lower() for p in files}
    results: list[dict[str, object]] = []

    def add(name: str, evidence: list[str]) -> None:
        if evidence:
            results.append({"name": name, "evidence": evidence})

    add("STM32 / STM32CubeMX", [p for p in paths if p.endswith(".ioc")][:20])
    add("TI MSPM0 / SysConfig", [p for p in paths if p.endswith(".syscfg")][:20])
    add("PlatformIO", [p for p in paths if p.endswith("platformio.ini")][:20])
    add("CMake", [p for p in paths if p.endswith("cmakelists.txt")][:20])
    add("Arduino", [p for p in paths if p.endswith(".ino")][:20])
    add("Zephyr / west", [p for p in paths if p.endswith("west.yml") or "zephyr" in p][:20])
    add("ESP-IDF", [p for p in paths if p.endswith("idf_component.yml") or p.endswith("sdkconfig") or "sdkconfig." in p or "/managed_components/" in p][:20])
    add("K230 / CanMV", [p for p in paths if "k230" in p or "canmv" in p or p.endswith(".kmodel")][:20])
    add("KiCad", [p for p in paths if p.endswith(".kicad_sch") or p.endswith(".kicad_pcb")][:20])
    add("Altium Designer", [p for p in paths if p.endswith(".schdoc") or p.endswith(".pcbdoc")][:20])

    if not results:
        add("待人工确认", ["未找到可识别的工程标记；请检查根目录、构建文件和平台说明。"])
    return results


def summarize(root: Path) -> dict[str, object]:
    files = collect_files(root)
    suffix_count = Counter((p.suffix.lower() or "[无后缀]") for p in files)
    directories = sorted({relative(p.parent, root) for p in files if p.parent != root})
    documentation = find_suffixes(files, root, DOC_SUFFIXES)
    hardware = find_suffixes(files, root, HARDWARE_SUFFIXES)
    source = find_suffixes(files, root, SOURCE_SUFFIXES)
    configs = find_suffixes(files, root, CONFIG_SUFFIXES)
    markers = find_named(files, root, {"readme.md", "agents.md", ".任务上下文.md"})
    build_files = find_named(files, root, BUILD_FILENAMES)
    return {
        "generated_at": date.today().isoformat(),
        "project_root": str(root),
        "file_count": len(files),
        "directories": directories[:240],
        "suffix_count": dict(sorted(suffix_count.items())),
        "project_markers": markers,
        "build_files": build_files,
        "stack_candidates": detect_stack(files, root),
        "source_files": source,
        "configuration_files": configs,
        "hardware_files": hardware,
        "document_files": documentation,
    }


def bullet_list(items: Iterable[str], empty: str = "- 未发现；待确认。") -> str:
    values = list(items)
    return "\n".join(f"- `{x}`" for x in values) if values else empty


def stack_table(items: list[dict[str, object]]) -> str:
    rows = ["| 技术栈候选 | 文件证据 |", "|---|---|"]
    for item in items:
        evidence = "<br>".join(f"`{x}`" for x in item["evidence"])
        rows.append(f"| {item['name']} | {evidence} |")
    return "\n".join(rows)


def report_markdown(data: dict[str, object]) -> str:
    return f"""---
type: 工程只读扫描报告
status: 待确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 工程只读扫描报告

> 本报告仅根据目录名、文件名和扩展名生成；不读取源码语义，不代表构建、烧录、上板或硬件验证成功。

## 扫描范围

- 工程根目录：`{data['project_root']}`
- 文件数量：`{data['file_count']}`
- 默认排除：版本控制目录、依赖缓存、虚拟环境、常见构建输出和已有 `Obsidian嵌入式知识库`。

## 项目入口文件

{bullet_list(data['project_markers'])}

## 构建、烧录与验证入口候选

{bullet_list(data['build_files'])}

## 技术栈候选

{stack_table(data['stack_candidates'])}

## 硬件/EDA 文件候选

{bullet_list(data['hardware_files'])}

## 可转换资料候选

{bullet_list(data['document_files'])}

## 待确认

- 确认实际芯片型号、开发板版本、封装、供电、电平和调试接口。
- 阅读真实构建脚本、原理图、BOM 和手册后，再补充接口关系。
- 仅转换与当前工程直接相关的资料，不要批量转换整个资料目录。
"""


def write_generated(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def vault_files(data: dict[str, object]) -> dict[str, str]:
    today = data["generated_at"]
    stack = stack_table(data["stack_candidates"])
    return {
        "README.md": """# 项目 Obsidian 嵌入式知识库

> 本知识库由 `project-to-obsidian-kb` 基于原工程只读扫描创建。原工程保持不变；本目录保存索引、项目决策、资料来源、验证边界和故障经验。

- [[00_总览/项目总览|项目总览]]
- [[00_总览/扫描清单|扫描清单]]
- [[10_嵌入式工程/工程结构|工程结构]]
- [[10_嵌入式工程/构建烧录与配置|构建烧录与配置]]
- [[20_芯片与开发板/芯片与开发板索引|芯片与开发板索引]]
- [[98_资料索引/资料清单|资料清单]]
- [[99_待确认/待确认|待确认]]
""",
        "00_总览/项目总览.md": f"""---
type: 项目总览
status: 草案
trust_level: L0
source_path: .
created: {today}
verification_scope: 未验证
---

# 项目总览

> 本页仅关联原工程的扫描证据；需要阅读源码、构建脚本和硬件资料后再补充真实结论。

## 导航

- [[扫描清单]]
- [[../10_嵌入式工程/工程结构|工程结构]]
- [[../10_嵌入式工程/构建烧录与配置|构建烧录与配置]]
- [[../20_芯片与开发板/芯片与开发板索引|芯片与开发板索引]]
- [[../30_硬件模块与接口/硬件资料候选|硬件资料候选]]
- [[../50_项目记录与验证/验证状态|验证状态]]
- [[../98_资料索引/资料清单|资料清单]]
- [[../99_待确认/待确认|待确认]]

## 技术栈候选

{stack}

## 当前边界

- 原工程未被本 Skill 修改。
- 扫描结果不是构建或上板证据。
- 具体芯片、板卡、接口和验证状态均待结合原始资料确认。
""",
        "00_总览/扫描清单.md": report_markdown(data),
        "10_嵌入式工程/工程结构.md": f"""---
type: 工程结构索引
status: 草案
trust_level: L0
source_path: .
created: {today}
---

# 工程结构

## 目录候选

{bullet_list(data['directories'])}

## 源码文件候选

{bullet_list(data['source_files'])}

> 以上来自文件树。模块职责、任务调度、中断关系和公共接口需阅读源码后再填写。
""",
        "10_嵌入式工程/构建烧录与配置.md": f"""---
type: 构建烧录配置索引
status: 草案
trust_level: L0
source_path: .
created: {today}
verification_scope: 未构建
---

# 构建、烧录与配置

## 入口候选

{bullet_list(data['build_files'])}

## 配置文件候选

{bullet_list(data['configuration_files'])}

## 验证边界

- 未执行任何构建、烧录或目标板操作。
- 在确认项目 README 和脚本后，记录实际命令、产物路径、警告和失败原因。
""",
        "20_芯片与开发板/芯片与开发板索引.md": f"""---
type: 芯片与开发板索引
status: 待确认
trust_level: L0
source_path: .
created: {today}
---

# 芯片与开发板索引

## 扫描证据

{stack}

## 建档规则

- 只有从项目配置、BOM、原理图、手册或官方页面确认型号后，创建开发板主档案。
- 芯片 PinMux、板级接口和供电/调试信息分别建档并互相链接。
- 资料默认 L0；不要将扫描和 Markdown 转换写成上板验证。

参见 [[../98_资料索引/资料清单|资料清单]] 和 [[../99_待确认/待确认|待确认]]。
""",
        "30_硬件模块与接口/硬件资料候选.md": f"""---
type: 硬件资料候选
status: 待确认
trust_level: L0
source_path: .
created: {today}
---

# 硬件资料候选

## 原理图、PCB 与 BOM 候选

{bullet_list(data['hardware_files'])}

## 当前规则

- 先确认模块身份、版本、供电、电平、接口方向、协议、异常安全状态和资料来源。
- 原理图/BOM 缺失时，接口关系写“待确认”，不要按文件名猜测。
""",
        "50_项目记录与验证/验证状态.md": f"""---
type: 验证记录
status: 草案
trust_level: L0
source_path: .
created: {today}
verification_scope: 未执行
---

# 验证状态

| 范围 | 当前证据 | 结论 |
|---|---|---|
| 资料参考 | 文件树扫描 | L0：仅存在候选资料 |
| 本机构建 | 未执行 | 待确认 |
| 烧录 | 未执行 | 待确认 |
| 目标板 | 未执行 | 待确认 |
| 整机/车辆 | 未执行 | 待确认 |

> 后续记录实际命令、日志、板卡版本、接线、测试条件和结果；不要跨范围升级结论。
""",
        "60_故障排查与经验/README.md": """# 故障排查与经验

> 仅记录已经发生、可复现且对后续项目有帮助的问题。当前未从文件树推断任何故障。
""",
        "98_资料索引/资料清单.md": f"""---
type: 资料索引
status: 草案
trust_level: L0
source_path: .
created: {today}
---

# 资料清单

## 可转换资料候选

{bullet_list(data['document_files'])}

## 使用方式

1. 确认资料与当前项目、目标芯片或开发板直接相关。
2. 记录来源、版本、用途和相对路径。
3. 仅转换被选中的资料到 `转换稿/`；原始文件仍保留在原工程或资料目录。
4. 基于转换稿和原始资料蒸馏板卡/芯片档案，关键结论标注页码或章节。
""",
        "99_待确认/待确认.md": """---
type: 待确认清单
status: 使用中
trust_level: L0
verification_scope: 未验证
---

# 待确认

- 目标 MCU 与实际开发板型号、版本、封装。
- 构建、烧录、调试工具链和入口命令。
- 供电、电平、引脚复用、板级占用和接口方向。
- 资料版本、原理图/BOM 完整性和冲突项。
- 本机构建、目标板和整机功能的实际验证记录。
""",
    }


def create_vault(root: Path, output: Path, data: dict[str, object], overwrite: bool, dry_run: bool = False) -> list[str]:
    try:
        output.relative_to(root)
    except ValueError as error:
        raise ValueError("输出目录必须位于 PROJECT_ROOT 内，避免误写到外部位置。") from error
    if output == root:
        raise ValueError("输出目录不能与 PROJECT_ROOT 相同。")

    written: list[str] = []
    for rel_path, content in vault_files(data).items():
        target = output / rel_path
        if dry_run:
            action = "覆盖" if target.exists() else "新建"
            written.append(f"[{action}] {rel_path}")
            continue
        if write_generated(target, content, overwrite):
            written.append(relative(target, output))
    inventory_path = output / "00_总览" / "inventory.json"
    if dry_run:
        action = "覆盖" if inventory_path.exists() else "新建"
        written.append(f"[{action}] {relative(inventory_path, output)}")
    elif not inventory_path.exists() or overwrite:
        inventory_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(relative(inventory_path, output))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="当前工程根目录；默认当前目录。")
    parser.add_argument("--report", help="只读扫描报告输出路径；不创建知识库。")
    parser.add_argument("--create", action="store_true", help="创建项目内的 Obsidian 知识库骨架。")
    parser.add_argument("--output", help="知识库输出目录；默认 PROJECT_ROOT/Obsidian嵌入式知识库。")
    parser.add_argument("--overwrite-generated", action="store_true", help="覆盖已存在的生成笔记；使用前先人工检查差异。")
    parser.add_argument("--dry-run", action="store_true", help="只列出将新建/覆盖的文件，不写入任何内容；需与 --create 一起使用。")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        parser.error(f"PROJECT_ROOT 不存在或不是目录：{root}")
    if not args.report and not args.create:
        parser.error("至少指定 --report 或 --create。")
    if args.dry_run and not args.create:
        parser.error("--dry-run 需要与 --create 一起使用。")

    data = summarize(root)
    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_markdown(data), encoding="utf-8", newline="\n")
        print(f"[OK] 只读扫描报告：{report_path}")

    if args.create:
        output = Path(args.output).resolve() if args.output else root / "Obsidian嵌入式知识库"
        if args.dry_run:
            plan = create_vault(root, output, data, args.overwrite_generated, dry_run=True)
            print(f"[计划] 输出目录：{output}")
            print(f"[计划] 将新建/覆盖文件数量：{len(plan)}")
            for item in plan:
                print(f"  - {item}")
            return 0
        written = create_vault(root, output, data, args.overwrite_generated)
        print(f"[OK] 知识库目录：{output}")
        print(f"[OK] 新建/更新文件数量：{len(written)}")
        for item in written:
            print(f"  + {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())