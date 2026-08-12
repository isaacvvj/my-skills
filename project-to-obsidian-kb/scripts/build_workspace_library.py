#!/usr/bin/env python3
"""Scan a project workspace and build separate engineering-library and Obsidian-vault indexes."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

SKIP={'.git','.hg','.svn','.idea','.vscode','.vs','.settings','.trae','node_modules','.venv','venv','__pycache__','build','Debug','Release','debug','release','dist','out','target','cmake-build-debug','cmake-build-release','Obsidian嵌入式知识库','嵌入式工程库'}
SRC={'.c','.h','.cpp','.cxx','.cc','.hpp','.s','.py','.ino','.rs','.ps1','.sh'}
TEXT=SRC|{'.md','.txt','.json','.yaml','.yml','.ini','.cfg','.ioc','.syscfg','.xml','.project','.cproject','.uvprojx','.ewp','.mk','.cmake'}
DOC={'.pdf','.doc','.docx','.ppt','.pptx','.xls','.xlsx','.html','.htm'}
EDA={'.kicad_sch','.kicad_pcb','.sch','.brd','.pcbdoc','.schdoc','.bom','.csv'}
MARKERS={'cmakelists.txt','makefile','platformio.ini','west.yml','idf_component.yml','.project','.cproject'}
SCRIPTS={'build.ps1','flash.ps1','validate.ps1','build.bat','flash.bat'}
HW_WORDS=('datasheet','data-sheet','reference','manual','user-guide','schematic','pinout','pin-mux','hardware','board','mcu','芯片','开发板','数据手册','参考手册','用户手册','原理图','引脚','硬件')
PROTECTED={'drivers','startup','middleware','middlewares','cmsis','hal','ll','sdk','third_party','third-party','vendor','generated','targetconfigs'}

def rel(p:Path,root:Path)->str:return p.relative_to(root).as_posix()
def safe(s:str)->str:return re.sub(r'[\\/:*?"<>|#\[\]]','_',s).strip('. ') or '待确认'
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p:Path)->str:
 for e in ('utf-8-sig','utf-8','gbk'):
  try:return p.read_text(encoding=e)
  except UnicodeDecodeError:pass
 return p.read_text(encoding='utf-8',errors='replace')
def files(root:Path,extra:set[str]|None=None)->list[Path]:
 out=[]; skip=SKIP|(extra or set())
 for cur,dirs,names in os.walk(root):
  dirs[:]=[x for x in dirs if x not in skip]; base=Path(cur)
  out += [base/x for x in names if (base/x).is_file()]
 return sorted(out,key=lambda p:rel(p,root).lower())
def marker_root(p:Path)->Path|None:
 n=p.name.lower()
 if n in MARKERS or p.suffix.lower() in {'.ioc','.syscfg','.uvprojx','.ewp'}:return p.parent
 if n in SCRIPTS and p.parent.name.lower()=='tools':return p.parent.parent
 return None

def evidence_add(store,cat,val,src):
 if val:store[cat][val].add(src)
def tech(fs:list[Path],root:Path)->list[dict]:
 store=defaultdict(lambda:defaultdict(set)); langs={'.c':'C','.h':'C/C++ 头文件','.cpp':'C++','.cxx':'C++','.cc':'C++','.hpp':'C++ 头文件','.py':'Python','.ino':'Arduino','.rs':'Rust','.ps1':'PowerShell','.sh':'Shell'}
 rules={
 'MCU/SoC':[(r'\bSTM32[A-Z0-9_]{3,}\b','STM32'),(r'\bMSPM0[A-Z0-9_]+\b','MSPM0'),(r'\bESP32(?:-[A-Z0-9]+)?\b','ESP32'),(r'\bRP2040\b','RP2040'),(r'\bK230\b','K230'),(r'\bRK3566\b','RK3566')],
 '开发板':[(r'\bBluePill\b','BluePill'),(r'\bLite-K230D\b','Lite-K230D'),(r'地猛星','地猛星'),(r'天猛星','天猛星'),(r'庐山派','庐山派')],
 '软件框架':[(r'\bFreeRTOS\b|\bxTaskCreate\b|\bvTaskDelay\b','FreeRTOS'),(r'\bRT-Thread\b|\brt_thread_','RT-Thread'),(r'\bHAL_[A-Za-z0-9_]','STM32 HAL'),(r'\bLL_[A-Za-z0-9_]','STM32 LL'),(r'\bDriverLib\b|\bDL_[A-Za-z0-9_]','TI DriverLib'),(r'\bESP-IDF\b|\bapp_main\b','ESP-IDF'),(r'\bArduino\.h\b|\bsetup\s*\(','Arduino'),(r'\bCanMV\b|\bmachine\.UART\b','CanMV / MicroPython'),(r'\bbare[- ]?metal\b|裸机','裸机候选')],
 '通信与接口':[(r'\bUART\b|\bUSART\b','UART/USART'),(r'\bI2C\b|\bIIC\b','I2C'),(r'\bSPI\b','SPI'),(r'\bCAN\b|\bFDCAN\b','CAN'),(r'\bUSB\b','USB'),(r'\bETH\b|\bEthernet\b|\bWiFi\b|\bSocket\b','网络'),(r'\bADC\b','ADC'),(r'\bDMA\b','DMA'),(r'\bPWM\b','PWM'),(r'\bTIM\d*\b|\bTimer\b','定时器'),(r'encoder|编码器','编码器'),(r'camera|摄像头','摄像头')],
 '软件设计与算法':[(r'\bPID\b','PID'),(r'kalman|卡尔曼','卡尔曼滤波'),(r'filter|滤波','滤波'),(r'state[_ -]?machine|状态机','状态机'),(r'vision|yolo|kpu|视觉','视觉识别'),(r'motion|运动控制|trajectory','运动控制'),(r'crc|frame|protocol|协议','协议解析')]}
 for p in fs:
  src=rel(p,root); n=p.name.lower(); suf=p.suffix.lower()
  if suf in langs:evidence_add(store,'编程语言',langs[suf],src)
  if n=='cmakelists.txt':evidence_add(store,'构建系统','CMake',src)
  if n=='makefile' or suf=='.mk':evidence_add(store,'构建系统','Make',src)
  if n=='platformio.ini':evidence_add(store,'构建系统','PlatformIO',src)
  if n in {'.project','.cproject'}:evidence_add(store,'构建系统','Eclipse / CubeIDE / CCS 候选',src)
  if suf=='.uvprojx':evidence_add(store,'构建系统','Keil uVision',src)
  if suf=='.ewp':evidence_add(store,'构建系统','IAR',src)
  if n in SCRIPTS:evidence_add(store,'构建/烧录/验证脚本',p.name,src)
  if suf=='.ioc':evidence_add(store,'平台与芯片配置','STM32CubeMX .ioc',src)
  if suf=='.syscfg':evidence_add(store,'平台与芯片配置','TI SysConfig .syscfg',src)
  if suf not in TEXT or p.stat().st_size>512*1024:continue
  t=read(p)
  for cat,items in rules.items():
   for expr,val in items:
    if re.search(expr,t,re.I):evidence_add(store,cat,val,src)
  for x in re.findall(r'\b(?:STM32[A-Z0-9_]{3,}|MSPM0[A-Z0-9_]+|ESP32(?:-[A-Z0-9]+)?)\b',t,re.I):evidence_add(store,'具体器件候选',x.upper(),src)
 order=['MCU/SoC','具体器件候选','开发板','编程语言','平台与芯片配置','软件框架','构建系统','构建/烧录/验证脚本','通信与接口','软件设计与算法']
 return [{'category':c,'value':v,'evidence':sorted(s)} for c in order for v,s in sorted(store[c].items())]

def docs(fs:list[Path],root:Path)->list[dict]:
 out=[]
 for p in fs:
  src=rel(p,root); low=src.lower()
  if p.suffix.lower() in EDA:out.append({'path':src,'kind':'原理图/PCB/BOM','priority':'高','reason':'EDA 或 BOM 文件'})
  elif p.suffix.lower() in DOC and (any(w in low for w in HW_WORDS) or any(w in low for w in ('hardware','manual','board','资料','硬件'))):out.append({'path':src,'kind':'可转换硬件资料','priority':'高','reason':'文件名或路径具有硬件资料特征'})
 return sorted(out,key=lambda x:x['path'].lower())

def first(records:list[dict],category:str)->str|None:return next((x['value'] for x in records if x['category']==category),None)
def route(name:str,records:list[dict])->tuple[str,str,str]:
 ps=[x['value'] for x in records if x['category']=='MCU/SoC']; plat=ps[0] if len(ps)==1 else ('multi-board' if len(ps)>1 else 'other')
 board='多板系统' if len(ps)>1 else (first(records,'开发板') or first(records,'具体器件候选') or '待确认板卡')
 return plat.lower(),safe(board),safe(name)
def mod_domain(p:Path)->str:
 s=p.stem.lower(); parts={x.lower() for x in p.parts}
 if p.name.lower() in {'main.c','main.cpp','main.py','app_main.c','app_main.cpp'}:return '项目编排'
 if parts&PROTECTED:return '受保护依赖'
 if any(x in s for x in ('uart','usart','i2c','spi','can','protocol','frame','ring','serial')):return '通信协议'
 if any(x in s for x in ('motor','pwm','servo','stepper','encoder','adc','imu','sensor','camera','vision','oled','lcd','key')):return '外设与驱动'
 if any(x in s for x in ('pid','filter','kalman','state','control','track','motion')):return '软件设计与算法'
 return '项目功能'
def modules(fs:list[Path],root:Path)->dict[str,list[dict]]:
 by=defaultdict(list)
 for p in fs:
  if p.suffix.lower() in SRC:by[p.stem.lower()].append(p)
 out=defaultdict(list)
 for name,srcs in sorted(by.items()):
  srcs=sorted(srcs,key=lambda x:rel(x,root)); d=mod_domain(srcs[0]); inc=set(); api=set(); funcs=set()
  for p in srcs:
   if p.stat().st_size>256*1024:continue
   t=read(p); inc.update(re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',t,re.M))
   if p.suffix.lower() in {'.h','.hpp'}:api.update(re.sub(r'\s+',' ',x.strip()) for x in re.findall(r'^\s*(?:extern\s+)?(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+[A-Za-z_]\w*\s*\([^;{}]*\)\s*;',t,re.M))
   funcs.update(re.findall(r'^\s*(?:static\s+)?[A-Za-z_][\w\s\*]*?\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{',t,re.M))
  classes=set()
  for src_path in srcs:
   if src_path.suffix.lower()=='.py' and src_path.stat().st_size<=256*1024:
    classes.update(re.findall(r'^class\s+([A-Za-z_]\w*)',read(src_path),re.M))
  out[d].append({'name':name,'source_files':[rel(x,root) for x in srcs],'public_api':sorted(api)[:30],'defined_functions':sorted(funcs)[:40],'classes':sorted(classes)[:20],'direct_includes':sorted(inc)[:40],'reuse_status':'仅供工程参照，禁止自动抽取' if d in {'项目编排','受保护依赖'} else '候选模块：独立构建与上板验证后才可进入模板仓库'})
 return dict(out)
def inventory(workspace:Path)->dict:
 allfs=files(workspace); groups=[]; materials=[]
 for child in sorted((p for p in workspace.iterdir() if p.is_dir() and p.name not in SKIP),key=lambda x:x.name.lower()):
  fs=files(child); hasproj=any(marker_root(p) for p in fs); hasdocs=any(p.suffix.lower() in DOC|EDA for p in fs)
  if hasproj:groups.append(child)
  elif hasdocs:materials.append(child)
 if not groups:groups=[workspace]
 projects=[]; subs=[]
 for g in groups:
  gfs=files(g); gt=tech(gfs,g); platform,board,name=route(g.name,gt)
  projects.append({'name':g.name,'source_path':rel(g,workspace) if g!=workspace else '.','tech':gt,'archive':f'项目归档/{platform}/{board}/{name}','template':f'模板仓库/{platform}/{board}/{name}-候选'})
  roots={r for p in gfs if (r:=marker_root(p))}
  if not roots:roots={g}
  for r in sorted(roots,key=lambda x:(len(x.parts),str(x).lower())):
   rfs=files(r); rt=tech(rfs,r); sp,sb,sn=route(r.name,rt)
   subs.append({'name':r.name,'group':g.name,'source_path':rel(r,workspace),'tech':rt,'archive':f'项目归档/{platform}/{board}/{name}/{sp}/{sb}/{sn}','template':f'模板仓库/{sp}/{sb}/{sn}-候选'})
 return {'date':date.today().isoformat(),'workspace':str(workspace),'name':workspace.name,'file_count':len(allfs),'tech':tech(allfs,workspace),'docs':docs(allfs,workspace),'modules':modules(allfs,workspace),'groups':projects,'subs':subs,'materials':[{'name':m.name,'source_path':rel(m,workspace),'archive':f'资料归档/{safe(m.name)}'} for m in materials]}

def table_tech(items:list[dict])->str:
 rows=['| 类型 | 实际内容 | 证据来源 | 可信等级 |','|---|---|---|---|']
 for x in items:rows.append(f"| {x['category']} | {x['value']} | {'<br>'.join('`'+a+'`' for a in x['evidence'])} | L0 |")
 return '\n'.join(rows) if len(rows)>2 else '- 信息不足，缺失，需手动实现。'
def table_docs(items:list[dict])->str:
 rows=['| 资料 | 类型 | 优先级 | 判定依据 |','|---|---|---|---|']
 for x in items:rows.append(f"| `{x['path']}` | {x['kind']} | {x['priority']} | {x['reason']} |")
 return '\n'.join(rows) if len(rows)>2 else '- 未发现可主动蒸馏资料；待确认。'
def code_inventory(items:list[dict])->str:
 rows=["| 代码候选 | 源文件数 | API/函数候选 | 当前边界 |","|---|---|---|"]
 for x in items:
  api=x["defined_functions"][:4] or ["待确认"]
  rows.append(f"| `{x['name']}` | {len(x['source_files'])} | {', '.join('`'+a+'`' for a in api)} | {x['reuse_status']} |")
 return "\n".join(rows) if len(rows)>2 else "- 未发现相关代码候选；待确认。"
def put(path:Path,text:str,overwrite:bool)->bool:
 if path.exists() and not overwrite:return False
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n');return True
def migration(data:dict)->str:
 rows=['| 工程组 | 原始路径 | 项目归档目标 | 模板候选目标 | 迁移状态 |','|---|---|---|---|---|']
 for x in data['groups']:rows.append(f"| {x['name']} | `{x['source_path']}` | `{x['archive']}` | `{x['template']}` | 待复制校验 |")
 return '\n'.join(rows)

def engine_files(data:dict)->dict[str,str]:
 mats='\n'.join(f"- `{x['source_path']}` → `{x['archive']}`" for x in data['materials']) or '- 无独立资料组。'
 return {'README.md':'# 嵌入式工程库\n\n完整工程资产按模板仓库、项目归档和资料归档管理；源码不放 Obsidian。\n\n- [模板仓库](模板仓库/README.md)\n- [项目归档](项目归档/README.md)\n- [资料归档](资料归档/README.md)\n- [工程迁移计划](工程迁移计划.md)\n','模板仓库/README.md':'# 模板仓库\n\n按 `平台/板卡或器件/模板名` 分类。只有接口、依赖、独立构建和验证范围明确后，才允许从项目归档提升到模板仓库。\n','项目归档/README.md':'# 项目归档\n\n按 `平台/板卡或具体器件/工程组/子项目` 保存完整工程。使用 `--stage-archives` 先复制并逐文件 SHA256 校验；旧工程不自动删除。\n','资料归档/README.md':f'# 资料归档\n\n保留完整资料包、原始手册、原理图导出和工程附件；知识库只保存索引、蒸馏结论和来源。\n\n## 当前资料组\n\n{mats}\n','工程迁移计划.md':f'---\ntype: 工程迁移计划\nstatus: 待确认\ntrust_level: L0\ncreated: {data["date"]}\n---\n\n# 工程迁移计划\n\n{migration(data)}\n\n```text\n只读盘点 → 用户确认 → 复制到项目归档 → SHA256 校验 → 检查构建入口和知识库链接 → 人工确认旧路径是否收口\n```\n\n模板仓库不自动接收整个项目；仅接收经过抽取计划和验证的模板候选。\n'}

def vault_files(data:dict,workspace:Path,engine:Path,vault:Path)->dict[str,str]:
 subs='\n'.join(f"- [[01-项目地图/项目档案/{safe(x['group'])}-{safe(x['name'])}|{x['group']} / {x['name']}]]" for x in data['subs']) or '- 未发现子项目；待确认。'
 f={'README.md':'# 项目 Obsidian 嵌入式知识库\n\n本库保存导航、技术栈证据、硬件资料蒸馏、项目记录和验证状态。完整源码保留在原工程和相邻工程库，不复制进 Obsidian。\n\n- [[00-首页与导航/项目导航|项目导航]]\n- [[00-首页与导航/技术栈地图|技术栈地图]]\n- [[01-项目地图/子项目索引|子项目索引]]\n- [[80-项目与实验记录/项目总览|项目总览]]\n- [[80-项目与实验记录/构建与验证状态|构建与验证状态]]\n- [[98-资料索引/资料清单|资料清单]]\n- [[99-待确认|待确认]]\n','00-首页与导航/工程库导航.md':f'# 工程库导航\n\n- [工程库首页]({os.path.relpath(engine/"README.md",vault/"00-首页与导航").replace("\\","/")})\n- [模板仓库]({os.path.relpath(engine/"模板仓库"/"README.md",vault/"00-首页与导航").replace("\\","/")})\n- [项目归档]({os.path.relpath(engine/"项目归档"/"README.md",vault/"00-首页与导航").replace("\\","/")})\n- [工程迁移计划]({os.path.relpath(engine/"工程迁移计划.md",vault/"00-首页与导航").replace("\\","/")})\n\n工程迁移采用复制+SHA256校验，旧目录仅在人工确认后处理。\n','00-首页与导航/技术栈地图.md':f'# 技术栈地图\n\n{table_tech(data["tech"])}\n\n识别结论均为 L0。按领域从 [[项目导航]] 进入对应索引。\n','01-项目地图/子项目索引.md':f'# 子项目索引\n\n{subs}\n','01-项目地图/项目文件地图.md':'# 项目文件地图\n\n按子项目档案查看工程入口、配置、构建脚本、自动生成文件和归档目标。不要直接修改 `.ioc`、`.syscfg`、启动文件、链接脚本、SDK 和构建产物。\n\n- [[子项目索引]]\n- [[../00-首页与导航/工程库导航|工程库导航]]\n','80-项目与实验记录/项目总览.md':f'# 项目总览\n\n## 工程组\n\n{migration(data)}\n\n## 当前可信等级\n\n- 仅完成文件与资料扫描：L0。\n- 未执行构建、烧录、上板或整机验证。\n\n相关：[[../01-项目地图/子项目索引|子项目索引]]、[[构建与验证状态]]、[[../00-首页与导航/工程库导航|工程库导航]]。\n','80-项目与实验记录/构建与验证状态.md':'# 构建与验证状态\n\n| 范围 | 当前证据 | 结论 |\n|---|---|---|\n| 资料/源码参考 | 文件、README、配置扫描 | L0 |\n| 本机构建 | 未执行 | 待确认 |\n| 烧录 | 未执行 | 待确认 |\n| 目标板 | 未执行 | 待确认 |\n| 整机功能 | 未执行 | 待确认 |\n\n构建、烧录、上板和整机功能不可互相替代。\n','95-AI协作规范/知识库协作规范.md':'# 知识库协作规范\n\n1. 修改前阅读 README、AGENTS、任务上下文、构建脚本和硬件资料。\n2. 先计划，再最小修改；不擅自改自动生成文件、启动文件、链接脚本、芯片配置和厂商 SDK。\n3. 每次变更区分资料、构建、烧录、目标板和整机证据。\n4. 代码、配置、工程库和知识库保持来源可追溯。\n5. 未确认内容写“待确认”或“缺失，需手动实现”。\n','98-资料索引/资料清单.md':f'# 资料清单\n\n{table_docs(data["docs"])}\n\n- [[硬件资料蒸馏任务]]\n','98-资料索引/硬件资料蒸馏任务.md':f'# 硬件资料蒸馏任务\n\n{table_docs(data["docs"])}\n\n1. 优先转换高优先级数据手册、参考手册、开发板手册、原理图、引脚图和 BOM。\n2. 调用 `document-to-markdown` 后，**主动阅读转换稿正文、目录、表格、资料版本和页码**。\n3. 资料足够时创建并互链：`<芯片>-芯片资源与PinMux速查`、`<板卡><芯片>开发板档案`、`<板卡>-板级引脚与接口`。\n4. 每个结论记录来源、页码/章节、L0 和待确认项；不把手册资料写成上板验证。\n','99-待确认.md':'# 待确认\n\n- MCU、板卡、封装、PinMux、供电、电平和接口方向；\n- 子项目之间的共享代码边界；\n- 哪些项目/模块具备进入模板仓库的条件；\n- 资料蒸馏中无法确认的型号、版本与冲突项。\n'}
 for x in data['subs']:
  f[f"01-项目地图/项目档案/{safe(x['group'])}-{safe(x['name'])}.md"]=f'# {x["group"]} / {x["name"]} 项目档案\n\n- 原始路径：`{x["source_path"]}`\n- 项目归档目标：`{x["archive"]}`\n- 模板候选目标：`{x["template"]}`\n\n## 实际技术栈与证据\n\n{table_tech(x["tech"])}\n\n返回 [[../子项目索引|子项目索引]]、[[../../00-首页与导航/工程库导航|工程库导航]]、[[../../80-项目与实验记录/构建与验证状态|构建与验证状态]]。\n'
 return f

def add_domains(f:dict,data:dict,workspace:Path,vault:Path)->list[tuple[str,str]]:
 domains={'20-芯片与开发板/芯片与开发板索引.md':('芯片与开发板索引',{'MCU/SoC','具体器件候选','开发板','平台与芯片配置'}),'30-硬件模块与接口/接口与外设索引.md':('接口与外设索引',{'通信与接口'}),'40-外设与驱动/外设与驱动索引.md':('外设与驱动索引',set()),'50-软件设计与算法/软件框架索引.md':('软件框架索引',{'编程语言','软件框架'}),'50-软件设计与算法/算法与控制索引.md':('算法与控制索引',{'软件设计与算法'}),'60-通信协议/通信协议索引.md':('通信协议索引',set()),'70-构建与烧录/构建工具链索引.md':('构建工具链索引',{'构建系统','构建/烧录/验证脚本'}),'60-可复用代码与工程模板/工程模板与项目归档索引.md':('工程模板与项目归档索引',set())}
 mp={'外设与驱动':'40-外设与驱动/外设与驱动索引.md','通信协议':'60-通信协议/通信协议索引.md','软件设计与算法':'50-软件设计与算法/算法与控制索引.md'}; by=defaultdict(list)
 for g,items in data['modules'].items():
  if g in mp:by[mp[g]].extend(items)
 nav=[]
 for path,(title,cats) in domains.items():
  rec=[x for x in data['tech'] if x['category'] in cats]; note=vault/path
  if path.startswith('60-可复用'):
   text=f'# {title}\n\n## 工程组与归档目标\n\n{migration(data)}\n\n模板仓库只接收经过抽取计划、独立构建和验证的资产；完整工程先进入项目归档。\n'
  else:
   text=f'# {title}\n\n- 返回 [[../00-首页与导航/项目导航|项目导航]]\n- 参照 [[../00-首页与导航/技术栈地图|技术栈地图]]\n\n## 实际技术栈证据\n\n{table_tech(rec)}\n\n## 当前工程相关代码候选\n\n{code_inventory(by[path]) if by.get(path) else "- 未发现归入本领域的代码候选；待确认。"}\n\n自动分组只用于 AI 阅读入口；确认依赖、构建和验证后才能提取为模板。\n'
  f[path]=text;nav.append((path,title))
 return nav
def add_nav(f:dict,nav:list[tuple[str,str]]):
 links='\n'.join(f'- [[../{p.removesuffix(".md")}|{title}]]' for p,title in nav)
 f['00-首页与导航/项目导航.md']=f'# 项目导航\n\n- [[语义模块蒸馏任务]]：先读实际代码，再生成少量按功能命名的模块笔记。\n- [[../60-可复用代码与工程模板/代码模块索引|代码模块索引]]\n- [[技术栈地图]]\n- [[工程库导航]]\n- [[../01-项目地图/子项目索引|子项目索引]]\n- [[../01-项目地图/项目文件地图|项目文件地图]]\n{links}\n- [[../80-项目与实验记录/项目总览|项目总览]]\n- [[../80-项目与实验记录/构建与验证状态|构建与验证状态]]\n- [[../95-AI协作规范/知识库协作规范|知识库协作规范]]\n- [[../98-资料索引/资料清单|资料清单]]\n- [[../98-资料索引/硬件资料蒸馏任务|硬件资料蒸馏任务]]\n- [[知识库构建报告]]\n- [[../99-待确认|待确认]]\n'
def hashes(root:Path)->dict[str,str]:return {rel(p,root):sha(p) for p in files(root,{'嵌入式工程库','Obsidian嵌入式知识库'})}
def stage(workspace:Path,engine:Path,data:dict)->list[str]:
 out=[]
 for x in data['groups']+data['materials']:
  source=workspace/x['source_path']; target=engine/x['archive']
  if target.exists():raise FileExistsError(f'归档目标已存在，拒绝覆盖：{target}')
  before=hashes(source);shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','嵌入式工程库','Obsidian嵌入式知识库'));after=hashes(target)
  if before!=after:raise RuntimeError(f'SHA256 校验失败：{source} -> {target}')
  (target/'归档校验.json').write_text(json.dumps({'source_path':str(source),'destination':str(target),'sha256':before,'status':'copied_and_verified','trust_level':'L0'},ensure_ascii=False,indent=2),encoding='utf-8');out.append(str(target))
 return out
def semantic_modules(data: dict) -> list[dict]:
    """Use real source-name/API evidence to create a small set of human-readable module cards."""
    all_modules = [item for items in data["modules"].values() for item in items]
    specs = [
        ("视觉检测与坐标测量", "算法", ("ball", "detect", "track", "calib", "vision", "yolo", "camera"), "根据目标工程实际视觉代码归并检测、标定、跟踪或测量职责。", "算法与控制索引"),
        ("GPIO输入输出与事件触发", "驱动", ("gpio", "exti", "interrupt", "button", "key"), "根据目标工程实际代码归并 GPIO、外部中断、回调和事件交接职责。", "芯片与开发板索引"),
        ("串行通信与协议可靠性", "通信协议", ("uart", "usart", "i2c", "spi", "can", "protocol", "frame", "ring", "serial"), "根据目标工程实际代码归并收发、帧解析、校验、序号、新鲜度和失联处理职责。", "通信协议索引"),
        ("闭环控制与运行状态管理", "控制", ("pid", "control", "state", "mode", "trajectory", "motion", "recovery"), "根据目标工程实际代码归并反馈控制、状态切换、限幅和恢复职责。", "算法与控制索引"),
        ("定时采样与执行器输出", "外设与驱动", ("pwm", "motor", "encoder", "adc", "dma", "timer", "stepper", "servo"), "根据目标工程实际代码归并定时器、采样、PWM、编码器和执行器职责。", "外设与驱动索引"),
    ]
    output = []
    for title, kind, tokens, summary, domain in specs:
        matched = [item for item in all_modules if any(token in item["name"].lower() for token in tokens)]
        if not matched:
            continue
        source_files = sorted({path for item in matched for path in item["source_files"]})
        interfaces = sorted({name for item in matched for name in (item["defined_functions"] + item.get("classes", []))})[:16]
        source_project = source_files[0].split("/", 1)[0] if source_files else "待确认"
        output.append({"title": title, "kind": kind, "summary": summary, "domain": domain, "source_project": source_project, "source_files": source_files, "interfaces": interfaces})
    return output


def semantic_note(item: dict) -> str:
    sources = "\n".join("  - " + value for value in item["source_files"]) or "  - 待确认"
    interfaces = ", ".join(item["interfaces"]) if item["interfaces"] else "待从源码与调用方确认"
    return f"""---
