# disclosure_anchor 数据库选型调研

调研时间：2026-06-16

输入文档：

- `docs/architecture/service-purpose.md`
- `docs/architecture/pdf-parsing-investigation.md`
- `docs/architecture/cninfo-webapi-usage-reference.md`

本文回答三个问题：

1. `disclosure_anchor` 第一版数据库应该选什么？
2. "Postgres 对 AI 好"这个说法是否成立、成立到什么程度？
3. 财报解析成 Markdown 后，正文、表格、chunk 应该切到什么粒度？

## 结论

推荐把 **PostgreSQL 作为主数据库**，把原始 PDF 和大型解析中间产物继续放在本地文件系统，必要时再用 DuckDB 做分析副引擎。

第一版不要先上独立向量数据库，也不要把 DuckDB/SQLite 当主账本。

推荐形态：

```text
local filesystem
  raw_files/                 # 原始 PDF / 附件 / H5 保存件
  parser_artifacts/           # MinerU/Docling 原始 md/json/html/table 输出

PostgreSQL
  company                     # 公司和证券基础信息
  filing                      # 公告/财报主记录、来源、日期、类型、哈希、路径
  filing_file                 # PDF/附件/H5 文件记录
  filing_text_block           # parser 原始块：标题/段落/列表/公式等，带页码/bbox/order
  filing_text_chunk           # 面向检索/AI 的派生 chunk，带 heading_path/page/order
  filing_table                # 表格级记录，带页码、bbox、HTML/JSON、质量标记
  filing_table_cell           # 需要精细化时的单元格原值、行列、规范化值
  processing_run              # 下载/解析/重跑/校验的版本、状态、错误
  optional: text_search index # 关键词/全文检索索引
  optional: embedding vector  # 语义检索向量，先作为派生索引，不是事实来源

DuckDB, optional
  read-side analytics over Parquet/CSV/JSON exports
```

把握等级：

- 高把握：主账本用 PostgreSQL 比 SQLite/DuckDB/独立向量库更适合当前服务目的。
- 高把握：Markdown 适合正文展示和检索派生，不适合做表格事实来源。
- 中高把握：第一版可以把 pgvector 留在 PostgreSQL 内部，不急着拆到 Qdrant/Milvus/Chroma。
- 中等把握：中文全文检索的最终效果要实测；PostgreSQL 内置全文检索很好，但中文财报需要额外分词/三元组/外部搜索方案验证。

## 需求映射

`service-purpose.md` 里的数据库不是一个临时索引，而是 filings database/API。它至少要稳定回答：

- 某家公司有哪些公告和财报入库；
- 某份公告的元数据、原始文件路径、哈希、来源 URL、公告日期、报告期；
- PDF 文本、章节、段落、item；
- 表格、页码、位置、单元格原值；
- 哪次解析/下载成功或失败、使用哪个 parser 版本；
- 后续程序能按公司、日期、公告类型、报告期、关键词、章节、表格直接查询。

这几个要求决定了主数据库需要优先满足：

1. **关系型约束**：公司、证券、公告、文件、解析结果、处理运行之间有明确关系。
2. **事务和去重**：下载、哈希、解析状态、重跑版本不能乱。
3. **并发写入**：后续可能同时跑 CNINFO 同步、PDF 下载、parser、表格校验、API 查询。
4. **半结构化承载**：CNINFO 返回字段、MinerU/Docling block JSON、表格 HTML/JSON 都会变化，需要 `jsonb` 或等价能力。
5. **检索扩展**：先支持元数据过滤和关键词搜索，再扩展向量/混合检索。
6. **本地 API 化**：未来服务/API 读写同一个稳定数据库，而不是每次扫文件夹。

PostgreSQL 正好覆盖这些需求；SQLite 覆盖本地简单账本；DuckDB 覆盖分析；向量库覆盖语义近邻检索，但它们单独都不适合作为这个服务的事实主库。

## 候选方案对比

| 候选 | 适合角色 | 优点 | 主要问题 | 本项目结论 |
|---|---|---|---|---|
| PostgreSQL | 主数据库 / API 后端 | ACID、约束、并发、JSONB、索引类型、全文检索、扩展生态、pgvector 可选 | 要运行服务；中文全文检索需要额外方案；pgvector 不是无限规模向量系统 | **推荐作为主库** |
| SQLite | 本地原型 / 测试 fixture / 单机缓存 | 零运维、单文件、可靠、足够快 | 单库同一时刻只有一个 writer；多进程/多机器/高并发写不合适；后续迁移成本 | 不做长期主账本 |
| DuckDB | 分析副引擎 / Parquet 查询 / 批量校验 | 嵌入式 OLAP、直接读 Parquet/JSON/CSV、分析很强 | 官方并发模型偏单进程；不是 OLTP 主库 | 作为 read-side 工具，不做主账本 |
| 独立向量库 | 大规模语义检索 sidecar | 专门做向量 ANN、过滤、扩展、部署形态成熟 | 需要和主库同步；事实来源会分裂；第一版复杂度过高 | 等向量规模和延迟需求证明后再引入 |
| Elasticsearch/OpenSearch | 关键词/中文检索 sidecar | 文本检索强，中文 analyzer 生态成熟 | 又是一个同步系统；不是事实主库 | 可作为后续检索增强，不是第一版主库 |

