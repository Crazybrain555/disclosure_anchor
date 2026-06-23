# 开源参考项目调研

本轮目标：为 `disclosure_anchor` 及其所在 L1 数据层的第一版实现找可借鉴的 GitHub 项目。服务目标不是单纯下载 PDF，而是：标准财务数据通过 `Dataset API` 使用、自维护披露文件处理成 `document + document_unit` 经 `Filing API` 交给 L2。

> 调研时间：2026-06-15（2026-06-20 按 v1.0 canonical 设计重构）。
>
> **对齐说明**：原稿把第一版存储定为“硬盘 + SQLite 索引”、对象用 `filing_text` / `filing_table` / `filing_table_cell`，
> 并把 Docling 作为默认 parser——这些都已过时。按 `service-purpose.md` / `财报与披露数据接入及切分方案.md` /
> `database-selection.md`，第一版**主库为 PostgreSQL**、对象为 `document_unit`（text/table/qa）、**默认 parser 为 MinerU**。
> 本文同时补入真正塑造 v1.0 的几个架构参考（OpenBB / dlt / CocoIndex），它们在原稿里缺失。术语与硬决策以 canonical 两文为准。

## 结论

最值得借鉴的是几类成熟设计，而不是直接复制某一个项目。按它们影响 v1.0 的方面分三组：

**A. 塑造架构与接口（数据源契约 + 领域对象 + 轻数据库 + 增量 + 变更传播）**

1. **数据源统一与 provider 适配 → Dataset API**：借鉴 `OpenBB`。
2. **Company / Filing / typed object 查询接口 → Filing API**：借鉴 `edgartools`。
3. **原始文件与数据库分离、数据库做减法**：借鉴 `secfsdstools`。
4. **增量游标与同步状态 → `source_access` / `source_checkpoint`**：借鉴 `dlt` 思想（不引框架）。
5. **content hash 驱动的变更传播**：借鉴 `CocoIndex` 思想（不引框架）。

**B. 披露侧抓取、下载与正文语义结构**

6. **巨潮接口参数、分页、断点续爬、去重**：参考 `CNInfoHedgeCrawler`、`CnInfoReports`、`stock-fundamental-data`。
7. **下载器与解析分离、fair-access**：参考 `sec-edgar-downloader`。
8. **section / 语义元素切分**：参考 `sec-parser`、`edgartools`。

**C. PDF 解析**

9. **PDF→Markdown/JSON、表格抽取**：默认 `MinerU`，`Docling` 第二后端（按需），`Camelot`/`pdfplumber` 做 text-PDF 表格 fallback（按需）。详见 `pdf-parsing-investigation.md`。

---

## 一、塑造 v1.0 架构的参考

### 1. OpenBB-finance/OpenBB

URL: https://github.com/OpenBB-finance/OpenBB

定位：面向分析师、quant 和 AI agent 的金融数据平台，把公开/授权/自有数据源通过统一平台接入，供 Python / REST / MCP 消费。

可借鉴点（最值得重点参考）：

- **provider 架构**：统一数据模型 → 统一查询参数 → Provider Router → 各数据源；每个 provider 实现 `Transform Query → Extract Data → Transform Data` 三步。
- 同一标准模型可挂多个 provider，调用者选 provider 或用默认；同一 router 同时暴露给 Python / REST / MCP。
- 统一的是**模型和接口**，不是把所有供应商数据先复制进一张统一表。

对本项目的启发：

- 这正是 `Dataset API` 的来源：`dataset("financial.income_statement").get(company=..., period=...)`，默认 provider 首版用 Wind（可换 Tushare / 同花顺 iFinD / Choice 等），缺失/失败/需要原文时再 fallback。
- 数据能力定义放 Git 中的 `dataset_registry`（YAML/Pydantic/注册表），数据库只记实际发生的 `source_access`，不承担“接口说明文档”职责。
- 值得细看：ProviderInterface、Fetcher、Standardized Data Model、Router Extension、Python/REST/MCP 共用接口的设计。

### 2. dgunning/edgartools

URL: https://github.com/dgunning/edgartools

定位：SEC EDGAR filings 的 Python structured-data library。

可借鉴点：

- `Company` / `Filing` 作为核心领域对象，而不是散落的文件路径。
- filing 可转成 typed object、DataFrame、clean text；延迟解析、本地缓存、保留原 filing 引用。
- 暴露业务语言（公司 / 公告 / 报告期 / 章节 / 表格 / 问答），而不是让调用方直接写 SQL。

对本项目的启发：

- 这是 `Filing API` 的来源。第一版 agent 入口应接近：

```python
filing = company("002484").filings(filing_type="annual_report", period="2025A").latest()
filing.text_units()
filing.tables()
filing.qa_items()
filing.units(semantic_key="receivable_aging")
filing.units(heading_path="第三节/管理层讨论与分析")
```

- agent 不需要知道标准数据 provider 的表名、PostgreSQL 表名、PDF parser、Markdown 路径、是否跨页——由领域对象隐藏。

不直接采用的原因：它面向 SEC/EDGAR 和 XBRL，不适配巨潮 PDF；但对象模型和 typed output 值得学。