type: 代码模块
status: 自动识别后待人工确认
trust_level: L0
platform: []
mcu: []
language: [C, Python]
module_type: {item['kind']}
source_project: {item['source_project']}
source_files:
{sources}
repo_name: 嵌入式工程库
repo_relative_path: 待确认
interfaces: [{interfaces}]
dependencies: []
verified_compile: false
verified_hardware: false
unverified_items: [实际职责、硬件绑定、调用顺序、构建和上板证据]
---

# {item['title']}

## 功能说明

{item['summary']}

> 本笔记根据真实工程中具有相关命名、API 和测试线索的用户模块生成。它不是源码文件镜像，也不代表模块已经独立构建或上板验证。

## 源码来源范围

`source_files` 仅为普通来源文本，不建立源码文件链接。SHA256、include 和完整 API 清单保存在工程库的 `工程参照/*/代码扫描清单.json`，不进入 Obsidian 图谱。

## API 候选

`{interfaces}`

## 复用与安全边界

- 补充输入、输出、单位、状态、时序和异常安全状态；
- 区分纯逻辑与 HAL/BSP、PinMux、DMA、中断、任务、摄像头或执行器硬件入口；
- 独立构建、目标板和整机验证必须分别记录；
- 只有完成抽取计划和验证后，才迁入工程库模板仓库。

