#!/usr/bin/env python3
"""Inventory an embedded project and create a linked engineering-library plus Obsidian-knowledge-base pair."""
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
    "Obsidian嵌入式知识库", "嵌入式工程库",
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
HARDWARE_DOC_KEYWORDS = ("datasheet", "data-sheet", "reference", "manual", "user-guide", "schematic", "pinout", "pin-mux", "hardware", "board", "mcu", "芯片", "开发板", "数据手册", "参考手册", "用户手册", "原理图", "引脚", "硬件")


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


def classify_module(stem: str, paths: list[Path]) -> tuple[str, str]:
    lowered_stem = stem.lower()
    lowered_parts = {part.lower() for path in paths for part in path.parts}
    names = {path.name.lower() for path in paths}
    if names & ENTRY_FILENAMES:
        return "应用入口/项目编排", "仅供参照：用于理解控制流，不自动抽取"
    if lowered_parts & PROTECTED_PATH_PARTS:
        return "厂商或自动生成依赖", "仅索引：禁止擅自拆分、复制或修改"
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
            return module_type, "候选模块：先确认依赖并独立构建后再进入模板库"
    return "项目功能模块", "候选模块：职责和最小依赖待人工确认"


def parse_includes(text: str) -> list[str]:
    values = re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, flags=re.MULTILINE)
    return sorted(dict.fromkeys(values))[:80]


def parse_public_api(text: str) -> list[str]:
    results: list[str] = []
    joined = re.sub(r'\\\n', ' ', text)
    pattern = re.compile(r'^\s*(?:extern\s+)?(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*;', re.MULTILINE)
    for match in pattern.finditer(joined):
        if match.group(1) not in {"if", "while", "for", "switch"}:
            results.append(re.sub(r'\s+', ' ', match.group(0).strip()))
    return list(dict.fromkeys(results))[:60]


def parse_defined_functions(text: str) -> list[str]:
    pattern = re.compile(r'^\s*(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{', re.MULTILINE)
    return list(dict.fromkeys(match.group(1) for match in pattern.finditer(text)))[:80]


def safe_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|#\[\]]', '_', value).strip('. ')
    return cleaned or "未命名工程"


