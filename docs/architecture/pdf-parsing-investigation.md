# PDF 解析方案调研（开源框架 + 输出格式）

本文是对 `open-source-references.md` 中第 5/8/9/10 条（PDF→Markdown/JSON、表格抽取）的专项深入调研，回答两个问题：

1. 有没有解析做得好的开源框架，财报解析是不是"规则一样、没那么难"？
2. PDF 解析成 **Markdown** 是不是最合适的目标格式？

> 服务目的见 `service-purpose.md`：我们要的不是"把 PDF 下载到文件夹"，而是把正文、章节、表格、页码、处理状态变成**可查询的本地数据**。解析格式必须服务于 `filing_text` / `filing_table` 这套结构，而不是只产出一坨给人看的文本。
>
> 调研时间：2026-06。本文中的 license / 平台支持等关键事实以各项目**官方仓库**为准（部分第三方对比博客信息已过期，见下方"事实更正"）。

---

## 一、结论（TL;DR）

1. **默认解析后端用 MinerU**。中文版面/表格是它的强项（CJK SOTA），已支持 macOS 14+ / Apple Silicon，license 已从 AGPL 改为基于 Apache 2.0 的自有协议，商用更友好。它同时输出 Markdown + 结构化 JSON（含页码、bbox、块类型、表格 HTML），天然贴合我们的 `filing_text` / `filing_table` 设计。
2. **Docling 作为第二后端 / 交叉校验**。MIT 协议、Linux Foundation 项目、`DoclingDocument` 结构化模型，适合 RAG 与对照。
3. **Camelot / pdfplumber 作为 text-based PDF 的表格 fallback 与"数字对账"工具**，输出 DataFrame，便于和 MinerU 的表格做一致性校验。
4. **格式不是"二选一"，而是双轨**：
   - 正文/章节/item → **Markdown**（可读、好切块、利于后续 RAG）；
   - 表格 → **保留结构化形式（HTML/JSON/cells），不要拍平成 Markdown 管道符**。财报表格拍平成 `| a | b |` 会丢精度。
   - 两者都来自同一个**结构化中间产物**（MinerU 的 `content_list.json` / DoclingDocument），这个中间产物才是入库的真正来源。
5. **你的假设"财报规则一样、没那么难"——对一半**：版面确实高度规则（封面/目录/重要提示/管理层讨论/三大报表/附注），**版面级切分确实不难**；但**表格里的数字保真是真正的难点**（合并单元格、跨页表、负号/括号表示负数、千分位、脚注关系）。已有专门的金融 OCR 基准（FinCriticalED）和金融专用模型（Agentar-Fin-OCR）就是冲着这个问题来的。所以第一版必须带**表格数字校验**，不能盲信单一解析器。

---

## 二、直接回答你的两个假设

### 假设 A：「财报解析应该都是一样的规则，没那么难」

**部分成立。**

- ✅ **成立的部分**：A 股定期报告版面高度标准化。年报/季报基本都是「封面 → 重要提示 → 目录 → 公司简介 → 会计数据和财务指标 → 管理层讨论与分析 → 公司治理 → 财务报告（资产负债表/利润表/现金流量表/所有者权益变动表）→ 附注」。这种规则性让**章节切分**和**报告期识别**确实相对简单——可以靠标题正则 + 版面顺序搞定大部分。
- ❌ **不成立的部分**：**表格才是难点，而不是版面**。财报里的财务报表：
  - 大量**合并单元格**、多级表头（"本期/上期"、"合并/母公司"）；
  - **跨页表格**需要正确合并（MinerU 支持，朴素方案会断）；
  - 数字格式坑：括号表负数 `(1,234)`、负号、千分位逗号、单位（元/万元/亿元）、`-` 表示空值；
  - 数字一旦 OCR 错位（小数点、负号、漏位），下游所有计算都错——这正是 **FinCriticalED**（2026 金融 fact-level OCR 基准）证明的：通用解析器在金融表格上"文本看着对、数字未必对"。

**结论**：版面解析借现成框架就够；**表格数字必须有校验/对账机制**，这是第一版就要设计进去的，不是以后再说。

### 假设 B：「PDF 解析成 Markdown 是不是最合适？」

**Markdown 是正文的最佳格式，但不是表格的最佳格式，也不能是唯一格式。**

业界 2026 的共识（多篇 RAG 解析评测一致）：
- **Markdown 适合正文**：保留标题层级、列表、阅读顺序，切块（chunking）干净，利于嵌入/RAG。
- **JSON/结构化适合精确字段和表格**：需要"第几页、第几行、单元格原值"时，Markdown 表达力不够。
- **生产最佳实践 = 两者都留**（hybrid）。

对**我们这个项目**尤其如此，因为 `service-purpose.md` 明确要求"表格保留页码和表格位置""单元格行列位置和原始值"。这只能靠结构化产物，Markdown 管道符表格做不到。

**结论**：
- 把 **Markdown 当正文（filing_text）的展示/检索层**；
- 把解析器的**结构化中间产物（带 bbox/page/type/表格HTML）当入库的事实来源**；
- 表格在 `filing_table` 里**以 HTML 或 cell 级 JSON 保存**，Markdown 只作为附带的可读副本。