## 相关笔记

- [[代码模块索引]]
- [[{item['domain']}]]
- [[子项目索引]]
- [[构建与验证状态]]
"""


def create(workspace: Path, engine: Path, vault: Path, data: dict, overwrite: bool, do_stage: bool) -> list[str]:
    if engine == vault:
        raise ValueError("工程库与知识库目录不能相同。")
    written = []
    for path, text in engine_files(data).items():
        if put(engine / path, text, overwrite):
            written.append(f"工程库/{path}")
    for group in data["groups"]:
        payload = {"workspace_group": group["name"], "source_path": group["source_path"], "modules": data["modules"], "generated_at": data["date"], "status": "read_only_inventory", "trust_level": "L0"}
        inventory_path = engine / "工程参照" / safe(group["name"]) / "代码扫描清单.json"
        if not inventory_path.exists() or overwrite:
            inventory_path.parent.mkdir(parents=True, exist_ok=True)
            inventory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(f"工程库/{inventory_path.relative_to(engine).as_posix()}")

    notes = vault_files(data, workspace, engine, vault)
    navigation = add_domains(notes, data, workspace, vault)
    add_nav(notes, navigation)
    semantic = semantic_modules(data)
    module_links = "\n".join(f"- [[{item['title']}]]" for item in semantic) or "- 未发现可命名的功能模块；执行 [[语义模块蒸馏任务]]。"
    notes["60-可复用代码与工程模板/代码模块索引.md"] = f"""# 代码模块索引