def detect_modules(files: list[Path], root: Path) -> list[dict[str, object]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        if path.suffix.lower() in SOURCE_SUFFIXES:
            grouped[path.stem.lower()].append(path)
    modules: list[dict[str, object]] = []
    for stem, paths in sorted(grouped.items()):
        paths = sorted(paths, key=lambda path: relative(path, root).lower())
        module_type, reuse_status = classify_module(stem, paths)
        headers = [path for path in paths if path.suffix.lower() in HEADER_SUFFIXES]
        implementations = [path for path in paths if path.suffix.lower() in IMPLEMENTATION_SUFFIXES]
        includes: list[str] = []
        api: list[str] = []
        functions: list[str] = []
        for path in paths:
            if path.stat().st_size > 512 * 1024:
                continue
            content = read_text(path)
            includes.extend(parse_includes(content))
            if path in headers:
                api.extend(parse_public_api(content))
            if path in implementations:
                functions.extend(parse_defined_functions(content))
        modules.append({
            "name": stem,
            "module_type": module_type,
            "reuse_status": reuse_status,
            "source_files": [relative(path, root) for path in paths],
            "header_files": [relative(path, root) for path in headers],
            "implementation_files": [relative(path, root) for path in implementations],
            "direct_includes": sorted(dict.fromkeys(includes))[:80],
            "public_api": list(dict.fromkeys(api))[:60],
            "defined_functions": list(dict.fromkeys(functions))[:80],
            "source_sha256": {relative(path, root): file_hash(path) for path in paths},
        })
    return modules


def detect_hardware_document_candidates(files: list[Path], root: Path) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for path in files:
        rel = relative(path, root)
        lowered = rel.lower()
        if path.suffix.lower() in HARDWARE_SUFFIXES:
            candidates.append({"path": rel, "kind": "原理图/PCB/BOM", "priority": "高", "reason": "EDA 或 BOM 文件"})
            continue
        if path.suffix.lower() not in DOC_SUFFIXES:
            continue
        keyword_match = any(keyword in lowered for keyword in HARDWARE_DOC_KEYWORDS)
        hardware_path = any(part in lowered for part in ("hardware", "board", "schematic", "docs", "资料", "硬件", "原理图"))
        if keyword_match or hardware_path:
            priority = "高" if keyword_match else "中"
            reason = "文件名/路径包含硬件资料特征" if keyword_match else "位于疑似硬件资料路径，需读取正文确认"
            candidates.append({"path": rel, "kind": "可转换硬件资料", "priority": priority, "reason": reason})
    return candidates


def hardware_document_table(candidates: list[dict[str, str]]) -> str:
    if not candidates:
        return "- 未发现可主动蒸馏的硬件资料；待确认。"
    rows = ["| 资料 | 类型 | 优先级 | 自动判定依据 |", "|---|---|---|---|"]
    for item in candidates:
        rows.append(f"| `{item['path']}` | {item['kind']} | {item['priority']} | {item['reason']} |")
    return "\\n".join(rows)

def summarize(root: Path) -> dict[str, object]:
    files = collect_files(root)
    return {
        "generated_at": date.today().isoformat(),
        "project_name": root.name,
        "project_root": str(root),
        "file_count": len(files),
        "directories": sorted({relative(path.parent, root) for path in files if path.parent != root})[:240],
        "suffix_count": dict(sorted(Counter((path.suffix.lower() or "[无后缀]") for path in files).items())),
        "project_markers": find_named(files, root, {"readme.md", "agents.md", ".任务上下文.md"}),
        "build_files": find_named(files, root, BUILD_FILENAMES),
        "stack_candidates": detect_stack(files, root),
        "source_files": find_suffixes(files, root, SOURCE_SUFFIXES),
        "configuration_files": find_suffixes(files, root, CONFIG_SUFFIXES),
        "hardware_files": find_suffixes(files, root, HARDWARE_SUFFIXES),
        "document_files": find_suffixes(files, root, DOC_SUFFIXES),
        "hardware_document_candidates": detect_hardware_document_candidates(files, root),
        "modules": detect_modules(files, root),
    }


def bullet_list(items: Iterable[str], empty: str = "- 未发现；待确认。") -> str:
    values = list(items)
    return "\n".join(f"- `{item}`" for item in values) if values else empty


def stack_table(items: list[dict[str, object]]) -> str:
    rows = ["| 技术栈候选 | 文件证据 |", "|---|---|"]
    for item in items:
        rows.append(f"| {item['name']} | {'<br>'.join('`' + value + '`' for value in item['evidence'])} |")
    return "\n".join(rows)


def source_link(root: Path, note_path: Path, rel_path: str) -> str:
    return os.path.relpath(root / rel_path, start=note_path.parent).replace("\\", "/")


def module_table(data: dict[str, object], root: Path, note_path: Path) -> str:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for module in data["modules"]:
        groups[module["module_type"]].append(module)
    chunks: list[str] = []
    for module_type in sorted(groups):
        chunks.extend([f"## {module_type}", "", "| 模块候选 | 原工程文件 | API/函数候选 | 当前复用边界 |", "|---|---|---|---|"])
        for module in groups[module_type]:
            file_links = "<br>".join(
                f"[{rel}]({source_link(root, note_path, rel)})" for rel in module["source_files"]
            )
            api_names = module["defined_functions"][:5] or ["待确认"]
            chunks.append(f"| `{module['name']}` | {file_links} | {', '.join('`' + name + '`' for name in api_names)} | {module['reuse_status']} |")
        chunks.append("")
    return "\n".join(chunks) if chunks else "- 未发现可识别源码模块；待确认。"


def report_markdown(data: dict[str, object]) -> str:
    return f"""---
type: 工程只读扫描报告
status: 待确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 工程只读扫描报告

> 此报告仅根据工程文件树和有限源码结构提取生成。模块判断用于建立阅读入口，不代表解耦完成、独立构建或硬件验证。

- 工程根目录：`{data['project_root']}`
- 文件数量：`{data['file_count']}`

## 项目入口文件

{bullet_list(data['project_markers'])}

## 构建、烧录与验证入口候选

{bullet_list(data['build_files'])}

## 技术栈候选

{stack_table(data['stack_candidates'])}

## 模块候选（聚合清单）

| 模块 | 分类 | 源文件 | 复用边界 |
|---|---|---|---|
{chr(10).join('| `' + item['name'] + '` | ' + item['module_type'] + ' | ' + '<br>'.join('`' + path + '`' for path in item['source_files']) + ' | ' + item['reuse_status'] + ' |' for item in data['modules'])}

## 硬件与资料候选

### 原理图、PCB、BOM

{bullet_list(data['hardware_files'])}

### 可转换资料

{bullet_list(data['document_files'])}

### 主动蒸馏候选

{hardware_document_table(data['hardware_document_candidates'])}

## 待确认

- 自动识别的模块边界、函数关系、全局变量、中断/RTOS 上下文和最小依赖；
- 芯片、板卡、PinMux、供电、电平和硬件验证状态；
- 是否将某个候选模块正式抽取到工程库模板候选。
"""


def write_generated(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def engineering_library_files(data: dict[str, object]) -> dict[str, str]:
    project_key = safe_name(data["project_name"])
    return {
        "README.md": f"""# 嵌入式工程库

> 本工程库与 `Obsidian嵌入式知识库` 分离：代码继续保留在原工程中；这里保存工程参照清单、模块候选清单和后续抽取契约。不要因自动识别而直接移动或复制原工程代码。

- 工程参照：`工程参照/{project_key}/工程清单.md`
- 模块机器清单：`工程参照/{project_key}/模块索引.json`
- 模板候选规则：`模板候选/README.md`
""",
        f"工程参照/{project_key}/工程清单.md": f"""---
type: 工程参照
status: 自动扫描，待人工确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# {data['project_name']} 工程参照

> 原工程是唯一黄金基线。此工程库不自动复制源码；通过同目录的 `模块索引.json` 记录模块候选、API、依赖和源文件 SHA256。

## 工程入口

{bullet_list(data['project_markers'])}

## 构建与配置入口

{bullet_list(data['build_files'])}

## 模块候选

- 数量：{len(data['modules'])}
- 详情：`模块索引.json`

## 抽取到模板候选前

1. 在原工程中阅读头文件、实现、调用方、构建配置和硬件约束；
2. 复制到新工程/模板候选副本中，不要剪切黄金基线；
3. 定义最小 API 和依赖，完成独立构建后再记录 L1；
4. 对硬件模块完成目标板验证后再记录 L2。
""",
        f"工程参照/{project_key}/模块索引.json": json.dumps(data["modules"], ensure_ascii=False, indent=2),
        "模板候选/README.md": """# 模板候选

> 此目录初始不放自动复制的代码。只有人工确认模块边界、最小依赖和迁移计划后，才从原工程复制到新的候选工程中构建验证。

禁止直接剪切原工程代码；原工程保持为可回退的黄金基线。
""",
    }


def knowledge_files(data: dict[str, object], root: Path, library_name: str) -> dict[str, str]:
    project_key = safe_name(data["project_name"])
    library_project_rel = f"../{library_name}/工程参照/{project_key}/工程清单.md"
    hardware_docs = hardware_document_table(data["hardware_document_candidates"])
    return {
        "README.md": """# 项目 Obsidian 嵌入式知识库

> 本 Vault 只保存项目导航、资料、决策、验证与经验；不保存完整源码。真实代码保留在原工程，模块候选和抽取契约位于相邻的 `嵌入式工程库`。

- [[00-首页与导航/项目导航|项目导航]]
- [[00-首页与导航/工程库导航|工程库导航]]
- [[00-首页与导航/模块导航|模块导航]]
- [[60-可复用代码与工程模板/可复用模块候选|可复用模块候选]]
- [[80-项目与实验记录/项目总览|项目总览]]
- [[80-项目与实验记录/构建与验证状态|构建与验证状态]]
- [[98-资料索引/资料清单|资料清单]]
- [[98-资料索引/硬件资料蒸馏任务|硬件资料蒸馏任务]]
- [[99-待确认|待确认]]
""",
        "00-首页与导航/项目导航.md": f"""---
type: 导航页
status: 使用中
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 项目导航

> 从这里进入项目，不要在目录之间无目标漫游。

- [[工程库导航]]：原工程参照、模块机器清单和模板候选入口。
- [[模块导航]]：所有代码模块候选的聚合地图，不为每个模块自动创建孤立笔记。
- [[../60-可复用代码与工程模板/可复用模块候选|可复用模块候选]]：进入工程库前的抽取门槛。
- [[../80-项目与实验记录/项目总览|项目总览]]：目标、入口、技术栈和风险。
- [[../80-项目与实验记录/构建与验证状态|构建与验证状态]]：L0/L1/L2/L3 证据边界。
- [[../20-芯片与开发板/硬件资料与板卡候选|硬件资料与板卡候选]]。
- [[../98-资料索引/资料清单|资料清单]]。
- [[../98-资料索引/硬件资料蒸馏任务|硬件资料蒸馏任务]]。
- [[../99-待确认|待确认]]。
""",
        "00-首页与导航/工程库导航.md": f"""---
type: 导航页
status: 使用中
trust_level: L0
source_path: {library_project_rel}
created: {data['generated_at']}
---

# 工程库导航

> 代码不放进本 Vault。原工程保持不动；相邻工程库记录工程参照和模块抽取候选。

- [工程参照清单]({library_project_rel})
- [模块机器清单](../{library_name}/工程参照/{project_key}/模块索引.json)
- [模板候选说明](../{library_name}/模板候选/README.md)

## 使用顺序

```text
知识库中的模块导航
→ 原工程文件链接
→ 工程库模块清单
→ 新工程副本中的模板候选
→ 独立构建 / 目标板验证
```

不要从原工程剪切代码，不要把扫描到的模块写成已验证模板。
""",
        "00-首页与导航/模块导航.md": """---
type: 聚合模块导航
status: 自动扫描，待人工确认
trust_level: L0
source_path: .
---

# 模块导航

> 本页聚合当前工程的所有模块候选，避免为每个源文件生成孤立 Markdown。点击源文件链接后，AI 应直接读取真实工程文件。

""",
        "20-芯片与开发板/硬件资料与板卡候选.md": f"""---
type: 硬件资料与板卡候选
status: 待确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 硬件资料与板卡候选

## 扫描到的硬件文件

{bullet_list(data['hardware_files'])}

## 技术栈证据

{stack_table(data['stack_candidates'])}

> 手册、原理图和配置文件只能形成 L0 参考；先按 [[../98-资料索引/硬件资料蒸馏任务|硬件资料蒸馏任务]] 主动转换并阅读资料，再确认型号、封装、PinMux、供电、电平和板级连接。
""",
        "60-可复用代码与工程模板/可复用模块候选.md": """---
type: 可复用模块候选
status: 自动扫描，待人工确认
trust_level: L0
source_path: .
---

# 可复用模块候选

> 本页不存放源码。模块具体清单集中在 [[../00-首页与导航/模块导航|模块导航]]，工程抽取规则集中在相邻工程库。

## 进入工程库前的门槛

1. 明确公共 API、数据所有权、全局变量和初始化顺序；
2. 明确 HAL/BSP、PinMux、DMA、中断、RTOS 和构建依赖；
3. 在新工程副本中完成独立构建；
4. 根据模块风险完成目标板验证；
5. 记录适用边界、禁止复用情形和证据等级。
""",
        "80-项目与实验记录/项目总览.md": f"""---
type: 项目总览
status: 自动扫描，待人工确认
trust_level: L0
source_path: .
created: {data['generated_at']}
verification_scope: 未验证
---

# 项目总览

## 项目入口

{bullet_list(data['project_markers'])}

## 技术栈候选

{stack_table(data['stack_candidates'])}

## 模块候选

- 共识别 `{len(data['modules'])}` 个聚合模块候选；见 [[../00-首页与导航/模块导航|模块导航]]。
- 原工程代码不复制入知识库；工程抽取清单见 [[../00-首页与导航/工程库导航|工程库导航]]。

## 当前状态

- 本知识库由只读扫描生成；未执行构建、烧录、上板或整机验证。
- 自动识别内容默认 L0，待读取真实项目文档和源码后确认。
""",
        "80-项目与实验记录/构建与验证状态.md": """---
type: 构建与验证状态
status: 待确认
trust_level: L0
source_path: .
verification_scope: 未执行
---

# 构建与验证状态

| 范围 | 当前证据 | 结论 |
|---|---|---|
| 资料参考 | 文件树、配置与源码候选 | L0 |
| 本机构建 | 未执行 | 待确认 |
| 烧录 | 未执行 | 待确认 |
| 目标板 | 未执行 | 待确认 |
| 整机/车辆 | 未执行 | 待确认 |

> 后续必须记录实际命令、工作目录、日志、板卡版本、接线和测试条件；构建、烧录、上板和整机验证不可互相替代。
""",
        "98-资料索引/资料清单.md": f"""---
type: 资料索引
status: 自动扫描，待确认
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 资料清单

## 可转换资料候选

{bullet_list(data['document_files'])}

## 主动蒸馏候选

{hardware_docs}

## 使用规则

1. 优先读取上表"高"优先级的硬件资料；中优先级资料先转换标题/目录并确认类型。
2. 保留原始资料在原工程/资料目录；转换稿只作为可检索镜像。
3. 基于资料生成芯片、板卡或模块档案时，每个关键结论记录来源、版本和页码/章节。
4. 具体动作见 [[硬件资料蒸馏任务]]。
""",
        "98-资料索引/硬件资料蒸馏任务.md": f"""---
type: 硬件资料蒸馏任务
status: 自动扫描，待执行
trust_level: L0
source_path: .
created: {data['generated_at']}
---

# 硬件资料蒸馏任务

> 此页要求 Agent 主动阅读项目内与硬件相关的 PDF、DOCX、HTML、原理图和引脚资料；不是仅列出文件名。执行转换/容器前按项目规则确认计划和权限。

## 优先读取资料

{hardware_docs}

## 执行顺序

1. 对高优先级可转换资料调用 `document-to-markdown`，输出到 `98-资料索引/转换稿/`；原资料保持不动。
2. 主动阅读转换后的正文、目录、表格、版本与页码。先确认这是数据手册、参考手册、开发板用户手册、原理图说明还是普通参考资料。
3. 若资料可确认 MCU：创建或补充 `20-芯片与开发板/<芯片型号>-芯片资源与PinMux速查.md`。
4. 若资料可确认开发板：创建或补充 `20-芯片与开发板/<板卡名><芯片型号>开发板档案.md`。
5. 若原理图/BOM 足以确认板级连接：创建或补充 `20-芯片与开发板/<板卡名>-板级引脚与接口.md`。
6. 每个结论标注 `source_path`、资料版本、页码/章节、L0 状态和待确认项；不要把手册结论写成上板验证。

## 无法转换时

- Docker/Podman 或转换 Skill 不可用：记录"缺失，需手动实现"，保留原始资料路径；
- 文档是扫描件、图片或格式损坏：记录解析限制，必要时改用 OCR/人工核对；
- 找不到确切型号、封装或板卡版本：只建立待确认候选，不编造档案内容。
""",
        "99-待确认.md": """---
type: 待确认清单
status: 使用中
trust_level: L0
verification_scope: 未验证
---

# 待确认

- 模块候选的真实职责、调用方、全局变量、中断/任务上下文和最小依赖；
- 实际芯片、板卡、封装、PinMux、供电、电平和接口方向；
- 构建、烧录、调试工具链与实际命令；
- 独立模块构建、目标板与整机验证记录；
- 哪些候选模块值得进入工程库的模板候选目录。
""",
    }


def create_outputs(root: Path, knowledge: Path, engineering: Path, data: dict[str, object], overwrite: bool) -> list[str]:
    for output in (knowledge, engineering):
        try:
            output.relative_to(root)
        except ValueError as error:
            raise ValueError("知识库和工程库都必须位于 PROJECT_ROOT 内，避免误写到外部位置。") from error
        if output == root:
            raise ValueError("输出目录不能与 PROJECT_ROOT 相同。")
    if knowledge == engineering:
        raise ValueError("知识库和工程库输出目录不能相同。")

    written: list[str] = []
    for rel_path, content in engineering_library_files(data).items():
        target = engineering / rel_path
        if write_generated(target, content, overwrite):
            written.append(f"工程库/{relative(target, engineering)}")

    files = knowledge_files(data, root, engineering.name)
    module_note_path = knowledge / "00-首页与导航" / "模块导航.md"
    files["00-首页与导航/模块导航.md"] += module_table(data, root, module_note_path) + "\n\n## 复用规则\n\n- [[../60-可复用代码与工程模板/可复用模块候选|可复用模块候选]]：进入工程库前的抽取门槛。\n- 具体 API、include、SHA256 和候选边界见相邻工程库的 `模块索引.json`。\n- 先读原工程，再在新工程副本中抽取；不自动移动或复制当前工程代码。\n"
    for rel_path, content in files.items():
        target = knowledge / rel_path
        if write_generated(target, content, overwrite):
            written.append(f"知识库/{relative(target, knowledge)}")

    inventory_path = engineering / "工程参照" / safe_name(data["project_name"]) / "工程扫描清单.json"
    if not inventory_path.exists() or overwrite:
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(f"工程库/{relative(inventory_path, engineering)}")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="当前工程根目录；默认当前目录。")
    parser.add_argument("--report", help="只读扫描报告输出路径；不创建知识库或工程库。")
    parser.add_argument("--create", action="store_true", help="同时创建项目内的嵌入式工程库和 Obsidian 知识库。")
    parser.add_argument("--knowledge-output", help="知识库目录；默认 PROJECT_ROOT/Obsidian嵌入式知识库。")
    parser.add_argument("--engineering-output", help="工程库目录；默认 PROJECT_ROOT/嵌入式工程库。")
    parser.add_argument("--overwrite-generated", action="store_true", help="覆盖已有自动生成文件；使用前先人工检查差异。")
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
        knowledge = Path(args.knowledge_output).resolve() if args.knowledge_output else root / "Obsidian嵌入式知识库"
        engineering = Path(args.engineering_output).resolve() if args.engineering_output else root / "嵌入式工程库"
        written = create_outputs(root, knowledge, engineering, data, args.overwrite_generated)
        print(f"[OK] 知识库目录：{knowledge}")
        print(f"[OK] 工程库目录：{engineering}")
        print(f"[OK] 聚合模块数量：{len(data['modules'])}")
        print(f"[OK] 新建/更新文件数量：{len(written)}")
        for item in written:
            print(f"  + {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
