# 开源参考项目调研

本轮目标：为 `disclosure_anchor` 的第一版实现找可借鉴的 GitHub 项目。服务目标不是单纯下载 PDF，而是建设一个本地上市公司公告 / 财报数据库：原文可保存，元数据可查询，正文、章节、表格、附件和处理状态可被程序直接读取。

## 结论

最值得借鉴的是几类成熟设计，而不是直接复制某一个项目：

1. **本地索引 + 原始文件 / 派生数据分层**：借鉴 `secfsdstools`。
2. **Company / Filing / typed object 查询接口**：借鉴 `edgartools`。
3. **section / item 级正文切分**：借鉴 `edgartools` 和 `sec-parser`。
4. **下载状态、去重、断点续跑、处理日志**：借鉴 `CNInfoHedgeCrawler` 和 `sec-edgar-downloader`。
5. **PDF 转 Markdown/JSON、表格抽取**：优先评估 `Docling` 和 `MinerU`，必要时用 `Camelot` 做 text-based PDF 表格 fallback。
6. **巨潮接口参数和公告列表字段**：参考 `CnInfoReports`、`CNInfoHedgeCrawler`、`stock-fundamental-data`，但不要照抄成只有文件下载的脚本。

## 推荐重点参考

### 1. dgunning/edgartools

URL: https://github.com/dgunning/edgartools

定位：SEC EDGAR filings 的 Python structured-data library。

可借鉴点：

- `Company` / `Filing` 作为核心对象，而不是散落的文件路径。
- filing 可以变成 typed object、DataFrame、clean text。
- 支持 XBRL financial statements、8-K items、section extraction、full-text/RAG 友好文本。
- 设计目标很接近“从披露文件直接拿可用数据”。

对本项目的启发：

- 第一版也应该定义 `Company`、`Filing`、`FilingText`、`FilingTable` 这些稳定概念。
- API 使用体验应接近：

```python
db.company("600519").filings(type="年度报告").latest()
db.filing(id).text_items()
db.filing(id).tables()
```

不直接采用的原因：

- 它面向 SEC/EDGAR 和 XBRL，不适配巨潮 PDF 公告数据源。
- 但对象模型和 typed output 值得学习。

### 2. HansjoergW/sec-fincancial-statement-data-set

URL: https://github.com/HansjoergW/sec-fincancial-statement-data-set

定位：SEC Financial Statement Data Sets 的本地下载、Parquet 转换、SQLite 索引工具。

可借鉴点：

- 先把远端数据下载到本地硬盘。
- 原始批量数据转换为更快读取的本地格式。
- SQLite 建索引表，记录每份 report 的唯一 ID、公司、form、filed date、period、路径、URL。
- 处理状态单独入库，可以重建索引。

对本项目的启发：

- 这是最像 `disclosure_anchor` 的底层数据工程形态。
- 我们也应分成：

```text
raw_files/       # 原始 PDF / HTML / 附件
processed/       # 文本、表格、markdown/json/parquet
ledger.db        # company / filing / file / text / table / processing_run 索引
```

- 不要把数据库当唯一存储；数据库管索引和结构化结果，硬盘管大文件和中间产物。

### 3. alphanome-ai/sec-parser

URL: https://github.com/alphanome-ai/sec-parser

定位：把 SEC EDGAR HTML 文档解析成符合视觉/语义结构的元素树。

可借鉴点：

- 文档不只是纯文本；应该保留标题、段落、表格等语义元素。
- 树状结构适合后续 section/item 查询和 RAG。

对本项目的启发：

- 巨潮 PDF 解析后也不要只存一个全文字段。
- 应存 `filing_text` 或 `filing_item`：

```text
filing_id, item_type, heading, page_start, page_end, order_index, text
```

- 财报可以先粗切：封面、目录、重要提示、管理层讨论、财务报表、附注等；公告可以先按标题/页/段落粗切。

### 4. jadchaar/sec-edgar-downloader

URL: https://github.com/jadchaar/sec-edgar-downloader

定位：SEC EDGAR filing 下载器。

可借鉴点：

- 简洁的下载 API：按 form、ticker/CIK、日期范围、limit 下载。
- 明确 user-agent / fair access policy。
- 下载器只负责可靠获取，不负责复杂分析。

对本项目的启发：

- `disclosure_anchor` 也应把“获取公告列表 / 下载文件”和“解析入库”分开。
- 命令层可以有简单入口：

```bash
disclosure-anchor ingest --code 600519 --type 年度报告 --start 2020-01-01
```

### 5. Interstellar1217/CNInfoHedgeCrawler

URL: https://github.com/Interstellar1217/CNInfoHedgeCrawler

定位：巨潮资讯上市公司公告自动爬取工具，偏“套期保值”等关键词场景。

可借鉴点：

- 使用 `curl_cffi` 模拟浏览器 TLS 指纹。
- 支持关键词、日期范围、分页、断点续爬。
- 用 SQLite 保存元数据，同时 CSV 兜底。
- 记录已下载 announcement id，避免重复下载。
- 将 PDF 下载和字段提取串起来。

对本项目的启发：

- 巨潮侧抓取可以参考其工程细节：分页、重试、延迟、SQLite 状态、PDF URL 生成。
- 但不要采用它的业务窄化：它是垂直关键词/推送工具，我们要做通用公告 / 财报数据库。

### 6. tr1s7an/CnInfoReports

URL: https://github.com/tr1s7an/CnInfoReports

定位：巨潮资讯网公告查询和下载脚本。

可借鉴点：