---

## 三、候选框架对比（2026-06 现状）

| 框架 | 类型 | License | macOS/Apple Silicon | 中文/CJK | 表格 | 速度 | 输出 | 适合角色 |
|---|---|---|---|---|---|---|---|---|
| **MinerU** (v3.3.1) | 版面模型 + 可选 VLM | MinerU 协议（基于 Apache 2.0） | ✅ 14+，MPS / `vlm-mlx` 加速 | ✅✅✅ SOTA | ✅✅✅ HTML、跨页合并 | Pipeline 快(CPU可跑)，VLM 需 GPU | **Markdown + JSON（content_list，带 bbox/page）** | **默认后端** |
| **Docling** | 版面模型 | MIT（Linux Foundation） | 部分（CPU 慢） | ✅ 好 | ✅✅ | 中等，CPU 偏慢 | DoclingDocument → md/json/html | **第二后端 / RAG / 交叉校验** |
| **Marker** | 版面模型 | 商用有营收门槛（采用前复核） | ✅ MPS | ✅ 好 | ✅✅ | GPU 很快 | Markdown/JSON | 候补，授权需确认 |
| **PaddleOCR-VL** | VLM | Apache 2.0 | 需确认 | ✅✅ 强 | ✅✅ | 需 GPU | Markdown/JSON | 中文 OCR 强，可作 VLM 候选 |
| **PyMuPDF4LLM** | 原生文本抽取 | **AGPL-3.0 / 商用付费**（注意） | ✅ CPU | 基础 | ✅ 一般 | **最快**，无 ML | Markdown | 纯数字版 PDF 快速兜底 |
| **Camelot** | 表格专用 | MIT | ✅ CPU | n/a | text-PDF 强 | 快 | DataFrame/CSV/JSON | **表格 fallback / 数字对账** |
| **pdfplumber** | 文本/表格 | MIT | ✅ CPU | n/a | text-PDF 中 | 快 | dict/表格 | 轻量表格 + 字符级定位 |

### 事实更正（重要）

第三方对比博客（如 themenonlab、Spheron）仍在写 "MinerU 是 AGPL、不支持 macOS"——**已过期**。以官方仓库为准：

- **MinerU v3.3.1（2026-06-11 发布）**：协议为 "MinerU Open Source License, based on Apache 2.0"；**支持 Windows/Linux/macOS 14+**；Apple Silicon 走 MPS，另有 `vlm-mlx-engine` 后端（相对 transformers 后端 100%–200% 提速）。这对你（darwin 本机）很关键。

---

## 四、为什么默认选 MinerU

针对"中文财报 + 本地数据库"这个具体场景，MinerU 的契合点：

1. **中文是第一公民**：OmniDocBench 上 CJK 版面/识别 SOTA，支持 109 种语言；A 股 PDF 大多是数字版（非扫描），命中它最强的场景。
2. **跨页表格合并**：财报三大报表经常跨页，MinerU 原生支持合并，省掉自己写拼接逻辑的坑。
3. **输出天然分层**，正好喂我们的 schema：
   - `*.md` → 正文 Markdown；
   - `content_list.json` → 每个块的 `type`（text/title/table/equation/image）、`page_idx`、`bbox`、阅读顺序；
   - 表格块以 **HTML** 给出（保结构），公式给 LaTeX。
   - 这套结构可以直接映射到 `filing_text(item_type, heading, page_start, order_index, text)` 和 `filing_table(html, page, bbox, ...)`。
4. **两档后端，按 PDF 质量分流**：
   - **Pipeline 后端**：CPU 可跑（16GB+ RAM），适合干净的数字版 PDF（A 股年报多数属于此类），成本低；
   - **VLM/Hybrid 后端**：复杂版面/扫描件，精度更高（OmniDocBench ~95），需要 GPU（8GB+）或在 Apple Silicon 上用 `vlm-mlx`。
5. **license 风险下降**：从 AGPL 改为 Apache-2.0 基础协议，作为本地服务后端更可用（仍建议采用前读一遍附加条款）。

**MinerU 的注意点**：
- VLM 后端要 GPU 才划算；纯 CPU 上优先用 pipeline 后端。
- 它仍是"概率模型"，**表格数字不能盲信**（见第五节校验）。
- 数据库要按 `open-source-references.md` 的设计，保留 `parser`、`parser_version`、`backend`、`processing_run`，允许同一 filing 多次重跑、多版本并存。

---

## 五、财报特有的硬骨头 + 校验策略

FinCriticalED / Agentar-Fin-OCR 这类金融专用工作给出的明确信号：**通用解析器在金融数字上需要额外校验，不能直接信。** 第一版就应内建：

