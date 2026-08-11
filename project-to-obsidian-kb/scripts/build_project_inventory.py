#!/usr/bin/env python3
"""Inventory an embedded project and create a non-destructive linked Obsidian knowledge base."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
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
SOURCE_SUFFIXES = {".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".s", ".py", ".ino", ".rs"}
HEADER_SUFFIXES = {".h", ".hpp"}
IMPLEMENTATION_SUFFIXES = {".c", ".cpp", ".cxx", ".cc", ".py", ".ino", ".rs"}
CONFIG_SUFFIXES = {".ioc", ".syscfg", ".ld", ".sct", ".cfg", ".json", ".yaml", ".yml"}
BUILD_FILENAMES = {
    "cmakelists.txt", "makefile", "platformio.ini", "package.json", "west.yml",
    "build.ps1", "flash.ps1", "validate.ps1", "build.bat", "flash.bat",
}
PROTECTED_PATH_PARTS = {
    "drivers", "startup", "middleware", "middlewares", "cmsis", "hal", "ll", "sdk",
    "third_party", "third-party", "vendor", "generated", "targetconfigs",
}
ENTRY_FILENAMES = {"main.c", "main.cpp", "main.py", "app_main.c", "app_main.cpp"}


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            pass
    return path.read_text(encoding="utf-8", errors="replace")


def collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        base = Path(current)
        files.extend(base / name for name in names if (base / name).is_file())
    return sorted(files, key=lambda path: relative(path, root).lower())


def find_named(files: Iterable[Path], root: Path, names: set[str], limit: int = 80) -> list[str]:
    return [relative(path, root) for path in files if path.name.lower() in names][:limit]


def find_suffixes(files: Iterable[Path], root: Path, suffixes: set[str], limit: int = 240) -> list[str]:
    return [relative(path, root) for path in files if path.suffix.lower() in suffixes][:limit]


def detect_stack(files: list[Path], root: Path) -> list[dict[str, object]]:
    paths = {relative(path, root).lower() for path in files}
    results: list[dict[str, object]] = []

    def add(name: str, evidence: list[str]) -> None:
        if evidence:
            results.append({"name": name, "evidence": evidence[:20]})

    add("STM32 / STM32CubeMX", [path for path in paths if path.endswith(".ioc")])
    add("TI MSPM0 / SysConfig", [path for path in paths if path.endswith(".syscfg")])
    add("PlatformIO", [path for path in paths if path.endswith("platformio.ini")])
    add("CMake", [path for path in paths if path.endswith("cmakelists.txt")])
    add("Arduino", [path for path in paths if path.endswith(".ino")])
    add("Zephyr / west", [path for path in paths if path.endswith("west.yml") or "zephyr" in path])
    add("ESP-IDF", [path for path in paths if path.endswith("idf_component.yml") or "/components/" in path])
    add("K230 / CanMV", [path for path in paths if "k230" in path or "canmv" in path or path.endswith(".kmodel")])
    add("KiCad", [path for path in paths if path.endswith(".kicad_sch") or path.endswith(".kicad_pcb")])
    add("Altium Designer", [path for path in paths if path.endswith(".schdoc") or path.endswith(".pcbdoc")])
    if not results:
        results.append({"name": "待人工确认", "evidence": ["未找到可识别的工程标记；请检查根目录、构建文件和平台说明。"]})
    return results


def classify_module(stem: str, paths: list[Path], root: Path) -> tuple[str, str]:
    lowered_stem = stem.lower()
    lowered_parts = {part.lower() for path in paths for part in path.parts}
    names = {path.name.lower() for path in paths}
    if names & ENTRY_FILENAMES:
        return "应用入口/项目编排", "项目专用：供 AI 理解控制流，不建议直接复制为独立模块"
    if lowered_parts & PROTECTED_PATH_PARTS:
        return "厂商或自动生成依赖", "仅索引：不要擅自改动或抽离；通过项目配置和官方资料确认边界"
    keyword_map = {
        "控制算法": ("pid", "filter", "kalman", "control", "trajectory"),
        "执行器控制": ("motor", "pwm", "servo", "stepper", "encoder", "gimbal"),
        "通信与协议": ("uart", "usart", "i2c", "spi", "can", "protocol", "frame", "ring", "serial"),
        "传感器与采样": ("adc", "imu", "sensor", "huidu", "gray", "camera", "vision"),
        "显示与人机交互": ("oled", "lcd", "display", "key", "button", "buzzer"),
        "系统服务": ("timer", "tick", "delay", "watchdog", "freertos", "queue", "task"),
    }
    for module_type, keywords in keyword_map.items():
        if any(keyword in lowered_stem for keyword in keywords):
            return module_type, "候选可复用模块：先阅读依赖、配置和调用方，再独立构建/上板验证"
    return "项目功能模块", "候选可复用模块：需人工确认职责、外部依赖和最小运行条件"


def parse_includes(text: str) -> list[str]:
    values = re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, flags=re.MULTILINE)
    return sorted(dict.fromkeys(values))[:80]


def parse_public_api(text: str) -> list[str]:
    results: list[str] = []
    joined = re.sub(r'\\\n', ' ', text)
    pattern = re.compile(
        r'^\s*(?:extern\s+)?(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*;',
        flags=re.MULTILINE,
    )
    for match in pattern.finditer(joined):
        name = match.group(1)
        if name in {"if", "while", "for", "switch"}:
            continue
        signature = re.sub(r'\s+', ' ', match.group(0).strip())
        results.append(signature)
    return list(dict.fromkeys(results))[:60]


def parse_defined_functions(text: str) -> list[str]:
    pattern = re.compile(
        r'^\s*(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{',
        flags=re.MULTILINE,
    )
    values = [match.group(1) for match in pattern.finditer(text)]
    return list(dict.fromkeys(values))[:80]


def safe_note_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|#\[\]]', '_', value).strip('. ')
    return cleaned or "未命名模块"


def detect_modules(files: list[Path], root: Path) -> list[dict[str, object]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        if path.suffix.lower() in SOURCE_SUFFIXES:
            grouped[path.stem.lower()].append(path)

    modules: list[dict[str, object]] = []
    for stem, paths in sorted(grouped.items()):
        paths = sorted(paths, key=lambda item: relative(item, root).lower())
        module_type, reuse_status = classify_module(stem, paths, root)
        header_paths = [path for path in paths if path.suffix.lower() in HEADER_SUFFIXES]
        implementation_paths = [path for path in paths if path.suffix.lower() in IMPLEMENTATION_SUFFIXES]
        includes: list[str] = []
        api: list[str] = []
        defined: list[str] = []
        readable_paths = [path for path in paths if path.stat().st_size <= 512 * 1024]
        for path in readable_paths:
            content = read_text(path)
            includes.extend(parse_includes(content))
            if path in header_paths:
                api.extend(parse_public_api(content))
            if path in implementation_paths:
                defined.extend(parse_defined_functions(content))
        modules.append({
            "name": stem,
            "note_name": safe_note_name(stem),
            "module_type": module_type,
            "reuse_status": reuse_status,
            "source_files": [relative(path, root) for path in paths],
            "header_files": [relative(path, root) for path in header_paths],
            "implementation_files": [relative(path, root) for path in implementation_paths],
            "direct_includes": sorted(dict.fromkeys(includes))[:80],
            "public_api": list(dict.fromkeys(api))[:60],
            "defined_functions": list(dict.fromkeys(defined))[:80],
            "source_sha256": {relative(path, root): file_hash(path) for path in paths},
        })
    return modules


def summarize(root: Path) -> dict[str, object]:
    files = collect_files(root)
    suffix_count = Counter((path.suffix.lower() or "[无后缀]") for path in files)
    return {
        "generated_at": date.today().isoformat(),
        "project_root": str(root),
        "file_count": len(files),
        "directories": sorted({relative(path.parent, root) for path in files if path.parent != root})[:240],
        "suffix_count": dict(sorted(suffix_count.items())),
        "project_markers": find_named(files, root, {"readme.md", "agents.md", ".任务上下文.md"}),
        "build_files": find_named(files, root, BUILD_FILENAMES),
        "stack_candidates": detect_stack(files, root),
        "source_files": find_suffixes(files, root, SOURCE_SUFFIXES),
        "configuration_files": find_suffixes(files, root, CONFIG_SUFFIXES),
        "hardware_files": find_suffixes(files, root, HARDWARE_SUFFIXES),
        "document_files": find_suffixes(files, root, DOC_SUFFIXES),
        "modules": detect_modules(files, root),
    }


def bullet_list(items: Iterable[str], empty: str = "- 未发现；待确认。") -> str:
    values = list(items)
    return "\n".join(f"- `{item}`" for item in values) if values else empty


def stack_table(items: list[dict[str, object]]) -> str:
    rows = ["| 技术栈候选 | 文件证据 |", "|---|---|"]
    for item in items:
        evidence = "<br>".join(f"`{value}`" for value in item["evidence"])
        rows.append(f"| {item['name']} | {evidence} |")
    return "\n".join(rows)


def module_table(modules: list[dict[str, object]]) -> str:
    rows = ["| 模块 | 自动分类 | 复用边界 | 源文件 |", "|---|---|---|"]
    for module in modules:
        files = "<br>".join(f"`{item}`" for item in module["source_files"])
        rows.append(f"| [[../60_可复用代码与工程模板/代码模块/{module['note_name']}代码模块|{module['name']}]] | {module['module_type']} | {module['reuse_status']} | {files} |")
    return "\n".join(rows) if len(rows) > 2 else "- 未发现可识别的源码模块；待确认。"


def report_markdown(data: dict[str, object]) -> str:
    return f"""---
