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

## 6. 测试落地（目录与命令）

第 3 节是目标分层，下面是当前仓库的实际落地与入口命令。

```text
tests/unit/          已实现  settings / ids / value_objects / PathBuilder / doctor / health / app startup
tests/contract/      已实现  phase00 golden fixture 结构（document_unit 字段、content_hash、order_index、IR↔unit 一致性）
tests/sample_corpus/ 已实现  tmp/sample_filings manifest 完整性 + 真实 ID/hash 走 PathBuilder
tests/integration/   已实现  Phase 02 PG schema / views / permissions / repositories / UnitOfWork rollback
```

入口命令（Makefile）：

```bash
make test              # 跑全部分层（当前 54 个；无 DB 环境时 16 个 integration skip）
make test-unit         # 仅 tests/unit
make test-contract     # 仅 tests/contract
make test-data         # 仅 tests/sample_corpus
make test-integration  # 仅 tests/integration（需要本地 PG + migration 到 head）
```

约定：

- `make test` 是**唯一权威入口**；VSCode Testing 已配置发现根为 `./tests`（`.vscode/settings.json`），三层都会出现在 Test Explorer。
- 依赖外部资源的测试（`tests/sample_corpus` 需要 `tmp/sample_filings`，`tests/integration` 需要本地 PG/runtime）在资源缺失时必须 **skip**，保证无外部依赖的环境仍全绿。
- `tmp/sample_filings` 与大型 parser artifact 是 git-ignored 的本地 fixture，不入库；只有 `tests/fixtures/phase00/` 的小型 golden 输出入库。

## 7. Phase 02 独立 testing 验证记录

2026-06-29 独立复测覆盖：

```bash
make migrate                         # 连续运行，幂等
.venv/bin/python -m alembic current  # 0002_harden_ops_permissions (head)
make test-integration                # 16 tests, OK
make test                            # DB env: 54 tests, OK
env -u DISCLOSURE_MIGRATION_DATABASE_URL -u DATABASE_URL -u DISCLOSURE_ADMIN_DATABASE_URL make test
                                     # no DB env: 54 tests, OK (skipped=16)
```

SQL 点检结果：

```text
tables=10
views=5
alembic=0002_harden_ops_permissions
leak_cols=0
active_idx=1
app_alembic_priv_count=0
missing_fk_indexes=none
```

Fresh DB 验证：创建随机临时库、按 bootstrap 前置 schema/grant 建库、从零 `alembic upgrade head` 到
`0002_harden_ops_permissions`，确认 5 个 public views、`disclosure_app` 无 `alembic_version` 权限、
FK helper indexes 无缺口，然后删除临时库。

备注：`make doctor` 当前仍主要覆盖 AgentSSD/runtime/model-cache 基线；Phase 02 的 DB 证明来自
Alembic、SQL 点检和 integration tests，PG doctor 输出项后续单独补齐。
