# board-manual-distiller｜板卡手册与引脚资料蒸馏器

将 MCU 开发板/芯片的数据手册、原理图、引脚图、Wiki 等资料蒸馏为**结构化、可检索、可追溯**的 Obsidian Markdown 档案。

## 功能特性

- **三层档案结构**：主档案（板级入口） + 芯片PinMux速查（芯片级资源） + 板级引脚与接口（板卡级连接）
- **证据可追溯**：每条硬件事实标注来源（官方手册/Wiki/原理图/BOM）与版本
- **信任分级**：trust_level L0~L3，区分"手册/原理图确认"与"上板验证"
- **强制防伪**：禁止猜测引脚/电平/供电，未知项一律标"待确认"
- **批量处理**：支持多块板卡一次蒸馏，自动生成总索引
- **Obsidian友好**：完整 YAML frontmatter + `[[]]` 内部链接

## 目录结构

```
board-manual-distiller/
├── SKILL.md                    # 技能主文件（何时使用/模板/工作流/约束/检查清单）
├── README.md                   # 本说明文件
└── references/                 # 子场景模板
    ├── 主档案模板.md           # 开发板主索引
    ├── 芯片PinMux模板.md       # 芯片级资源与引脚复用
    ├── 板级接口模板.md         # 板级引脚与接口
    ├── 供电调试启动模板.md     # 供电/调试/启动专题
    └── 总索引模板.md           # 多板卡总索引
```

## 安装

将 `board-manual-distiller/` 整个目录放入：

- **Trae / TraeWork**：`<workspace>/.trae/skills/board-manual-distiller/`
- **Codex**：`~/.codex/skills/board-manual-distiller/`
- 或任意支持 skills 的 Agent 工作目录

## 使用方式

直接向 Agent 描述需求即可自动触发：

> "把XX开发板的资料整理一下" / "蒸馏XX芯片手册成md文件" / "做一个XX的引脚速查表" / "整理硬件资料方便管理"

## 输出示例

蒸馏一块开发板会生成（按资料可得性）：

```
STM32F103C8T6开发板档案.md           ← 主索引
STM32F103C8T6-芯片资源与PinMux速查.md  ← 芯片级（48脚完整映射表）
STM32F103C8T6-板级引脚与接口.md       ← 板级（需原理图）
```

多块板卡时额外生成 `芯片与开发板资料索引.md` 总导航。

## 已蒸馏案例

| 芯片 | 开发板 | 亮点 |
|---|---|---|
| STM32F103C8T6 | 通用最小系统板 | LQFP48 完整48脚映射表 |
| MSPM0G3507 | 立创地猛星/天猛星 | 板级接口（基于开源BOM+原理图） |
| ESP32-S3 | 乐鑫DevKitC-1 | Wi-Fi+BLE5+AI加速 |
| RP2040 | 树莓派Pico | 双核+PIO |
| K230/K230D | 立创庐山派 | RISC-V+6TOPS NPU |
| RK3566 | 立创泰山派 | 四核A55+1TOPS NPU |

## License

MIT