- 直接使用 `http://www.cninfo.com.cn/new/hisAnnouncement/query` 查询公告列表。
- 使用 `http://www.cninfo.com.cn/new/data/{column}_stock.json` 获取证券代码数据。
- filter 字段覆盖 market、tabName、plate、category、industry、stock、searchkey、seDate。
- `adjunctUrl` 可拼出 `http://static.cninfo.com.cn/` 下的 PDF URL。

对本项目的启发：

- 可作为巨潮接口参数的参考样本。
- 不适合作为架构样本：它主要是脚本式下载，没有本地 filings database 设计。

### 7. lichen6965/stock-fundamental-data

URL: https://github.com/lichen6965/stock-fundamental-data

定位：A 股基础数据研究样例，合并 CNINFO 披露列表和 Baostock 结构化数据。

可借鉴点：

- 明确指出巨潮披露列表 API 主要给标题、时间、`adjunctUrl`，列表接口通常不返回 PDF 正文。
- 记录了巨潮分页、限流、重试和 `column=szse` 覆盖沪深京检索的实测经验。
- 强调 PDF 正文解析需要另接 PDF/XBRL/商业授权。

对本项目的启发：

- 巨潮公告列表只是一层入口；真正价值在后续 PDF 下载、解析、入库。
- 第一版应把“列表元数据”和“PDF 解析结果”分表保存。

### 8. docling-project/docling

URL: https://github.com/docling-project/docling

定位：文档转换工具，可将 PDF 等格式解析成结构化表示。

可借鉴点：

- 支持 PDF 转 Markdown/JSON。
- 能处理文本、表格、版面结构，并有 Python API / CLI。
- 社区活跃，适合先做第一版 PDF 解析候选。

对本项目的启发：

- 第一版 PDF 解析可以优先试 Docling：把每份 PDF 转成 JSON/Markdown，再落到 `filing_text` / `filing_table`。
- 需要保留 parser version 和 parsing_run，方便后续重跑。

### 9. opendatalab/MinerU

URL: https://github.com/opendatalab/MinerU

定位：高精度文档解析引擎，输出 Markdown/JSON，支持 OCR、表格、复杂版面。

可借鉴点：

- 对中文、多栏、扫描件、复杂 PDF 更友好。
- 输出 Markdown/JSON，可作为本地 parsing backend。
- 支持 CLI / API / Docker。

对本项目的启发：

- 如果 Docling 对中文财报或扫描 PDF 效果不稳，应把 MinerU 作为第二个 parser backend。
- 数据库设计要允许同一份 filing 有多个 parser run 和多个解析版本。

### 10. camelot-dev/camelot

URL: https://github.com/camelot-dev/camelot

定位：PDF 表格抽取库。

可借鉴点：

- 对 text-based PDF 表格可直接输出 DataFrame / CSV / JSON / SQLite。
- 有解析报告，包括 accuracy、whitespace、order、page。

对本项目的启发：

- 可以作为表格抽取 fallback 或对照工具。
- `filing_table` 里应保留 table parser、page、accuracy/report 等质量字段。

## 不建议直接采用为主架构

### OpenEDGAR

URL: https://github.com/LexPredict/openedgar

优点：目标很接近“从 EDGAR 构建数据库”，思路值得看。

不建议主用原因：

- 项目较老，GitHub 上显示提交和维护活跃度不如 `edgartools`、`Docling`、`MinerU`。
- 以 EDGAR/Django 形态为中心，对本地轻量 filings database 来说偏重。

### 纯巨潮下载器

包括 `Giant_Tide_Announcement_Download`、`CnInfoReports` 等。

优点：

- 能快速确认巨潮接口和下载方式。
- 对缓存、分类、分页、增量更新有参考价值。

不建议主用原因：

- 多数停留在“下载 PDF 到目录”或“关键词垂直爬虫”。
- 缺少通用 filings database、parser version、text/table/item records、processing state 的长期设计。

## 第一版建议路线

### 数据源层

先支持巨潮：

- 公司/证券代码列表；
- 历史公告查询；
- PDF URL 拼接和下载；
- 人工指定公司、公告分类、日期范围。

以后再加港交所。

### 存储层

采用“硬盘文件 + SQLite 索引”的第一版：

- 原始 PDF 永远保留在硬盘；
- SQLite 保存 company、filing、filing_file、filing_text、filing_table、processing_run；
- 大型解析结果可后续放 JSON/Parquet，SQLite 保存路径和索引字段。

### 解析层

第一版：

- Docling 作为默认 PDF parser 候选；
- MinerU 作为中文/复杂版面候选；
- Camelot 作为 text-based PDF 表格 fallback；
- 每次解析都写 processing_run，不覆盖旧结果。

### API/查询层

先做 Python API / CLI，不急着做 HTTP 服务：

```python
db.filings(code="600519", category="年度报告", start="2020-01-01")
db.filing(filing_id).text_items()
db.filing(filing_id).tables()
db.filing(filing_id).files()
```

CLI 可先做：

```bash
disclosure-anchor ingest --code 600519 --category 年度报告 --start 2020-01-01
disclosure-anchor list --code 600519 --category 年度报告
disclosure-anchor show-text --filing-id ...
disclosure-anchor show-tables --filing-id ...
```

## 当前取舍

不要一开始做：

- 全市场全量抓取；
- 完整 HTTP API；
- 向量数据库；
- 自动 claim 抽取；
- 预测逻辑；
- 多数据源大一统。

先把一个闭环做硬：

```text
巨潮公告列表
→ PDF 下载
→ 原文保存
→ 元数据入 SQLite
→ PDF 解析为 text/table records
→ 可按公司/日期/分类/报告期查询
```
