---
id: disclosure_anchor_fixture_and_test_policy
project: disclosure_anchor
title: 样本与测试策略
status: final-for-implementation
created_at: 2026-06-26
---

# 样本与测试策略

## 1. 样本类型

最小样本集：

```text
annual_report.pdf        年报，验证 heading + long text + table
ir_activity.pdf          投关记录，验证完整 Q&A
short_announcement.pdf   短公告，验证少量事项型 text/table
```

样本用于 fixture 和人工复核，不用于覆盖全市场质量。

## 2. Fixture 输出

每个样本至少保存：

```text
mineru_raw 或简化 parser output
normalized_ir.v1.json
document_units.v1.jsonl
manual_review.md
```

## 3. 测试分层

```text
unit
  ids
  hashing
  PathBuilder
  retention rules
  quality checks
  source_ref builder

integration
  PostgreSQL repositories
  UnitOfWork rollback
  RawDocumentStore
  MinerU adapter with fixture
  document_unit builder

contract
  API DTO
  public view columns
  source_ref schema
  change_event schema

e2e
  register local PDF
  parse
  build units
  publish active run
  query units
  get source_ref
```

## 4. Golden sample 规则

如果 parser 升级导致 fixture 变化，必须区分：

```text
raw_file_hash 是否变化
unit content_hash 是否变化
structure_hash 是否变化
quality_status 是否变化
```

只有 unit content_hash 变化，才视为 L2 需要重处理。

## 5. 人工复核报告格式

```text
sample: annual_report.pdf
parser_version:
backend:
result:
  text_units_ok: yes/no
  table_units_ok: yes/no
  qa_units_ok: n/a
issues:
  - ...
action:
  pass / needs_rule_adjustment / parser_unusable
```
