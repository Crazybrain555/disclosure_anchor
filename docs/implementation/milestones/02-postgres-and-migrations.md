---
id: disclosure_anchor_milestone_02_postgres-and-migrations
project: disclosure_anchor
title: PostgreSQL 与 migrations
status: implemented
created_at: 2026-06-26
implemented_at: 2026-06-29
---

# Milestone 02: PostgreSQL 与 migrations

> 实施状态（2026-06-29）：已完成并在本地 PG18 AgentSSD 集群验证。`make db-create` / `make migrate` 幂等；
> `disclosure_core` / `disclosure_public` / `disclosure_ops` 三个 schema、九张核心表、五个 public view、
> 四个角色及最小权限、单 active run 偏唯一索引均已建立；repository / UnitOfWork 与 15 个集成测试通过
> （无 DB 环境时干净跳过）。A08-A10 标记为 pass。独立 review gate 待运行。

## 1. 目标

建立 `disclosure_anchor` database、schema、roles、核心表、public views、outbox seq 和 repository adapter。

## 2. 范围

范围内：

- native PostgreSQL cluster 脚本管理。
- database / schema / role 初始化。
- Alembic migration。
- 核心表。
- public views。
- repository integration tests。


## 3. 实施细则

1. Makefile 增加：

```bash
make pg-init
make pg-start
make pg-stop
make pg-status
make db-create
make migrate
```

2. 创建 database：`disclosure_anchor`。
3. 创建 schema：

```text
disclosure_core
disclosure_public
disclosure_ops
```

4. 创建 roles：

```text
disclosure_owner
disclosure_app
disclosure_reader
future_l2_reader
```

5. Alembic 创建核心表：

```text
company
security
tracked_company
source_access
source_checkpoint
document
processing_run
document_unit
outbox_event
```

6. 创建 public views：

```text
documents_v1
document_units_v1
processing_runs_v1
source_refs_v1
change_events_v1
```

7. 实现 repositories 与 UnitOfWork。
8. integration tests 使用测试 database 或临时 schema。


## 4. 检查点

- `make migrate` 幂等。
- `disclosure_app` 可写 core/ops。
- `disclosure_reader` 只能读 public views。
- public view 不暴露绝对路径、密钥、内部错误堆栈、MinerU raw JSON。
- repository tests 可创建 company/security/document/run/unit/outbox。
- UnitOfWork rollback 测试通过。


## 5. Definition of Done

- DB schema 可迁移。
- 权限边界成立。
- public views 可查询。
- repository integration tests 通过。


## 6. 明确不做

- 不写 CNINFO。
- 不做 API query。
- 不写 raw file store。
- 不写 claim/evidence 表。


## 7. 交付给下一阶段

- database/schema/roles。
- Alembic migration。
- repository adapter。
- public views。


## 8. 常见失败与处理

- 权限过宽：先修 role grant，不继续。
- migration 不可重复：修 Alembic，不手工改库。
- public view 泄露 relpath 以外绝对路径：立即移除。
