---
id: disclosure_anchor_milestone_08_worker-loop-and-ops
project: disclosure_anchor
title: worker loop 与本地运行
status: ready-for-implementation
created_at: 2026-06-26
---

# Milestone 08: worker loop 与本地运行

## 1. 目标

把 sync/download/parse/publish 串成可重复运行的本地 worker，支持 worker-once、worker-loop、runtime locks、失败重试和运行报告。

## 2. 范围

范围内：

- worker-once。
- worker-loop。
- runtime locks。
- pending 状态扫描。
- retry policy。
- reports。
- launchd 示例但不强制启用。


## 3. 实施细则

1. worker 状态来源：

```text
document.status
processing_run.status
outbox_event
runtime locks
```

2. 扫描队列：

```text
pending_download
pending_parse
parse_failed_retryable
ready_to_publish
```

3. 命令：

```bash
make worker-once
make worker-loop
```

4. runtime locks 防止同一 document 并发处理。
5. retry policy：

```text
retryable
non_retryable
needs_review
```

6. reports 输出：

```text
runtime/reports/worker/<date>.md
runtime/reports/parse_quality/<date>.md
```

7. 可选提供 launchd plist 示例，默认不启用。


## 4. 检查点

- `make worker-once` 能从 pending document 跑到 active run。
- worker 崩溃不会破坏 raw archive。
- 同一 document 不会并发 parse。
- 失败任务可定位。
- worker report 显示：发现、下载、解析、发布、失败数量。
- doctor 能发现 active run 冲突。


## 5. Definition of Done

- 本地运行闭环成立。
- 可定时执行 worker-once。
- 失败可恢复。


## 6. 明确不做

- 不引入 Celery。
- 不引入 Redis。
- 不引入 Airflow/Prefect/Dagster。
- 不建设全局 L6 调度脊柱。


## 7. 交付给下一阶段

- worker-once/loop。
- locks。
- retry。
- reports。
- launchd 示例。


## 8. 常见失败与处理

- worker 重复处理：检查 locks 和状态事务。
- publish 中断：旧 active run 保持。
- 长时间卡住：runtime lock 必须有 stale 检查和人工释放方式。
