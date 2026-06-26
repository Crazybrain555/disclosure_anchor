---
id: disclosure_anchor_milestone_01_code-skeleton-and-config
project: disclosure_anchor
title: 代码骨架与配置
status: ready-for-implementation
created_at: 2026-06-26
---

# Milestone 01: 代码骨架与配置

## 1. 目标

建立可维护的模块化单体代码骨架，让后续实现都落在正确层级；完成配置、路径注入、doctor 基础检查和最小 app 启动。

## 2. 范围

范围内：

- 创建 repo 目录结构。
- 创建 `pyproject.toml`、`Makefile`、`.env.example`。
- 实现 `settings.py`。
- 实现 `FileStorePathBuilder`。
- 实现 `doctor` 基础检查。
- 实现 domain ids、value objects、基础错误类型。
- 建立空 FastAPI app 和 CLI 入口。


## 3. 实施细则

1. 按 `001` 创建目录结构。
2. `settings.py` 使用 Pydantic Settings，支持：

```text
DISCLOSURE_DATA_ROOT
DISCLOSURE_SHARED_ROOT
DISCLOSURE_RUNTIME_ROOT
DATABASE_URL
MINERU_MODEL_CACHE
HF_HOME
MODELSCOPE_CACHE
```

3. `FileStorePathBuilder` 提供：

```text
raw_document_relpath(...)
parser_artifacts_root_relpath(...)
normalized_ir_relpath(...)
document_units_snapshot_relpath(...)
runtime_tmp_path(...)
```

4. `doctor` 检查：

```text
外置盘是否挂载
sentinel 是否存在
DATA_ROOT 是否可写
runtime 目录是否可写
模型缓存是否指向外置盘
```

5. FastAPI app 只实现 `/v1/health`。
6. CLI 实现 `python -m disclosure_anchor.cli.doctor`。
7. Makefile 实现：

```bash
make doctor
make test-unit
make api
```


## 4. 检查点

- `make doctor` 可运行。
- 外置盘未挂载时 doctor 失败。
- `PathBuilder` 只返回相对路径或受控 runtime path。
- repo 中没有硬编码 `/Volumes/AgentSSD` 的业务逻辑；只允许 `.env.example`、docs 出现。
- `/v1/health` 可返回 ok。
- unit tests 覆盖 settings、PathBuilder、ids。


## 5. Definition of Done

- 代码骨架完整。
- `make doctor` 和 `make test-unit` 通过。
- 空 app 可启动。
- 后续 DB / storage / parser adapter 有明确落位。


## 6. 明确不做

- 不建数据库表。
- 不实现 CNINFO。
- 不调用 MinerU。
- 不做业务查询 API。


## 7. 交付给下一阶段

- repo 骨架。
- settings / path builder / doctor。
- 空 FastAPI app。
- Makefile 基础命令。


## 8. 常见失败与处理

- 配置读取混乱：优先修 settings，不让 use case 读取环境变量。
- 路径手写扩散：立即收敛到 `FileStorePathBuilder`。
- doctor 误创建内置盘目录：视为严重错误，修正 fail closed。