> 这是知识库中的明确功能模块入口。模块按工程能力命名，不按 `.c/.h` 文件命名；关系图只连接项目、模块、芯片、接口、算法、协议、构建和验证笔记。

## 当前模块

{module_links}

## 使用方式

- 从这里进入一个功能模块，再回到项目、接口、算法和验证笔记。
- `source_files` 仅是普通文本来源，不是 Obsidian 链接；源码节点不会进入关系图。
- 自动生成模块默认为 L0；读完调用方、配置和硬件资料后再补充或拆分。

## 模块蒸馏规则

[[语义模块蒸馏任务]]
"""
    for item in semantic:
        notes[f"60-可复用代码与工程模板/{item['title']}.md"] = semantic_note(item)
    notes["00-首页与导航/语义模块蒸馏任务.md"] = """# 语义模块蒸馏任务

> 以知识库功能模块模式沉淀内容：例如“K230钢球视觉算法模块”“GPIO与外部中断代码模块”“视觉接收状态机”，而不是生成 `gpio.c`、`uart.h` 笔记。

1. 从 [[子项目索引]] 选择一个项目，先读 README、AGENTS、入口、调用方、配置、测试和硬件资料。
2. 按功能职责、数据流、控制流、硬件所有权和复用边界归并 3~8 个模块。
3. 创建或完善 [[代码模块索引]] 中的模块笔记；标题必须是功能名称。
4. 每个模块记录功能、输入输出、API、依赖、时序、安全状态、来源文本、验证、限制和相关 Wiki 链接。
5. 不建立 `.c/.h/.cpp/.hpp/.py` Wiki 或 Markdown 链接；完整源码阅读线索保留在工程库私有清单。
6. 无法确认时进入 [[待确认]]，不要创建空模块笔记。
"""
    notes["00-首页与导航/知识库构建报告.md"] = f"""# 知识库构建报告

