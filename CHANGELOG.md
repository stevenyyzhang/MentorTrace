# Changelog / 版本变更

## 1.1.0-dev — development, not a stable release / 开发版

The complete development tree is independently runnable. Download the full repository and install its documented dependencies; it does not require an installed v1.0.0 copy. The initial diagnosis rules and both frozen corpora are unchanged.

完整开发版可独立运行。下载完整仓库并准备文档所列依赖即可，不需要先安装 v1.0.0。四路初始诊断规则和两套冻结语料保持不变。

### Review and delivery / 审阅与交付

- Inspect whether frozen initial tasks were actually answered; distinguish unattempted coverage from completed-but-unknown judgments.
- Preserve independently answerable requirements, exact conditions, valid alternatives and affected occurrences through consolidation. Narrowing or withdrawal identifies excluded original clauses and manuscript evidence.
- Add source-only Phase A adjudication before Phase B comparison with the actual report. Freeze records and retain truthful reviewer provenance.
- Upgrade final-text preservation to version 2: review factual assertions, author prerequisites, bilingual meaning and wording against exact passages and hashes.
- Preserve the difference between proposed author work and work actually established by the manuscript. Coordinate claim corrections across affected locations and reconcile overlapping replacement drafts.
- Write natural English and Chinese explanations with the same checked meaning. Keep routine language explanations concise, place missing facts in Suggested revision, and reduce duplicated drafts and checklists.
- Require both the report-bound Phase B comparison and version 2 final-text ledger before author delivery and HTML/PDF export.

- 核查冻结后的初始任务是否实际回答，区分未执行范围与已经检查但无法判断的事项。
- 合并时保留独立要求、准确条件、有效替代方案和受影响位置；缩小或撤回意见须指出排除的原始要求并提供稿件证据。
- 新增先裁定原始要求的 Phase A，再与实际报告比较的 Phase B；冻结审核记录并保留真实来源。
- 最终文本保留检查升级为 v2，对照具体文本和哈希核查事实、作者确认前提、中英含义与措辞。
- 区分建议作者开展的工作与稿件已经证明完成的工作；同步相关位置的主张修改，协调重叠修改稿。
- 中英文按各自语言习惯表达同一核实后的含义；简化常规语言解释，将缺失事实放入建议修改，减少重复草稿和清单。
- 作者交付及 HTML/PDF 导出须同时通过报告绑定的 Phase B 和 v2 最终文本审核。

### Execution and usage / 执行与额度

- Reuse matching completed responses with verified hashes and original settings/provenance. Inspect uncertain attempts before retrying.
- Prepare conservative incremental delivery-review plans; carryover needs a recorded affected-scope and dependency assessment.
- Supply complete relevant evidence, compact JSON, combine related final-text checks and batch to verified capacity.
- Support bounded prefetch concurrency for independent Advisor batches; dependent stages remain sequential.
- Explicitly request Standard by default. Fast/priority requires explicit human authorization naming the tier and accepting additional usage. Any reasoning-effort change requires explicit authorization naming the new effort.
- Validate settings authorization at CLI/API entry points and pin settings in a frozen run. Perform mechanical checks locally and finish after required delivery checks.

- 校验哈希后复用输入一致的完成结果，保留原始设置与来源；结果不确定时先核查再重试。
- 准备保守的增量审核计划；继承旧审核须有实际记录的影响范围及依赖判断。
- 提供必要完整证据、紧凑 JSON，合并相关最终文本检查，并按核实后的容量分批。
- 支持独立 Advisor 批次有界预取并发，依赖阶段顺序执行。
- 默认显式请求 Standard；Fast/priority 须明确授权档位并接受额外消耗。推理强度的任何变化须明确授权新强度。
- CLI/API 入口校验设置授权，冻结运行固定参数；机械检查在本地完成，必要交付验收通过后结束。

### Migration / 迁移

- CLI model submission now requires `--settings-authorization AUTH.json`; isolated calls may ignore user-level configuration. The record must document the user's actual explicit choice. Optional Responses transport uses the same authorization structure and remains disabled by default.
- New HTML/PDF exports require `--preservation-audit DELIVERY.json` containing a completed v2 final-text review and `--requirements-audit B.json` bound to the same report and final-review source.
- Legacy v1 ledgers remain readable, but do not satisfy new delivery gates. Preserve original runs and prepare new audit/version directories rather than rewriting frozen artifacts.
- Keep earlier corpora and diagnostic outputs with their real provenance. Do not relabel replayed output as a fresh review under different settings.

- CLI 模型提交新增必需参数 `--settings-authorization AUTH.json`；隔离调用可能忽略用户全局配置，授权记录必须对应用户实际明确选择。可选 Responses 传输采用同样的授权结构，默认仍禁用。
- 新 HTML/PDF 导出需要完成的 v2 `--preservation-audit DELIVERY.json` 和绑定同一报告、同一最终复核来源的 `--requirements-audit B.json`。
- 旧 v1 记录仍可读取，但不能满足新的交付验收。保留原始运行，在新审核或版本目录中处理。
- 复用语料和诊断输出时保留真实来源，不得把旧结果标为不同设置下的新审阅。

### Validation status / 验证状态

A recorded set of 100 relevant offline tests passed on 2026-10-06. See `docs/validation-v1.1.0-dev.json` for scope and provenance. Publication checks validate file inventories, hashes and frozen corpus boundaries. These checks do not establish scientific judgment, bilingual equivalence or independent-model quality. Controlled comparisons of diagnostic quality, live elapsed time and usage savings remain pending. Other audit documents in `docs/` describe the v1.0.0 baseline.

2026-10-06 已记录 100 项相关离线测试通过，范围和来源见 `docs/validation-v1.1.0-dev.json`。公开文件检查验证文件清单、哈希和冻结语料边界，不能证明科学判断、双语等价或独立模型审核质量。审阅质量、实际耗时与额度节省仍待受控对照验证。`docs/` 中其他审核文档描述的是 v1.0.0 基线。

## 1.0.0 — stable tagged baseline / 稳定标签基线

Four isolated review lanes, frozen supervisor concerns and published-paper cases, manuscript-based consolidation/verification, bilingual Markdown/PDF reports, and offline workflow/publication checks. The existing `v1.0.0` tag preserves this baseline; its code and corpora are not replaced by development changes.

四路独立审阅、冻结的导师关注点和已发表论文案例、依据稿件进行合并复核、中英双语 Markdown/PDF 报告，以及离线工作流和公开文件检查。已有 `v1.0.0` 标签保留这一基线，开发改动不替换其代码或语料。