### 3. HansjoergW/sec-fincancial-statement-data-set（secfsdstools）

URL: https://github.com/HansjoergW/sec-fincancial-statement-data-set

定位：SEC Financial Statement Data Sets 的本地下载、Parquet 转换、SQLite 索引工具。

可借鉴点：

- 原始下载文件 → 转换后的 Parquet → 很小的索引；数据库主要承担 report 索引和 processing 状态，大量数据留在本地文件/Parquet。

对本项目的启发（最能帮助控制数据库复杂度）：

- **数据库不必保存系统产生的一切，只保存需要查询、约束、关联、版本和运行控制的东西**。这正是第一版只保留 `company / security / source_access / document / processing_run / document_unit`（可选 `source_checkpoint`）的依据。
- 原始 PDF 和完整 parser artifact 放文件系统，DB 存路径、哈希、索引和内容快照；不需要先建“金融数据仓库”。

### 4. dlt-hub/dlt（只借思想，不引框架）

URL: https://github.com/dlt-hub/dlt

定位：通用数据加载框架，处理 schema 推断、嵌套 JSON、primary key、merge key、增量游标、schema evolution/contract、pipeline state、load lineage。

可借鉴的概念：`primary_key`、`cursor`、`load_id`、`pipeline_state`、`schema_contract`。

对本项目的映射：

- 公告唯一标识、最新公告时间/游标、每次同步批次、每个 provider 的同步状态、接口输入输出契约。
- 落到对象上就是 `source_access`（每次访问/批次）和可选 `source_checkpoint`（增量游标、最近成功时间、state）。

不引入框架的原因：第一版来源少（CNINFO / 标准数据 provider / PDF / 少量 Web/MCP），自己写很轻的 adapter + checkpoint 已足够；过早引入通用 ETL 框架会增加理解和调试成本。

### 5. cocoindex-io/cocoindex（只借思想，不引框架）

URL: https://github.com/cocoindex-io/cocoindex

定位：增量计算引擎，声明目标数据如何由源数据生成，按输入内容和转换代码的 hash 判断哪些部分需要重算，并保留 lineage。

可借鉴的字段：`input_hash`、`transform_version`、`output_hash`。

对本项目的映射（变更传播）：

- parser 版本 / Markdown 样式 / 单元边界 / page / bbox 变化**不触发 L3**；
- 真实文本、表格数字、来源值变化才触发相应单元重处理（见 canonical §13、财报方案 §14）。

不引入框架的原因：CocoIndex 偏复杂增量计算和 AI/RAG 数据流，对第一版过重；先用 `content_hash` + `processor_version` 表达即可。

---

## 二、披露侧抓取、下载与正文语义结构

### 6. Interstellar1217/CNInfoHedgeCrawler

URL: https://github.com/Interstellar1217/CNInfoHedgeCrawler

可借鉴点：`curl_cffi` 模拟浏览器 TLS 指纹；关键词/日期范围/分页/断点续爬；记录已下载 announcement id 去重；PDF URL 生成。

对本项目的启发：巨潮侧抓取的工程细节（分页、重试、延迟、断点、PDF URL）值得参考，落到 `source_access` 和 `document`；但不要采用它的关键词垂直窄化，我们要通用披露文件接入。

### 7. tr1s7an/CnInfoReports

URL: https://github.com/tr1s7an/CnInfoReports

可借鉴点：直接用 `hisAnnouncement/query` 查公告列表；`{column}_stock.json` 取证券代码；filter 覆盖 market/tabName/plate/category/industry/stock/searchkey/seDate；`adjunctUrl` 拼 `static.cninfo.com.cn` 下的 PDF URL。

对本项目的启发：作为巨潮接口参数样本（与 `cninfo-webapi-usage-reference.md` 对照）；它是脚本式下载，没有 filings database 设计，不作架构样本。

### 8. lichen6965/stock-fundamental-data

URL: https://github.com/lichen6965/stock-fundamental-data

可借鉴点：明确指出巨潮披露列表 API 主要给标题、时间、`adjunctUrl`，列表接口通常不返回正文；记录分页、限流、重试和 `column=szse` 覆盖沪深京检索的实测经验；强调 PDF 正文解析需另接。

对本项目的启发：巨潮公告列表只是入口（→ `source_access` / `document` 元数据），真正价值在后续 PDF 下载、解析、切成 `document_unit`。

### 9. jadchaar/sec-edgar-downloader

URL: https://github.com/jadchaar/sec-edgar-downloader

可借鉴点：简洁下载 API（按 form / ticker / 日期范围 / limit）；明确 user-agent / fair-access；下载器只负责可靠获取，不做复杂分析。

对本项目的启发：把“获取公告列表 / 下载文件”和“解析入库”分开；命令层可有简单入口。

### 10. alphanome-ai/sec-parser

URL: https://github.com/alphanome-ai/sec-parser

可借鉴点：把文档解析成符合视觉/语义结构的元素树（title / section / paragraph / table / parent-child）。

对本项目的启发：解析后不要只存一个全文字段；按标题层级形成 `heading_path` 和 `document_unit(text)`。但它面向 SEC HTML，不解决标准数据 provider/PDF/MCP/账本统一问题，只借语义结构思想。