## 为什么主库选 PostgreSQL

### 1. 它最像这个服务需要的"本地 filings database"

这个服务要保存的是有强关系的事实记录，不只是文档 blob：

```text
company -> filing -> filing_file
                  -> filing_text_block -> filing_text_chunk
                  -> filing_table -> filing_table_cell
                  -> processing_run
```

这些对象需要唯一约束、外键、状态流转、版本记录、可重跑和可审计。PostgreSQL 是成熟的事务型关系数据库；相比之下，向量库和搜索引擎更像派生索引，不适合承载事实账本。

### 2. JSONB 适合保存"有结构但会变"的解析/接口字段

CNINFO 字段、MinerU `content_list.json`、DoclingDocument、表格 HTML/JSON 都会随着版本变化。PostgreSQL 的 `jsonb` 能验证 JSON、支持二进制分解存储、函数/操作符和 GIN 索引。官方文档也提醒，关系模型和 JSON 可以共存，并建议 JSON 文档保持可预测结构。

本项目建议：

- 稳定查询字段升成列：`filing_id`、`company_id`、`announcement_date`、`report_period`、`page_start`、`order_index`、`parser`、`parser_version`。
- 原始/变动字段进 `jsonb`：CNINFO 原始 payload、parser block metadata、bbox、表格解析报告。
- 大文件不要塞 DB：PDF、完整 parser artifact、可能很大的 HTML/Markdown 备份放文件系统，DB 存路径、哈希和摘要字段。

### 3. 它能先做关键词检索，再做向量/混合检索

PostgreSQL 内置全文检索支持 `tsvector`、`tsquery`、ranking、GIN 索引；同时 `pg_trgm` 是官方附带扩展，可以做 trigram 相似度和非左锚定 `LIKE`/正则加速。

但要注意中文：

- 英文型 `to_tsvector('english', ...)` 不等于中文财报搜索。
- A 股财报需要实测中文分词。可选路线包括 `simple`/`pg_trgm` 粗检索、`pg_jieba`/`zhparser` 这类中文分词扩展，或后续接 Elasticsearch/OpenSearch。
- 所以第一版可以先把文本块和 chunk 结构存对；中文检索质量作为可替换索引层验证，不要让 schema 依赖某个分词器。

### 4. pgvector 让"PG 对 AI 好"有现实含义

"Postgres 对 AI 好"不是因为 Postgres 自己会理解财报，而是因为：

- pgvector 可以把 embedding 存在同一个事务数据库里；
- 它支持 exact nearest neighbor，也支持 HNSW/IVFFlat 近似索引；
- 它可以和普通 SQL 条件一起用，例如先限制公司、日期、公告类型、章节、parser 版本，再做语义相似度；
- 它可以和 PostgreSQL 全文检索做 hybrid search。

这对本项目尤其重要，因为财报检索不是单纯"找语义相近文本"，而是经常带硬过滤：

```text
公司 = 300066
报告期 = 2026Q1
公告类型 = 季报
章节 = 管理层讨论 / 财务报表附注
页码范围 / parser_version / needs_review
```

把 metadata、chunk、embedding 放在一个主库里，可以减少"主库记录更新了，向量库没同步"的问题。

限制也要写清楚：

- pgvector 的 HNSW 查询性能好但建索引慢、占内存；IVFFlat 建索引更轻但召回/速度取舍不同。
- pgvector 支持的 `vector` 维度有上限，超大规模、多向量、多模态、高 QPS 语义检索可能仍然需要专门向量库。
- pgvector 不替代 chunking、embedding model、reranker、评测集；这些 AI 质量问题不由数据库自动解决。

结论：**PG 对 AI 好，在本项目里成立；但成立点是"统一事实库 + 元数据过滤 + 可选向量索引"，不是"数据库替代 AI 检索工程"。**

## 为什么不把 SQLite 当主库

SQLite 很适合低运维本地应用。官方文档明确说它强调经济、效率、可靠、独立、简单，适合本地文件型应用；如果数据小、写并发低、低于 TB 级，SQLite 往往很香。