1. **数字版优先**：A 股 PDF 多为文本层 PDF。先判定"有无文本层"，有就走 pipeline / pdfplumber 直取，OCR 只作为扫描件的退路——能取文本层就别 OCR，精度最高。
2. **表格双解析对账**：对财务报表页，用 **MinerU + Camelot/pdfplumber 各解析一次**，比对关键数字（总资产、营收、净利润等可加总校验的行）。不一致 → 标记 `needs_review`，不污染干净数据。
3. **结构化保真**：表格存 **HTML / cell 级 JSON**（行列 + 原始字符串），不要只存 Markdown 表格。负号、括号、千分位、单位都按**原始字符串**保留，规范化（转 float）放到下游、并保留原值。
4. **可重跑、可追溯**：每次解析写 `processing_run`，记录后端/版本/耗时/错误，永不覆盖旧结果——这样换 parser 或升级模型可以回溯对比。
5. **轻量勾稽校验**（可选增强）：利用财报恒等式做体检，例如「资产 = 负债 + 所有者权益」、利润表分项加总、合并报表本期/上期对齐。校验失败的表打 flag，人工抽查。

---

## 六、和数据库 schema 的映射

把解析产物落到 `service-purpose.md` 里列的对象：

```text
PDF
 └─ MinerU(pipeline 或 vlm)
     ├─ document.md          → filing_text(全文 markdown 副本)
     └─ content_list.json    → 事实来源
         ├─ type=title/text  → filing_text(item_type, heading, page_start, order_index, text)
         ├─ type=table       → filing_table(html, page, bbox, parser, accuracy)
         │                      └─(可选) filing_table_cell(row, col, raw_value)
         └─ type=equation     → 存 LaTeX
 └─ Camelot/pdfplumber(仅 text-PDF 表格)
     └─ 对账结果              → filing_table.cross_check / needs_review 标记
processing_run: parser, parser_version, backend, status, error, duration
```

要点：**Markdown 是派生展示层，`content_list.json` 是入库依据**。先存结构化，再从结构化生成 Markdown，而不是反过来从 Markdown 反推结构。

---

## 七、第一版建议路线

1. **闭环先跑通一份真实 PDF**：用仓库里已有的样本（如 `三川智慧_300066_2026年一季度报告.pdf`）跑 MinerU pipeline 后端，落地 `*.md` + `content_list.json`，肉眼核对章节切分与三大报表表格。
2. **分流策略**：有文本层 → pipeline/pdfplumber；扫描/复杂 → VLM 后端（macOS 上 `vlm-mlx`，有 GPU 用 GPU）。
3. **表格对账**：财务报表页加 Camelot/pdfplumber 二次解析与关键数字比对。
4. **入库**：按第六节映射写 `filing_text` / `filing_table` / `processing_run`，保留 parser/version/backend。
5. **Docling 作对照**：同一份 PDF 用 Docling 跑一遍，对比表格/切分质量，决定是否需要按文档类型路由到不同后端。

**第一版先不做**：自训模型、全市场全量、向量库、claim 抽取（与 `open-source-references.md` 的取舍一致）。

---

## 八、风险与开放问题

- **license 复核**：MinerU 自有协议附加条款、Marker 商用门槛、PyMuPDF(4LLM) 的 AGPL，采用前都要再读一遍。本文以 2026-06 官方信息为准，license 会变（MinerU 就刚从 AGPL 改过）。
- **算力**：VLM 后端要 GPU 才划算；纯 CPU/Mac 以 pipeline 后端为主，复杂件再考虑 `vlm-mlx` 或外置 GPU。
- **数字保真上限**：再好的解析器在金融数字上都有错误率，"对账 + flag + 可重跑"是必须的工程兜底，而不是锦上添花。
- **是否需要金融专用模型**：Agentar-Fin-OCR / PaddleOCR-VL 等值得跟踪；但第一版用 MinerU + 对账已足够，等闭环稳定后再评估是否引入。

---

## 参考来源

- MinerU 官方仓库（license / macOS / 后端 / 输出，v3.3.1）：https://github.com/opendatalab/MinerU
- MinerU Changelog（MLX 后端、协议变更）：https://opendatalab.github.io/MinerU/reference/changelog/
- Docling 论文（MIT、DoclingDocument）：https://arxiv.org/pdf/2501.17887
- OmniDocBench（CVPR 2025 文档解析基准，2026 更新 MinerU2.5 / PaddleOCR-VL）：https://github.com/opendatalab/OmniDocBench
- FinCriticalED（金融 fact-level OCR 基准，数字保真难点）：https://arxiv.org/pdf/2511.14998
- 开源 PDF→Markdown 工具对比（2026，Marker/Docling/MinerU/pdf-craft/PyMuPDF4LLM）：https://themenonlab.blog/blog/best-open-source-pdf-to-markdown-tools-2026
- 自托管文档智能（Docling/Marker/MinerU 生产部署对比）：https://www.spheron.network/blog/self-host-document-intelligence-docling-marker-mineru-rag-guide/
- RAG 解析格式 Markdown vs JSON vs flat text：https://ocrqueen.com/blog/document-extraction-rag-markdown-vs-json-vs-flat-text
- 2026 RAG PDF 解析器评测（Firecrawl）：https://www.firecrawl.dev/blog/best-pdf-parsers