type: 工程只读扫描报告
status: 待确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 工程只读扫描报告

> 本报告根据文件树和有限源码结构提取生成；自动模块分类、函数列表和依赖仅作 AI 阅读入口，不代表完成解耦、独立构建或硬件验证。

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

## 自动识别的代码模块

{module_table(data['modules'])}

## 硬件/EDA 文件候选

{bullet_list(data['hardware_files'])}

## 可转换资料候选

{bullet_list(data['document_files'])}

## 待确认

- 自动模块边界按同名源文件/头文件和文件名启发式生成；阅读源码、调用方和构建配置后再确认。
- 仅转换与当前工程直接相关的资料，不要批量转换整个资料目录。
- 只有独立构建、目标板验证或稳定复用记录才能提升可信等级。
"""


def write_generated(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def markdown_source_link(source: Path, note_path: Path) -> str:
    return os.path.relpath(source, start=note_path.parent).replace("\\", "/")


def module_note(module: dict[str, object], root: Path, note_path: Path, generated_at: str) -> str:
    source_files = [root / value for value in module["source_files"]]
    source_links = "\n".join(
        f"- [{relative(source, root)}]({markdown_source_link(source, note_path)})" for source in source_files
    )
    api = "\n".join(f"- `{item}`" for item in module["public_api"]) or "- 未从头文件解析到函数声明；先阅读源文件和调用方。"
    defined = "\n".join(f"- `{item}`" for item in module["defined_functions"]) or "- 未自动解析到函数定义；待人工确认。"
    includes = "\n".join(f"- `{item}`" for item in module["direct_includes"]) or "- 未解析到显式 include，或文件未读取。"
    source_reading = "\n- 默认不复制完整源码。AI 应按上方相对链接读取原工程文件；跨环境交接时应连同原工程交付，或手动摘录必要片段并标注来源和 SHA256。"
    return f"""---