但当前目标不是一个临时脚本，而是本地 filings database/API。后续很自然会出现：

- 下载器写 `filing` / `filing_file`；
- parser 写 `processing_run` / `filing_text_block` / `filing_table`；
- 表格校验器更新 `needs_review`；
- API/查询进程同时读；
- 可能还有 embedding 任务写 `filing_text_chunk.embedding`。

SQLite 的官方选择指南也说，多个并发 writer 或数据跨网络/多进程时，client/server 数据库通常更合适。第一版如果为了省安装用 SQLite，之后大概率要迁移 schema 和查询语义。

因此：

- SQLite 可用于单元测试、fixture、临时 cache。
- 不建议把 SQLite 作为这个服务的目标主库。

## 为什么不把 DuckDB 当主库

DuckDB 很适合本项目的另一个侧面：分析。

它可以直接读 Parquet/JSON/CSV，读 Parquet 支持 projection/filter pushdown，非常适合后续做：

- 导出 `filing_table_cell` 到 Parquet 后批量分析；
- 对表格数字做 cross-check；
- notebook/研究脚本临时聚合；
- 从 parser artifact 或中间文件快速抽样。

但 DuckDB 官方并发文档说明，它的 read-write 模式主要是单进程内并发；多进程写 DuckDB 原生库需要额外协议，2026-06 时相关远程协议仍处于 beta/演进阶段。它的长处是 OLAP，不是承载多任务 ingest/parser/API 的主账本。

因此：

- DuckDB 应作为 **read-side analytics engine**；
- 可以从 PostgreSQL 导出 Parquet，或直接读文件系统里的中间产物；
- 不建议让 DuckDB 管 `processing_run`、下载状态、去重、API 主查询。

## 为什么第一版不单独上向量库

Qdrant/Milvus/Chroma/LanceDB 这类系统对大规模向量搜索很有价值。以 Qdrant 为例，它围绕 collection/point/vector/payload 组织数据，支持 payload 过滤、dense/sparse/hybrid 检索、HNSW 和扩展部署。

但第一版不建议把它作为必需组件：

1. 本服务的事实主数据是公告元数据、文件、parser 输出、处理状态，不是向量。
2. 向量索引一定是派生物：embedding model 变了就要重算。
3. 单独上向量库会引入同步、删除、重跑、权限、备份、恢复的一整套额外问题。
4. 目前还没有证明本地 filings 文本规模会超过 pgvector 的舒适区。

推荐路线：

- 第一版：PostgreSQL 主库；先设计 `filing_text_chunk`，embedding 字段可以先留空或放后续迁移。
- 第二阶段：用 pgvector 做小规模语义检索和 hybrid search。
- 只有当出现明确证据时再拆 sidecar：例如向量条数达到千万级、高 QPS、复杂 payload filtering 性能不足、多模型多向量召回需要专门引擎。

## Markdown 财报应该切到什么程度

结论：**Markdown 可以作为正文的可读/检索派生格式，但不能作为唯一事实来源。**

根据 `pdf-parsing-investigation.md`，MinerU/Docling 的结构化中间产物才是入库依据。Markdown 只适合正文和标题层级，不适合保真保存财务表格。

推荐分层：

```text
parser artifact
  content_list.json / DoclingDocument / table html-json
      ↓
filing_text_block
  parser 原始 block 级记录：title/text/list/equation/table_ref
  保留 page_idx、bbox、order_index、heading_level、raw_text、parser metadata
      ↓
filing_text_chunk
  面向搜索/embedding 的派生 chunk
  保留 chunk_text、heading_path、page_start/page_end、source_block_ids、token_count

filing_table
  表格级记录：caption、page、bbox、html/json、parser、quality flags
      ↓
filing_table_cell
  可选细化：row_index、col_index、raw_value、normalized_value、unit、is_header、confidence
```

正文切分建议：

- 第一层：按 parser block 入库。标题、段落、列表、公式、表格引用分开存，保留页码和 bbox。
- 第二层：按财报章节重组。通过 heading_path 表达"第三节 管理层讨论与分析 > 主营业务分析"这种层级。
- 第三层：生成检索 chunk。chunk 不要直接按固定字符数切 Markdown，而应优先按标题/段落边界切；太长再按 token/字数拆。
- chunk 应保存 `source_block_ids`，这样 AI 找到 chunk 后可以回到页码、bbox、原 PDF 和 parser run。

表格切分建议：

