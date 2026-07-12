# Temporal NL → Lifted LTLf 翻译交付（temporal-nl-v1-20260711-final）

Run 目录：`artifacts/temporal_predictions/temporal-nl-v1-20260712-145052/`
执行规程：`docs/input_design.md` §Colleague-Only Procedure（Phase 0–3）
Runner：`scripts/run_temporal_translation_calls.py`（分支 `feat/temporal-nl-translation-run`，commit 8e6e230）

## 运行配置（475 条全程一致）

| 项 | 值 |
|---|---|
| model_id | `gpt-5.5`（OpenAI-compatible JSON mode，中转 packyapi） |
| model_parameters | `{"temperature": 0, "max_tokens": 60000, "timeout_seconds": 1000, "response_format": "json_object", "stream": true}` |
| prompt_config | `full` |
| prompt_source_commit | `8804f7347f40c908d6a58c2141f91a77efbfdba8`（与 handoff_manifest sealed 值一致；该 commit 与 HEAD 的 prompts.py/errors.py 逐字节相同） |
| semantic retry budget | 3（实际零重试） |
| 传输层 | SDK max_retries=3，与语义重试独立（实际零触发） |

Preflight 额外证据：475/475 行的 `prompt_context_sha256` 与本机渲染的 system prompt 哈希完全一致。

## 冻结

- `translation_predictions.jsonl`：475 行，每 translation_id 恰一条，按 worklist 顺序
- SHA-256：`512c766b60e9c3d953d49b930a4845bfda6bceb9706675a2670084d45db47f41`
- 冻结时间：2026-07-12T14:59:37+0800，文件 chmod 444，无任何手工修改
- 冻结之后才解压私有 validation 包（hidden gold 在冻结前从未接触）

## 结果（数字直接来自 goal_validation/summary.json）

| 指标 | 值 |
|---|---|
| primary calls | 475（5 smoke + 470 续跑，smoke 未重调） |
| accepted | 475/475，全部 attempt_count=1（零语义重试、零 terminal failure） |
| macro（unique translation inputs）DFA 语义等价 | **475/475**（status 全为 `semantically_equivalent`） |
| micro（problem rows）hidden witness 接受 | **1228/1228**（status 全为 `witness_accepted`） |
| execution traces | 未提供 → not_attempted（0 attempted） |
| validated append datasets | 16 domain，合计 1228 cases，与 test-split 规模逐 domain 一致 |

## 交付物

```
translation_predictions.jsonl            # 冻结，SHA-256 见上
translation_predictions.sha256
run_config.json                          # 配置 + 冻结记录
records/                                 # 475 个 per-id canonical 记录（拼装源）
attempt_log/                             # per-id 尝试日志（全部单次成功）
goal_validation/summary.json
goal_validation/translation_validation_results.jsonl
goal_validation/problem_validation_results.jsonl
goal_validation/validated_append_datasets/<domain>.json   # 16 个
goal_validation_infra_error_mona_env/    # 首次验证误配（子进程缺 MONA_BIN）的原样留存；
                                         # 属 validation_infrastructure_error，与模型无关，
                                         # 修复环境变量后重跑得到上表结果
```

## 合规声明

- 三个 prompt 均出自 `src/temporal_specification/prompts.py` 的 builder；重试只用 `build_retry_feedback` + `build_retry_user_message`（本次未触发）。
- 模型消息从未包含 profile、semantic_signature、translation_id、member_sample_ids、witness、assignment、原始 PDDL goal 或任何 hidden 审计信息（runner 内置 leak guard 断言）。
- 隐藏验证结果未回喂模型；预测文件冻结后未做任何编辑。
