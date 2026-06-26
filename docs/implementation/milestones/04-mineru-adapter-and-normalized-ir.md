---
id: disclosure_anchor_milestone_04_mineru-adapter-and-normalized-ir
project: disclosure_anchor
title: MinerU adapter 与 NormalizedIR
status: ready-for-implementation
created_at: 2026-06-26
---

# Milestone 04: MinerU adapter 与 NormalizedIR

## 1. 目标

把已登记 document 的 raw PDF 解析为 parser_artifacts，并将 MinerU 输出映射成 parser-neutral `NormalizedIR v1`。

## 2. 范围

范围内：

- MinerU process wrapper。
- parser artifact layout。
- MinerU output reader。
- Mapper to NormalizedIR。
- normalized_ir artifact 写入。
- parse processing_run 状态。


## 3. 实施细则

1. 实现 parser port：

```text
DocumentParserPort.parse(input_pdf, output_dir, options) -> ParserResult
```

2. 实现 MinerU adapter：

```text
mineru_process.py
artifact_reader.py
mapper_to_ir.py
```

3. 输出目录：

```text
data/parser_artifacts/<provider>/<security>/<provider_doc_id>/run_<run_id>/
```

4. NormalizedIR 输出：

```text
data/derived/normalized_ir/<provider>/<security>/<provider_doc_id>/run_<run_id>/normalized_ir.v1.json
```

5. processing_run 写入 parser_name、parser_version、backend、input_raw_file_hash、artifact relpath、normalized_ir relpath、status。
6. adapter 不让 domain 读取 MinerU raw JSON。


## 4. 检查点

- 给定 document_id，可生成 processing_run。
- parser_artifacts 目录存在。
- normalized_ir.v1.json 存在。
- NormalizedIR schema contract test 通过。
- 解析失败时 processing_run.status = failed，旧 active run 不受影响。
- 模型缓存没有落到内置盘默认 cache。


## 5. Definition of Done

- MinerU adapter 可解析样本 PDF。
- NormalizedIR 可被后续 unit builder 读取。
- parser 失败可定位。


## 6. 明确不做

- 不生成最终 document_unit。
- 不发布 active run。
- 不做复杂 parser fallback。
- 不实现常驻 HTTP MinerU service。


## 7. 交付给下一阶段

- ParserResult。
- parser_artifacts。
- normalized_ir artifact。
- processing_run parse 状态。


## 8. 常见失败与处理

- MinerU 输出格式变化：只改 mapper，不改 domain。
- 单份 PDF 解析超时：记录 failed，不阻塞其他任务。
- IR 过大：记录大小，暂不优化存储。
