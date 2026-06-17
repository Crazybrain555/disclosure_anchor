# disclosure_anchor raw 到 L2-ready 锚层方向

调研时间：2026-06-17

> 文件名仍是 `raw-to-l3-data-layer-direction.md`（避免改动已有引用），但方向已收口为
> **raw → L2-ready 锚**：本服务只做 L1，不产出 L3 数据。

输入文档：

- `docs/reference/投研预测引擎顶层框架协议_v0.5.md`
- `docs/architecture/service-purpose.md`
- `docs/architecture/open-source-references.md`
- `docs/architecture/database-selection.md`
- Financial Datasets `filings/items`: https://docs.financialdatasets.ai/api/filings/items

## 结论

`disclosure_anchor` 是**单一的 L1 披露锚归档层**，不是“raw + L3-ready”两层能力的组合。

按 v0.5：解析、切分、表格抽取、页码/段落/表格定位本来就是 L1 自维护资产（§2.2.1）。所以本服务内部确实有一条从原文到精简锚的派生梯度，但**整条梯度都关在 L1 里，上界停在“寻址 + 发现重点”，绝不跨进“判断 + 事实”**。判断与事实（规范化指标、claim、对账、采信）是 L2/L3 的活。

L1 内部分成两段：

1. **raw 段**：原文、元数据、下载来源、文件哈希、parser run、parser artifact。确定性、可复现、只追加、不可变。
2. **锚段（仍属 L1）**：把原文切成可独立引用的单元（section / item / block / table / cell），每个单元有稳定 id + 精确定位，再加结构标签、主题标签、检索索引。

衡量标准不是“我产出了多少事实”，而是 **L2/L3 好不好抓、好不好发现重点**。交付对象是 **L2，不是 L3**。

技术选型不变：

- PostgreSQL 做主库；
- 文件系统保存 PDF、附件、完整 parser artifact；
- 章节、段落、表格、单元格、定位、标签、索引都要有结构化记录；
- 每个单元都能被精确寻址、可被 L2 的 evidence link 锚回；
- embedding / full-text search 只作为查找候选资料的派生索引，不是事实来源；
- 第一版不要把核心方向做成 RAG，也不要先上专门图数据库。

Obsidian 式图谱适合做交互和理解方式，但第一版不建议把事实源做成 Markdown 链接库；而且“事实关系网”本身属于 L2/L3，L1 只负责把每个锚点切得可被关系网引用。

## 不可变 vs 可重生成——真正的分界线

L1 内两段性质不同，这个缝才是值得保留两段区分的真正理由（不是因为它们是两种数据）：

| | raw 段 | 锚段 |
| --- | --- | --- |
| 是什么 | 文档原样 | 文档被切好、标好、可寻址 |
| 怎么来 | 下载即定 | parser 跑一遍，确定性、可复现 |
| 可变性 | 不可变、只追加 | parser 升级可重跑、可版本化 |
| 但都不做 | — | 不规范化、不下结论、不判重要性 |

锚段重跑同一 parser 永远得到同一结果；它升级的是“切得多准、标得多细”，而不是“判断对不对”。判断在 L2 才开始。

## 参考对象给我们的启发

### Financial Datasets `filings/items`

值得学的不是 SEC 字段本身，而是数据产品形态：它把一份 filing 变成可按 ticker、filing type、year、quarter、item、accession number 查询的对象，返回 metadata、items、exhibit 文本，并把慢解析做成后台缓存和重试。

对本项目（只做 L1）的启发：

- 一份公告不是一个 PDF 路径，而是 `filing -> item/section -> text/exhibit/table`，每层都可寻址。
- API 应允许按公司、公告类型、报告期、章节、item、表格直接拿锚，L2 不用自己再切 PDF。
- parser 结果应缓存并版本化，而不是每次查询都重新解析。
- 没解析好的文件应有明确 processing status，而不是静默失败。
- 注意：Financial Datasets 把 item 内容直接当“可用数据”返回，但它不替你判断“这条对预测是否重要”。我们的边界与它一致——到“可取到分段内容”为止。

### 开源项目参考

`open-source-references.md` 里的项目可归纳成四类经验，全部落在 L1：