type: 代码模块
status: 自动盘点，待人工确认
trust_level: L0
module_type: {module['module_type']}
source_path: {module['source_files'][0] if module['source_files'] else '.'}
source_files:
{chr(10).join('  - ' + item for item in module['source_files'])}
interfaces: [{', '.join(module['defined_functions'][:12])}]
verified_compile: false
verified_hardware: false
reuse_status: {module['reuse_status']}
created: {generated_at}
---

# {module['name']} 代码模块

> 本页是从现有工程提取的**参照模块卡**，不是已经独立构建的模板。保留原工程为黄金基线；抽取或修改前先读源文件、调用方、构建配置和硬件约束。

## 功能与复用边界

- 自动分类：{module['module_type']}
- 当前建议：{module['reuse_status']}
- 不要因文件名、源码摘录或本页存在就假定接口、引脚和硬件行为已验证。

## 原工程文件

{source_links}

## 对外 API 候选（来自头文件）

{api}

## 源文件中函数定义候选

{defined}

## 直接 include 依赖

{includes}

## AI 阅读与复用顺序

1. 先读本页列出的头文件，确认公共 API、数据结构和宏。
2. 再读实现文件和调用方，确认初始化顺序、中断/任务上下文、全局变量和错误路径。
3. 检查 `.ioc`、`.syscfg`、构建脚本、PinMux、原理图和 BSP/HAL 依赖；不要只复制单个 `.c/.h` 文件。
4. 若要迁移，先复制到新工程的 `App/` 或 `BSP/` 边界，补齐最小依赖并独立构建；上板前保持执行器安全状态。
5. 在本页补充实际功能、最小依赖、移植限制、构建/上板记录后，才可提升可信等级。

