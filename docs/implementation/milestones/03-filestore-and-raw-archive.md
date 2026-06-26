---
id: disclosure_anchor_milestone_03_filestore-and-raw-archive
project: disclosure_anchor
title: 文件存储与 raw archive
status: ready-for-implementation
created_at: 2026-06-26
---

# Milestone 03: 文件存储与 raw archive

## 1. 目标

实现本地 PDF 登记和 raw archive，保证原始 PDF byte 保真、hash 可校验、路径由 FileStorePathBuilder 管理。

## 2. 范围

范围内：

- RawDocumentStore。
- atomic write。
- sha256。
- register local PDF use case。
- quarantine 机制。
- document raw metadata 写库。


## 3. 实施细则

1. 实现 `RawDocumentStore`：

```text
put_raw_document(provider, security_code, year, provider_document_id, input_file)
verify_raw_document(relpath, expected_hash)
```

2. atomic write：先写 tmp，再 fsync，再 rename。
3. hash 计算：以 PDF bytes 为准。
4. register local PDF use case 输入：

```text
file_path
company/security metadata
filing_type
title
disclosed_at
report_period
provider/local ref
```

5. 写入：

```text
source_access
document
raw file
outbox_event(document_downloaded 或 document_registered)
```

6. 重复导入策略：

```text
同 provider_document_id + raw_file_hash：不重复写 raw
同 provider_document_id + 不同 raw_file_hash：新 document 或新版本关系
hash mismatch / 文件打不开：进入 quarantine
```


## 4. 检查点

- 本地 PDF 可登记为 document。
- raw file 存到 `data/raw_documents/.../sha256_<hash>.pdf`。
- DB 存相对路径与 hash。
- 重复导入同文件不重复写。
- hash mismatch 进入 `runtime/quarantine`。
- raw 文件被手工改动后 doctor 能发现。


## 5. Definition of Done

- `register_local_pdf` 可用。
- raw archive 不覆盖旧文件。
- document 与 raw hash 一致。
- 相关 integration tests 通过。


## 6. 明确不做

- 不调用 MinerU。
- 不生成 document_unit。
- 不接 CNINFO。
- 不暴露 raw 下载 API。


## 7. 交付给下一阶段

- RawDocumentStore。
- register_local_pdf use case。
- hash 校验。
- raw archive fixture。


## 8. 常见失败与处理

- 文件写一半失败：不得生成 published document；保留 failed 输入。
- DB 写入成功但文件写入失败：UnitOfWork 必须 rollback 或标记 failed。
- relpath 不稳定：修 PathBuilder，不迁就测试。