- `secfsdstools`：本地文件和索引分层，raw 不一定全塞数据库。
- `edgartools`：用户应面对 Company / Filing / Item / Statement 这种对象，而不是文件夹。
- `sec-parser`：文档应保留语义结构，不只是一坨全文。
- Docling / MinerU / Camelot：PDF 解析要允许多 parser、多版本和质量字段。

所以第一版重点不是“爬得多”，也不是“抽得深”，而是把一份披露文件变成可长期复用、可被 L2 精确寻址的数据库对象。

## 数据层分层（L1 内部两段 + 一份 L1→L2 交接契约）

本服务只实现下面的 A、B 两段和它们之间的交接契约。C、D 列出来只是为了标清边界——**它们属于 L2/L3，本服务不产出**，这里只为它们留下可精确锚回的落点。

### A. raw anchor layer（L1，本服务实现）

目的：保证最底层可复查、可重跑、可证明来源。

对象：

- `source`：CNINFO、交易所、港交所、手工导入等来源；
- `source_record`：远端 API 或网页返回的公告索引记录；
- `raw_file`：PDF、附件、H5 保存件、文件哈希、路径、大小；
- `filing`：公告 / 财报主记录；
- `processing_run`：下载、解析、重跑、失败、耗时、parser 版本；
- `parser_artifact`：Docling/MinerU/Camelot 输出的大 JSON/Markdown/HTML 路径；
- `source_ref`：对外部来源（含 Wind/Tushare 等 provider）的访问登记，只记“来自哪里、何时、以什么形式”。

原则：

- raw 文件在硬盘，数据库保存路径、哈希和来源。
- 同一文件可多次 parser run，不能覆盖旧解析结果。
- `source_record` / `source_ref` 要保留远端 ID、query params、获取时间，方便以后解释为什么当时取到了这条资料。

### B. addressable anchor layer（L1，本服务实现）

目的：让 L2 不用打开 PDF、也不用自己再切，就能读正文、章节、表格、附件，并“一看就知道重点在哪”。

寻址对象：

- `filing_item`：按章节、item、公告内结构拆分的正文单元；
- `text_block`：标题、段落、列表、脚注、问答等 parser block；
- `table`：表格级记录，含页码、bbox、caption、HTML/JSON、parser 质量；
- `table_cell`：行列、原始值、是否表头、定位（**保留结构，不做口径规范化**）；
- `attachment`：附件文件、附件正文、附件和主 filing 的关系。

发现对象（机械标注，不下结论）：

- `structural_tag`：标出单元是“三大报表 / 管理层讨论 / 分产品收入表 / 投关问答”等；
- `topic_tag`：产能 / 价格 / 订单 / 客户 / 风险等机械主题分类；
- `query_index`：全文 / 关键词 /（可选）embedding，只作候选发现。

原则：

- 每个单元有稳定 id + 精确定位，保证 L2 抽出的任何 claim 都能锚回 G0。
- Markdown 可保留为展示格式，但不是唯一事实源。
- 表格必须保留结构化原始值；财务表、经营数据表、分产品/地区/客户表不应只存 Markdown 管道表。
- 投资者关系记录要把 Q&A、参与机构、调研时间、交流形式拆成可查询字段，同时保留原文块。
- 标签是“机械标注”：标“这段在谈价格”可以，判“价格利空、影响预测”不可以。

### C. normalized fact layer（属 L2，本服务不产出）

L2 才开始把锚变成“事实”：`metric_definition` / `metric_observation`（值、period、unit、currency、scale、accounting_basis、source_type、confidence）、`segment`、`event` 等。本服务只保证：从表格抽出的数字能回到 `table_cell`，从文字得到的结论能回到 `text_block`。

### D. evidence / claim / serving layer（属 L2/L3，本服务不产出）

`key_text` 当判断、`claim_candidate`、`evidence_link` 的采信侧、跨证据 `relationship`、冲突检测与对账、`l3_need` / `l3_context_pack` 都在这层。L1 不建这些库，只为它们留下可精确寻址的锚点。L3 不该直接读全部年报正文——但“给 L3 一个 compact pack”是 L2 的产出，不是本服务的产出。

## L1 → L2 交接契约（“好抓 / 好发现重点”具体长什么样）

这是本服务真正要保证的对外契约，全部不越界：

