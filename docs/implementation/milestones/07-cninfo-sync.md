---
id: disclosure_anchor_milestone_07_cninfo-sync
project: disclosure_anchor
title: CNINFO 增量同步
status: ready-for-implementation
created_at: 2026-06-26
---

# Milestone 07: CNINFO 增量同步

## 1. 目标

实现 CNINFO source adapter，让精选股票池的公告索引、PDF 下载、source_access、checkpoint 和重试机制进入正式管道。

## 2. 范围

范围内：

- CNINFO client。
- provider mapper。
- rate limit / retry。
- tracked_companies。
- source_checkpoint。
- index sync。
- PDF download。
- source_access 查空记录。


## 3. 实施细则

1. 实现 `DisclosureSourcePort`：

```text
search_announcements(...)
download_pdf(...)
```

2. CNINFO adapter 负责 provider 参数转换和返回映射。
3. `sync_disclosure_index`：

```text
tracked_companies
+ filing_type rules
+ time window
→ candidates
→ source_access
→ document candidates
```

4. `download_document`：

```text
provider ref
→ PDF bytes
→ RawDocumentStore
→ document
```

5. source_checkpoint 保存最近成功游标。
6. rate_limit 和 retry 不使用外部队列。
7. 查空也写 source_access。


## 4. 检查点

- 指定 10 家公司可稳定同步公告索引。
- 指定公告类型可下载 PDF。
- 下载结果进入 raw archive。
- 查空有 source_access。
- 失败可重试。
- provider ID 不作为内部主键。
- 重复公告不重复写 raw。


## 5. Definition of Done

- CNINFO 同步可跑通小样本。
- 失败状态可定位。
- 可从 CNINFO document 进入 Phase 04/05 管道。


## 6. 明确不做

- 不抓全市场。
- 不做复杂 anti-bot 规避。
- 不做标准数据 provider。
- 不做 L2 claim。


## 7. 交付给下一阶段

- CNINFO source adapter。
- source_checkpoint。
- index sync。
- download pipeline。


## 8. 常见失败与处理

- CNINFO 参数变化：只改 adapter/mapper，不改 domain。
- 限流失败：降低并发，记录 retry，不绕过。
- PDF hash 变化：作为新文件版本处理，不覆盖旧文档。