## 源码可读性入口
{source_reading}

## 待人工补充

- 实际功能、输入/输出、单位、时序和异常安全状态；
- 最小依赖与禁止耦合的项目专用部分；
- 独立构建、目标板和整机验证记录；
- 是否应沉淀为真正的模板仓库模块。
"""



def vault_files(data: dict[str, object]) -> dict[str, str]:
    today = data["generated_at"]
    stack = stack_table(data["stack_candidates"])
    modules = module_table(data["modules"])
    return {
        "README.md": """# 项目 Obsidian 嵌入式知识库

> 本知识库由 `project-to-obsidian-kb` 基于原工程只读盘点创建。原工程保持不变；本目录保存链接、模块参照、资料来源、验证边界和故障经验。

- [[00_总览/项目总览|项目总览]]
- [[00_总览/扫描清单|扫描清单]]
- [[10_嵌入式工程/工程结构|工程结构]]
- [[10_嵌入式工程/代码模块索引|代码模块索引]]
- [[60_可复用代码与工程模板/README|可复用模块参照]]
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

> 本页关联原工程扫描证据和模块参照。需要阅读源码、构建脚本和硬件资料后再补充真实结论。

## 导航

- [[扫描清单]]
- [[../10_嵌入式工程/工程结构|工程结构]]
- [[../10_嵌入式工程/代码模块索引|代码模块索引]]
- [[../10_嵌入式工程/构建烧录与配置|构建烧录与配置]]
- [[../60_可复用代码与工程模板/README|可复用模块参照]]
- [[../20_芯片与开发板/芯片与开发板索引|芯片与开发板索引]]
- [[../98_资料索引/资料清单|资料清单]]
- [[../99_待确认/待确认|待确认]]

## 技术栈候选

{stack}

## 当前边界

- 原工程未被本 Skill 修改。
- 模块卡仅提供 AI 阅读与迁移入口，不证明模块已解耦或已验证。
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

> 以上来自文件树。模块职责、任务调度、中断关系和公共接口需结合 [[代码模块索引]]、构建配置和源文件确认。
""",
        "10_嵌入式工程/代码模块索引.md": f"""---
type: 工程代码模块索引
status: 自动盘点，待人工确认
trust_level: L0
source_path: .
created: {today}
---

# 代码模块索引

> 此索引把现有工程按同名源文件/头文件聚合为 AI 可阅读的参照模块。它不会移动源码，也不表示已经完成物理拆分或独立构建。

## 模块地图

{modules}

## 使用方式

1. 先从模块卡进入，读取其原工程相对链接、API 候选和 include 依赖。
2. 抽取可复用代码时，先保留当前工程黄金基线；在新工程副本中单独构建，不直接剪切原项目文件。
3. 入口文件、自动生成文件、SDK 和厂商库通常只用于理解依赖边界，禁止直接当成通用模块复制。

相关入口：[[../60_可复用代码与工程模板/README|可复用模块参照]]、[[构建烧录与配置]]、[[../50_项目记录与验证/验证状态|验证状态]]。
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
| 资料参考 | 文件树和源码结构扫描 | L0：仅存在候选资料/模块 |
| 本机构建 | 未执行 | 待确认 |
| 烧录 | 未执行 | 待确认 |
| 目标板 | 未执行 | 待确认 |
| 整机/车辆 | 未执行 | 待确认 |

> 后续记录实际命令、日志、板卡版本、接线、测试条件和结果；不要跨范围升级结论。
""",
        "60_可复用代码与工程模板/README.md": """# 可复用代码与工程模板参照