---

## 三、PDF 解析参考

> 详细对比、license、平台支持和选型理由见 `pdf-parsing-investigation.md`，此处只列定位与角色。

### 11. opendatalab/MinerU（默认后端）

URL: https://github.com/opendatalab/MinerU

中文/复杂版面强（CJK SOTA），支持 macOS 14+ / Apple Silicon（MPS、`vlm-mlx`），输出 Markdown + `content_list.json`（含 page/bbox/type、表格 HTML、跨页表合并）。作为默认解析后端，从其结构化产物派生 `document_unit(text/table/qa)`。

### 12. docling-project/docling（第二后端，按需）

URL: https://github.com/docling-project/docling

MIT、`DoclingDocument`，适合对默认 parser 表现差的文档类型做交叉校验。不作默认后端。

### 13. camelot-dev/camelot + pdfplumber（text-PDF 表格 fallback，按需）

URL: https://github.com/camelot-dev/camelot

对 text-based PDF 表格输出 DataFrame，带 accuracy/whitespace/order/page 报告。用于第五节列出的**按需**表格复核与数字对账，不做全量逐表对账。

---

## 不建议直接采用为主架构

### OpenEDGAR

URL: https://github.com/LexPredict/openedgar

思路接近“从 EDGAR 构建数据库”，但项目较老、以 EDGAR/Django 为中心，对本地轻量 filings 服务偏重。

### 纯巨潮下载器

如 `Giant_Tide_Announcement_Download`、`CnInfoReports` 等。能快速确认巨潮接口和下载方式，对缓存/分类/分页/增量有参考价值；但多停留在“下载 PDF 到目录”或关键词垂直爬虫，缺少 `document/document_unit/processing_run` 的长期设计。

### RAG 型 SEC agent（向量库主导）

如 `wolfiesch/sec-edgar-agent` 这类 `PDF/HTML → chunk → embedding → 向量库 → 问答`、SQLite 只存 ingestion job 的形态。

不建议主用：本服务的目标不是“找几个相关 chunk 回答一个问题”，而是形成可冲突、可对账、可进入假设、可影响预测、可复盘的 claim（在 L2/L3）。向量检索以后可作候选发现工具，不应成为主数据库（见 canonical §11、§12）。

### EDGAR-Crawler

URL: https://github.com/lefterisloukas/edgar-crawler

按固定 item 抽取并输出标准 JSON，适合参考规则化 section extraction；但它是“下载 → item 切分 → JSON 输出”，不是长期运行的证据/预测系统，不作数据库主架构样本。

---

## 第一版建议路线

### 数据源层

- 标准数据：用 `dataset_registry` + provider adapter 封装标准数据 provider（首版 Wind），经 `Dataset API` 使用，记 `source_access`。
- 披露文件：先支持巨潮——证券代码列表、历史公告查询、PDF URL 拼接和下载、人工指定公司/分类/日期范围；以后再加港交所。

### 存储层

采用“**PostgreSQL 主库 + 文件系统**”（见 `database-selection.md`）：

- 原始 PDF 放 `raw_documents/`，parser artifact 放 `parser_artifacts/`（均在文件系统）；
- PostgreSQL 保存 `company / security / source_access / document / processing_run / document_unit`，可选 `source_checkpoint`；
- DB 存路径、哈希、索引字段和 `document_unit.payload` 内容快照；不建 block/chunk/cell/page/bbox 表。

### 解析层

- **MinerU 作为默认 PDF parser**；
- Docling 作为复杂版面/对照的第二后端（按需）；
- Camelot/pdfplumber 作为 text-PDF 表格 fallback 与按需数字对账；
- 每次解析写 `processing_run`，不覆盖旧结果，保留 active run。

### API / 查询层

先做 Python API（Dataset API + Filing API），不急着做 HTTP 服务：

```python
# 标准数据
dataset("financial.income_statement").get(company="600519", period="2025A")

# 披露文件
filing = company("600519").filings(filing_type="annual_report", period="2025A").latest()
filing.text_units()
filing.tables()
filing.qa_items()
```

REST、MCP 以后在这两个接口外加适配，不重新设计数据库。

## 当前取舍

不要一开始做：

- 全市场全量抓取；
- 完整 HTTP API；
- 向量数据库 / 图数据库；
- 自动 claim 抽取与预测逻辑（属 L2/L3+）；
- 把标准数据 provider 全量镜像进本地表；
- 为每种附注表建一张 SQL 表；
- page/block/cell 镜像与全量双 parser 对账。

先把一个闭环做硬：

```text
标准数据：dataset_registry → provider adapter（首版 Wind）→ Dataset API → source_access（+ as-of 快照）
披露文件：巨潮公告列表 → PDF 下载 → 原文保存(+hash) → document/processing_run
        → MinerU 解析 → 切成 document_unit(text/table/qa)
        → 可按 公司/报告期/公告类型/heading_path/semantic_key/title/unit_id 查询
两条路径在 L2 汇合，抽取 claim / 事件 / 口径 / 冲突。
```