- **寻址**：每份 filing 拆成可独立引用的单元（section / item / block / table / cell），每个单元有稳定 id + 精确定位（page / bbox / 段落序号）。→ 保证 L2 抽出的任何 claim 都能锚回 G0。
- **好抓**：能按 公司 / 报告期 / 公告类型 / 章节 / 表名 直接取到单元，L2 不用自己再切 PDF。
- **好发现重点**：结构标签 + 主题标签 + 检索索引（全文 / 关键词 /（可选）embedding），只作候选发现，不作事实。
- **处理状态**：哪些解析成功 / 失败、parser 版本——让 L2 知道这次切分能不能信。

明线（L1 绝不碰，全留给 L2）：规范化口径 / 单位 / 会计基础、生成 claim、冲突检测与对账、判真伪、判“对预测是否重要”、采信。

## Wind / Tushare / 外部数据怎么对接

Wind、Tushare、iFinD、Choice 等外部数据**不属于本服务范围**。按 v0.5 §2.3，L1 对这类 Tier 1 数据只登记 `source_ref`，不在这里规范化成事实、也不做对账。

本服务对它们只做一件事：

- 建 `source_ref`：记录 provider、dataset、query params、as-of time、返回字段摘要、口径说明、来源哈希/受权限约束的本地路径。

把外部指标规范化成 `metric_observation`、和披露数据并列对账、做 `same_period_as` / `conflict_check`，**都是 L2 的事**：

```text
（L2 才做）Tushare income.n_income_attr_p
→ metric_observation(metric = 归母净利润, source_type = provider)
→ same_period_as 财报披露的归母净利润
→ conflict_check: 数值、单位、口径是否一致
```

L1 只保证：当 L2 要把外部值和披露值并列时，能从 `source_ref` 和披露侧的 `table_cell` 精确锚回各自来源。

## 表格怎么保留

表格是 L1 的核心资产之一，不能被简单压成文本。L1 负责前两层，第三层是 L2：

1. `table`（L1）：整表，含 caption、页码、bbox、HTML/JSON、parser、质量字段——复原原貌；
2. `table_cell`（L1）：行列、raw_value、is_header、定位——保留结构、可定位数字（**不做口径/单位规范化**）；
3. `metric_observation`（L2，本服务不产出）：把 L3 需要的关键数字规范化成指标事实——服务预测和对账。

第一版 L1 优先切好这些表（不抽事实，只切好、标好、可寻址）：

- 三大报表；
- 主要会计数据和财务指标；
- 分产品 / 分地区 / 分行业收入毛利表；
- 现金流、资本开支、在建工程、产能相关表；
- 投资者关系记录中的问答表或机构列表。

## 关键文字怎么保留

注意区分两件事：

- **L1 做的**：把关键文字所在的 `text_block` 切好、可寻址，并用 `structural_tag` / `topic_tag` 机械标出主题（这段在谈业绩变动原因 / 订单 / 价格 / 管理层展望 / 风险 / 会计口径变化）。这是“发现重点”，不是“下结论”。
- **L2 做的（本服务不产出）**：把它升级成带 `normalized_summary`、`confidence`、`why_important` 的判断对象 `key_text`，再进 `claim_candidate`，由 L3 决定是否采信、是否冲突、是否影响预测。

机械主题标签可以先很实用：

- 业绩变动原因；
- 订单 / 产能 / 价格 / 成本；
- 产品结构 / 客户结构 / 地区结构；
- 管理层展望；
- 风险因素；
- 会计政策或口径变化；
- 投资者关系问答里的可量化线索。

L1 标“这段属于哪个主题”，L2 判“这段说了什么、可信不可信、对预测重不重要”。

## 关系图怎么做

用户直觉里的 Obsidian 图是对的：整套系统最终是一张证据关系网。但要分清谁建这张网：

- **事实/证据关系网（company-metric-claim-forecast 之间的 typed edge）属于 L2/L3**，不是本服务产出。
- **L1 负责的是让这张网的每个锚点可被精确引用**：filing、item、block、table、cell 都有稳定 id 和定位，关系网才挂得上去。

第一版即使要表达 L1 内部的结构关系（如 filing `contains` table / text_block / filing_item），也建议在 PostgreSQL 里用 typed tables + `relationship` 表达，不先上专门图数据库：