> 这里不是从原工程移动出来的独立模板库，而是面向 AI 阅读和后续抽取的模块参照层。每个模块卡都链接回原工程；先确认依赖、最小构建条件和验证记录，再在新工程副本中复用。

- [[代码模块/README|代码模块列表]]
- [[工程参考|工程参考与抽取规则]]
""",
        "60_可复用代码与工程模板/代码模块/README.md": """# 代码模块列表

> 模块页由工程扫描生成。它们默认是 L0 参照，不代表已成为独立模板。

请从 [[../../10_嵌入式工程/代码模块索引|代码模块索引]] 进入对应模块卡。
""",
        "60_可复用代码与工程模板/工程参考.md": """---
type: 工程参照与模块抽取规则
status: 使用中
trust_level: L0
---

# 工程参照与模块抽取规则

1. 原工程是黄金基线，先读模块卡、头文件、实现、调用方和构建配置。
2. 不从原工程直接剪切或删除代码；复制到新工程/模板候选目录后再解耦。
3. 拆分时明确公共 API、数据所有权、中断/任务上下文、HAL/BSP 依赖、配置依赖和硬件安全状态。
4. 先完成独立构建，再进行最小板级验证；分别记录 L1、L2 和 L3 证据。
5. 入口文件、厂商 SDK、启动文件、链接脚本、`.ioc`、`.syscfg` 和自动生成文件默认不作为可复用模块自动迁移。
""",
        "80_故障排查与经验/README.md": """# 故障排查与经验

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

- 自动模块边界、实际功能和可复用范围。
- 目标 MCU 与实际开发板型号、版本、封装。
- 构建、烧录、调试工具链和入口命令。
- 供电、电平、引脚复用、板级占用和接口方向。
- 资料版本、原理图/BOM 完整性和冲突项。
- 模块独立构建、目标板和整机功能的实际验证记录。
""",
    }


def create_vault(root: Path, output: Path, data: dict[str, object], overwrite: bool) -> list[str]:
    try:
        output.relative_to(root)
    except ValueError as error:
        raise ValueError("输出目录必须位于 PROJECT_ROOT 内，避免误写到外部位置。") from error
    if output == root:
        raise ValueError("输出目录不能与 PROJECT_ROOT 相同。")

    written: list[str] = []
    for rel_path, content in vault_files(data).items():
        target = output / rel_path
        if write_generated(target, content, overwrite):
            written.append(relative(target, output))

    module_root = output / "60_可复用代码与工程模板" / "代码模块"
    for module in data["modules"]:
        note_path = module_root / f"{module['note_name']}代码模块.md"
        content = module_note(module, root, note_path, data["generated_at"])
        if write_generated(note_path, content, overwrite):
            written.append(relative(note_path, output))

    inventory_path = output / "00_总览" / "inventory.json"
    if not inventory_path.exists() or overwrite:
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(relative(inventory_path, output))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="当前工程根目录；默认当前目录。")
    parser.add_argument("--report", help="只读扫描报告输出路径；不创建知识库。")
    parser.add_argument("--create", action="store_true", help="创建项目内的 Obsidian 知识库骨架和模块卡。")
    parser.add_argument("--output", help="知识库输出目录；默认 PROJECT_ROOT/Obsidian嵌入式知识库。")
    parser.add_argument("--overwrite-generated", action="store_true", help="覆盖已存在的生成笔记；使用前先人工检查差异。")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        parser.error(f"PROJECT_ROOT 不存在或不是目录：{root}")
    if not args.report and not args.create:
        parser.error("至少指定 --report 或 --create。")

    data = summarize(root)
    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_markdown(data), encoding="utf-8", newline="\n")
        print(f"[OK] 只读扫描报告：{report_path}")

    if args.create:
        output = Path(args.output).resolve() if args.output else root / "Obsidian嵌入式知识库"
        written = create_vault(root, output, data, args.overwrite_generated)
        print(f"[OK] 知识库目录：{output}")
        print(f"[OK] 识别模块数量：{len(data['modules'])}")
        print(f"[OK] 新建/更新文件数量：{len(written)}")
        for item in written:
            print(f"  + {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())