- 工作区：`{data['workspace']}`
- 工程组数量：{len(data['groups'])}
- 子项目数量：{len(data['subs'])}
- 自动功能模块：{len(semantic)}
- 硬件资料候选：{len(data['docs'])}
- 当前自动识别结论均为 L0。

返回 [[项目导航]]。
"""
    for path, text in notes.items():
        if put(vault / path, text, overwrite):
            written.append(f"知识库/{path}")
    if do_stage:
        written.extend(f"已复制并校验：{target}" for target in stage(workspace, engine, data))
    return written

def report(data:dict)->str:
 groups='\n'.join(f'- `{x["name"]}`：`{x["source_path"]}` → `{x["archive"]}`' for x in data['groups']) or '- 未发现工程组。'
 subs='\n'.join(f'- `{x["group"]} / {x["name"]}`：`{x["source_path"]}`' for x in data['subs']) or '- 未发现子项目。'
 return f'# 工程只读扫描报告\n\n- 工作区：`{data["workspace"]}`\n- 文件数量：{data["file_count"]}\n\n## 实际技术栈与证据\n\n{table_tech(data["tech"])}\n\n## 工程归档规划\n\n{groups}\n\n## 子项目\n\n{subs}\n\n## 硬件资料主动蒸馏候选\n\n{table_docs(data["docs"])}\n\n本报告未修改、移动、复制或删除原工程。\n'
def main()->int:
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project-root',default='.');ap.add_argument('--report');ap.add_argument('--create',action='store_true');ap.add_argument('--stage-archives',action='store_true');ap.add_argument('--engineering-root');ap.add_argument('--vault-root');ap.add_argument('--overwrite-generated',action='store_true');a=ap.parse_args();workspace=Path(a.project_root).resolve()
 if not workspace.is_dir():ap.error(f'PROJECT_ROOT 不存在或不是目录：{workspace}')
 if not(a.report or a.create or a.stage_archives):ap.error('至少指定 --report、--create 或 --stage-archives。')
 engine=Path(a.engineering_root).resolve() if a.engineering_root else workspace.parent/'嵌入式工程库';vault=Path(a.vault_root).resolve() if a.vault_root else workspace.parent/'Obsidian嵌入式知识库';data=inventory(workspace)
 if a.report:
  p=Path(a.report).resolve();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(report(data),encoding='utf-8',newline='\n');print(f'[OK] 只读扫描报告：{p}')
 if a.create or a.stage_archives:
  out=create(workspace,engine,vault,data,a.overwrite_generated,a.stage_archives);print(f'[OK] 工程库：{engine}');print(f'[OK] 知识库：{vault}');print(f'[OK] 工程组：{len(data["groups"])}；子项目：{len(data["subs"])}');print(f'[OK] 生成/暂存项：{len(out)}');[print(f'  + {x}') for x in out]
 return 0
if __name__=='__main__':raise SystemExit(main())