- 当前最重要的是事实约束、去重、版本、处理状态和来源追溯，关系数据库更稳；
- 图关系刚开始规模不会大到必须 Neo4j；
- 以后要做 Obsidian/Neo4j/前端 graph view，可从主库导出。

L1 内部可表达的结构关系（不含判断）：

```text
relationship
  subject_type / subject_id
  predicate
  object_type / object_id
  created_by
```

- company `filed` filing；
- filing `contains` table / text_block / filing_item；
- text_block `has_topic` topic_tag。

跨证据的判断型关系——`table_cell reports metric`、`key_text supports claim`、`claim affects forecast_variable`、`claim contradicts claim`——**都属于 L2/L3**，本服务只提供它们指向的锚点，不建这些边。

## 为什么不是 RAG

RAG 适合回答“这堆文档里可能有什么”。但本服务的核心问题是“怎么把披露文件切成可精确寻址、可发现重点的锚”，下游 L2 的核心问题才是“哪些事实可以进入预测、且能追到原文”。两个问题都不靠 RAG core。

第一版不做 RAG core 的原因：

- RAG chunk 命中不等于事实成立，更不等于可寻址；
- embedding 不能表达财报指标口径、单位、报告期、版本和冲突；
- 表格数字若只进文本 chunk，会丢失行列、单位、表头、脚注；
- L2 需要的是精确锚和候选发现，不是每次重读全文；
- 预测系统要可复盘，必须知道事实从哪里来、何时抽取、哪个 parser 版本。

L1 可保留的检索能力（都只作 candidate discovery）：

- 元数据过滤：公司、日期、公告类型、报告期、来源；
- 全文 / 关键词检索：找候选段落；
- embedding：找语义相近的候选文本；
- rerank：辅助挑选最相关片段。

但锚库的中心仍是结构化单元、表格、定位和标签，不是向量命中。

## 第一版实施路线（全部停在 L1）

建议按这个顺序推进：

1. **稳住 raw anchor**：CNINFO 公告索引、PDF 下载、哈希、路径、`source_record`、`processing_run`、外部来源 `source_ref`。
2. **落 addressable anchor**：把样本 PDF 解析成 `text_block`、`filing_item`、`table`、`table_cell`，每个单元有稳定 id + 定位。
3. **加发现层**：给单元打 `structural_tag` / `topic_tag`，建全文/关键词索引（embedding 可选）。
4. **固化 L1→L2 交接契约**：保证能按 公司 / 报告期 / 公告类型 / 章节 / 表名取到锚，并暴露 processing status 和 parser 版本。
5. **暴露查询 API**：让 L2 直接按上面维度抓锚，而不用打开 PDF。

第一版不要做（属 L2/L3 或后续）：

- 全市场全量；
- `metric_observation` / `key_text`(判断) / `claim_candidate` 等事实与判断对象；
- 冲突检测、对账、采信；
- `l3_context_pack`；
- 完整 RAG 问答、完整 Neo4j 图数据库；
- 所有 Wind/Tushare 表的全量复制（只登记 `source_ref`）；
- 自动 claim 最终采信、预测模型本身。

## 建议的最小验收

用现有 sample filings 可以先验收 L1 的两条链路——都**停在“交给 L2”**，不产出事实：

```text
美的集团投资者关系活动记录表
→ raw_file / filing 入库（A 段）
→ text_block 拆出问答，每块有稳定 id + 页码定位（B 段）
→ structural_tag = 投关问答；topic_tag = 订单/价格/业务展望（发现层）
→ 能按公司 / 公告类型 / 主题取到这些问答块，并暴露 parser 版本
→ 交给 L2：L2 再决定哪句是 claim、是否采信
```

```text
年报 PDF
→ raw_file / filing 入库（A 段）
→ table / table_cell 抽出主要财务表，保留行列/页码/原始值（B 段）
→ structural_tag = 三大报表 / 分产品收入表（发现层）
→ 能按公司 / 报告期 / 表名取到表与单元格，每个单元格可精确锚回页码
→ 交给 L2：L2 再规范化成 metric、和 Wind/Tushare（source_ref）对账
```

只要这两条链路跑通，`disclosure_anchor` 的方向就清楚了：它不是文件下载器，不是 RAG，也不是 L2/L3 的事实库，而是一个把披露 raw data 切成**可精确寻址、可发现重点的 L1 披露锚**、并把锚干净交给 L2 的服务。