- 不要把财务表格只存成 Markdown 管道表。合并单元格、多级表头、跨页、脚注、单位、负数括号会丢信息。
- `filing_table` 至少保存 HTML 或结构化 JSON、页码、bbox、parser 版本、质量标记。
- 对三大报表、附注表格、核心经营数据表，逐步落到 `filing_table_cell`。
- 数字规范化只做派生字段，原始字符串必须保留。

面向 AI 的 chunk 建议：

- 正文 chunk：从 `filing_text_block` 派生，保留章节路径和页码。
- 表格 chunk：不要直接 embedding 整张大表；先用表名、表头、关键行、单位、页码生成可检索摘要，同时保留 `table_id`。
- 长期可以为 `filing_table` 生成多个表格视图：原始 HTML、cell JSON、可读 Markdown 摘要、面向 embedding 的 textual summary。

## 第一版实施建议

第一版目标不是把所有高级检索一次做完，而是选一个不需要推倒重来的主库。

建议顺序：

1. **PostgreSQL 主库**：先落公司、公告、文件、处理运行、文本块、表格。
2. **文件系统存大对象**：PDF、完整 Markdown、完整 parser JSON、表格 HTML 大文件放本地目录；DB 存路径、哈希、parser run。
3. **结构化优先**：稳定字段列化，变动字段 `jsonb`，不要只有一坨全文。
4. **关键词检索先轻量**：先有标题/公司/日期/类型/章节/page 查询；再加 `pg_trgm` 或 `tsvector`。
5. **中文检索单独验证**：拿 20-50 个真实中文查询测试 `simple`、`pg_trgm`、`pg_jieba/zhparser` 或外部搜索方案。
6. **向量检索后置但不封死**：先设计 `filing_text_chunk`，之后加 `embedding_model`、`embedding`、`embedded_at`、`embedding_run_id`。
7. **DuckDB 作为分析工具**：当表格 cell 或 parser artifact 变多时，导出 Parquet 给 DuckDB 做批量校验和 notebook 分析。

第一版不建议：

- 把原始 PDF 作为 bytea 大字段塞进 Postgres。
- 只存 Markdown，不存 block/page/bbox/table/cell。
- 先上 Qdrant/Milvus/Chroma 再回头补关系型主库。
- 用 DuckDB 管下载/解析状态。
- 为了省事先用 SQLite 做主库，除非明确承认它只是 throwaway prototype。

## 仍需实测的问题

这些问题不阻止选 PostgreSQL，但会影响后续 schema 和索引细节：

1. **中文全文检索质量**：PostgreSQL 内置能力够不够，还是要 `pg_jieba`/`zhparser`/外部搜索？
2. **embedding 模型和 chunk 大小**：中文财报的最佳 chunk 长度要靠真实问答/召回样例定，不应现在拍死。
3. **表格 cell 规模**：如果全市场多年财报都 cell 化，Postgres 主库是否保留全部 cell，还是冷热分层到 Parquet？
4. **部署方式**：本地 `brew services`、Docker、还是项目脚本启动 Postgres，需要等实现计划确定。
5. **备份与迁移**：主库、raw files、parser artifacts 三者要保持一致备份，后续要定义 manifest/checksum。

## 参考来源

- PostgreSQL 18 文档：Full Text Search，`tsvector`/GIN/indexed search  
  https://www.postgresql.org/docs/current/textsearch.html  
  https://www.postgresql.org/docs/current/textsearch-tables.html
- PostgreSQL 18 文档：JSON/JSONB 设计与索引  
  https://www.postgresql.org/docs/current/datatype-json.html
- PostgreSQL 18 文档：索引类型  
  https://www.postgresql.org/docs/current/indexes-types.html
- PostgreSQL 18 文档：`pg_trgm`  
  https://www.postgresql.org/docs/current/pgtrgm.html
- pgvector 官方仓库：向量类型、HNSW/IVFFlat、hybrid search  
  https://github.com/pgvector/pgvector
- SQLite 官方选择指南与 FTS5  
  https://www.sqlite.org/whentouse.html  
  https://www.sqlite.org/fts5.html
- DuckDB 官方文档：数据导入、Parquet、JSON、FTS、并发模型  
  https://duckdb.org/docs/current/data/overview  
  https://duckdb.org/docs/current/data/parquet/overview  
  https://duckdb.org/docs/current/data/json/overview  
  https://duckdb.org/docs/current/core_extensions/full_text_search  
  https://duckdb.org/docs/current/connect/concurrency
- Qdrant 官方文档：向量检索、payload filtering、scaling  
  https://qdrant.tech/documentation/overview/  
  https://qdrant.tech/documentation/search/filtering/
- PostgreSQL 中文分词扩展参考（需后续实测，不作为第一版强依赖）  
  https://github.com/jaiminpan/pg_jieba  
  https://github.com/amutu/zhparser
