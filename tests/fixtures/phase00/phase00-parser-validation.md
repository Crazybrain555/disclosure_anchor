# Phase 00 Parser Validation

## Environment

- macOS: 26.5.1 (25F80), arm64
- Python for MinerU: 3.13.13 at `/Volumes/AgentSSD/agent_system/services/disclosure_anchor/runtime/venvs/mineru-phase00`
- MinerU: 3.4.0, backend `pipeline`, source `modelscope`
- Model cache: `/Volumes/AgentSSD/agent_system/shared/model_cache/modelscope`
- PostgreSQL: pass via Homebrew PostgreSQL 18.4 at `/opt/homebrew/opt/postgresql@18`; PGDATA is `/Volumes/AgentSSD/agent_system/postgres/pg18-main`; the temporary conda PostgreSQL env/cache and superseded PG17 paths were removed after validation. Socket-only posture (`port=55432`, `listen_addresses=''`, AgentSSD `unix_socket_directories`) is persisted in `postgresql.conf`, so a bare `pg_ctl -D <PGDATA> start` stays socket-only; `brew services` is not used.

## Parser Runs

| sample | parsed pages | elements | document units | conclusion |
|---|---:|---:|---|---|
| short_announcement | 1-4 (full) | 31 | {'text': 20} | pass |
| ir_activity | 1-24 (full) | 131 | {'table': 2, 'text': 46, 'qa': 36} | needs_rule_adjustment |
| annual_report | 1-209 (full) | 2697 | {'text': 1144, 'table': 473} | pass |

## Known Risks

- IR first Q&A is embedded in the initial activity table; formal mapper needs table-body Q&A extraction.
- Annual report full parse is table-heavy: 473 table units. Phase 04/05 must preserve raw table strings and normalize numeric values separately.
- Annual report heading paths in the Phase 00 fixture are heuristic and sufficient for feasibility/golden checks, not the final sectioning rule.
- MinerU 3.4.0 wrote user-level `/Users/zhang/mineru.json`; it contains placeholders and external model paths, not secrets.
- Local proxy env caused MinerU/httpx to fail without `socksio`; local parse succeeds when `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` are cleared and `NO_PROXY=*` is set.

## A01-A05 State

- A01: pass, AgentSSD mounted and sentinel exists.
- A02: pass, native PostgreSQL 18.4 can initialize, start, accept socket connections, create/drop a probe database, and stop with PGDATA on AgentSSD. Socket-only/55432 is persisted in `postgresql.conf` and re-verified by a bare `pg_ctl start` (both 127.0.0.1:5432 and :55432 report no response; the socket lives under AgentSSD).
- A03: pass, model and uv caches were directed to AgentSSD.
- A04: pass, normalized IR fixtures exist for all three sample roles, including full 209-page annual report.
- A05: pass, document unit fixtures exist for all three sample roles, including full 209-page annual report.
