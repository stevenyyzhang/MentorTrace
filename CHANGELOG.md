# Changelog / 版本变更

## 1.2.0 — Adaptive review and concurrent checks / 自适应审阅与并行检查

2026-10-27.

Release package follow-up: simplify both READMEs, synchronize project version metadata, check the tokenizer dependency, and remove the tests' reliance on a pre-existing private directory. All 410 offline tests pass in an isolated extracted package; no original-project file access or model calls. / 发布包修订：精简双语 README，统一项目版本号，补全 tokenizer 依赖检查，移除测试对预先存在的 private 目录的依赖。隔离解压包通过全部 410 项离线测试，不读取原项目文件，不调用模型。

- Preserve all 493 Concerns and 1,581 Expressions in direct independent Advisor review, with distinct requirement and expression responsibilities and reviewed conditional links.
- Detect model capacity and apply complete-request token/image/output/system and transport budgets across new adaptive runs. Minimize Advisor batches, prefer at most 12 and automatically permit necessary overflow; preserve reserves and historical protocols.
- Reduce repeated input/output with reversible references, separate review/draft views, explicit grouped judgments and program-generated exact locators. Missing work never becomes an implicit pass.
- Default initial lanes and independent source/delivery check packets to three isolated workers. Retain sequential dependencies, cached-result provenance and inspect-first failure handling.
- Carry connected complete Expression sources into drafting. Combine related post-processing checks, explicitly reuse unchanged verified claims, and shorten repetitive reports while retaining both languages and both delivery gates.
- Validate offline contracts, source integrity and saved-result compatibility. Latest end-to-end runtime and semantic quality are not newly measured by this release.

- Advisor 保留全部 493 条 Concern 和 1,581 条 Expression，直接独立审阅全文，明确问题检查与具体表达指导的分工，关联保留适用条件。
- 新自适应运行统一读取模型容量，检查完整请求与传输限制；Advisor 尽量减少批数，优先不超过 12 批，必要时自动增加，预留与历史协议不变。
- 用可还原引用、审阅／起草视图、明确的分组判断及程序定位减少重复；未完成内容不冒充已审阅。
- 初审与独立后处理分包默认最多三路并行；依赖阶段顺序执行，保留缓存来源和失败记录，不自动重试。
- 相关完整 Expression 材料继续参与起草；合并相关检查，明确复用未变化的核验判断，减少报告重复，保留双语与两道交付校验。
- 完成离线协议、来源完整性和保存结果兼容性验证；本次发布不代表最新完整流程耗时或语义质量已经重新实测。

## 1.1.0 — release / 正式版

2026-10-15. Bundle the admission-reviewed 1,581-record Expression library with the skill. New CLI runs use it by default for independent Advisor review and related drafting; --expression selects another snapshot and --no-expression creates an explicit baseline. Update the bilingual README with concise changes from 1.0 and plain definitions of Concern and Expression. Ship only the current Concern v4; retain v1–v3 in historical releases or local archives. Preserve existing frozen runs, source evidence, historical releases and actual model provenance.

2026-10-15。将准入复查保留的 1,581 条 Expression 与 skill 同仓分发，新 CLI 运行默认用于 Advisor 独立审阅及后续起草；`--expression` 可替换快照，`--no-expression` 可建立禁用对照。双语 README 改为简要版本增量，并解释 Concern 与 Expression 的含义和来源。正式包只带当前 Concern v4，v1–v3 留在历史发布或本地归档中。旧冻结运行、原始证据、历史版本与实际模型来源记录保留。

## 1.1.0-dev.4 — editorial learning and source transfer / 行文学习与来源迁移

2026-10-13 editorial selection: new runs use Reader v4 (a grounded no-change baseline and nullable candidate) and editorial selection v1 (merge/verify decision groups with source dispositions and a compatible preferred path). Apply the same net-benefit rule to Concern, Expression and good-paper transfer. Preserve frozen v1–v3 protocols and old reports. The separate V8 49-comment re-adjudication is a scoped recovery exercise, not a new four-module benchmark or evidence of general improvement.

2026-10-13 篇章取舍：新运行启用 Reader v4，允许有原文依据的保留决定；合并和验证按读者任务形成决策组，记录首选路径、收益、代价和放弃方案的依据。Concern、Expression 与优秀论文迁移采用同一收益判断。旧运行与原报告保留；V8 的49条重判仅属本次限定范围处理，不充当新的四模块评测或普遍改进证据。

2026-10-09 paragraph follow-up: resolve 13 review samples under delegated assistant judgment; independently learn four omitted long mentor annotations, admit three bounded paragraph/section examples and hold one unresolved definition/theorem candidate. Activate the 238-record private snapshot. Preserve exact mentor proposals and distinguish observed later bodies, unknown writers and subsequent mentor corrections. Require Expression-led intake and exclude held operations from transfer. Prior snapshots and A/B/C outputs remain unchanged.

2026-10-09 段落学习补充：按用户委托复核13个样例，独立补学四条遗漏的导师长批注，三条有条件入库、一条定义与定理依赖未解决而暂存，私有运行库增至238条。完整导师提议、后续正文、未知执笔者及后续导师纠正分别留存；Expression需独立选材，暂缓动作不能迁移。旧快照及A/B/C输出保留。

2026-10-09 authorized tranche completed: learn 89 selected source packets, preserve 236 local Expression records, and freeze a reviewed runtime snapshot with 235 records after holding one. Complete the connected 12-Concern/20-Expression audit and scoped A/B/C comparison. A/B are broadly tied in auxiliary assessment; C has broader coverage, overlap and additional calls/input. Preserve actual mentor text, original outputs, authorization and usage. Full historical review and stable mentor fit remain unvalidated.

2026-10-09 本轮授权范围完成：89个选定来源包学习留存236条局部Expression，关联核对后235条进入新运行快照，1条暂停迁移，旧快照保留。完成12条Concern/20条Expression核对及三组开发比较；辅助判断A/B基本持平，C覆盖更广且有重复和额外调用。实际导师原文、原始输出、授权和用量均留存；完整历史复核与稳定导师偏好仍未验证。

2026-10-08 subsequent authorized implementation: add private Expression snapshots,
independent Advisor task retrieval and source-bound drafting attribution. Bind original
published-page prose to selected cases. Actual mentor proposals remain distinct from
model analysis and new suggested prose. Real source learning and a scoped A/B/C
development comparison have private audit records; legacy protocols stay compatible.

2026-10-08 后续授权实施：新增私有 Expression 快照、Advisor 独立篇章任务检索和起草归因，绑定优秀论文原页文本。导师实际提议、模型分析和新稿建议分别保存。来源学习及三组开发对照保留私有审核记录；不宣称已验证导师风格或已完成全部历史材料整理。详见[实际接入与限制](docs/expression-integration-dev.4.md)。

2026-10-08 naming update: the four review modules are Reader, Expert, Advisor and Editor. Rename current skill references and synchronize prompts, diagrams, configuration, status output and documentation. New requests carry explicit module names; historical `technical`/`language` serialization identifiers and frozen request contents remain compatible. The proposed mentor expression-example library is named Expression; no training or model review is started by this rename. Earlier packaged snapshots retain their original names and validation scope.

2026-10-08 名称更新：四个审阅模块统一为 Reader、Expert、Advisor、Editor，同步当前 Skill 文件、提示词、架构图、配置和状态输出。旧运行标识及冻结请求保留兼容；计划中的导师表达案例库统一称为 Expression，本次更名没有启动训练。此前已打包快照保持其原有名称与验证范围。

2026-10-08. Built on the dev.3 public snapshot, retaining its 493-card concern corpus and published-case bytes. Earlier releases and frozen reviews remain unchanged.

- Learn editorial episodes with explicit before/context/feedback/after/follow-up evidence, component authorship, chronology, source-family dependence and conflicts. A local preparation/check tool creates private candidate lessons; it does not promote them or infer mentor acceptance.
- New runs record source-to-target writing distinctions in Reader and independent Advisor, including selection, emphasis, paragraph roles and coordinated repairs. Every optional organization proposal links to its evidence. Sufficient, nonmatching, unknown and unfinished outcomes remain valid.
- Preserve these records through both finding and optional-suggestion dispositions. Drafting receives full connected Reader accounts and complete relevant concern fields, with duplicate raw diagnostics kept in the private audit file. Attribute actual report wording to target evidence and recorded source use; legacy associations remain explicitly weaker.
- Preserve lane isolation, frozen legacy protocols, unvalidated-recipe exclusion and existing delivery gates. No additional review lane or automatic model call is introduced. Local attribution checking complements the independent semantic/final-text audits.
- The working tree already contained report-language and proposal-preparation edits beyond dev.3. They were preserved, not credited as newly implemented here.

- 在 dev.3 上补上“历史修改事件→条件性行文认识→本稿具体动作→实际建议文本”的记录与运行链路；保留 493 条 concern 和原案例库，不用增加数量代替学习。
- 新稿审阅对案例迁移、导师 concern 的篇章作用及可选篇章动作留存来源；起草恢复完整相关材料，并明确旧运行未记录的来源影响。
- 初次机制实现完成本地协议与来源追踪验证；该阶段没有重新训练模型或重新审稿。后续授权调用见上方日期记录，仍未证实导师偏好或因果质量提升。

See [design and limits](docs/editorial-learning-dev.4.md) and [validation](docs/validation-v1.1.0-dev.4.json).


## 1.1.0-dev.3 — development update / 开发版更新

2026-10-08. Corpus integration on the dev branch, based on 1.1.0-dev.2. This update does not create a stable release or replace earlier tagged snapshots.

- Default Advisor runs and project configuration now use advisor-concerns-v4: 493 complete English cards, preserving the original 437 and adding 56 conditional abstractions. The 481-card and 490-card intermediate snapshots remain available for frozen runs; published-case contents are unchanged.
- Apply historical-intake rules to supplied PDF feedback and LaTeX variants: read related edits jointly, retain version responses and corrections, verify blank-mark links, and distinguish diff inventories from actual semantic reading. Unknown modifiers and unresolved evidence remain unknown.
- Synchronize both READMEs with actual source grouping, six decision fields, snapshot counts and training-exposure limits. Public records use opaque source links; manuscripts, verbatim feedback, identities, filenames, local paths and private version histories remain local.
- Run scoped integrity, public-file anonymity and runtime integration checks. These checks do not establish scientific correctness, complete concern recall or improved diagnostic quality. No new model review is performed.

- Advisor 与项目配置默认使用 v4：493 条完整英文卡片，保留原 437 条，新增 56 条；481 条和 490 条中间快照继续供冻结运行使用，已发表论文案例内容不变。
- 混合 PDF/LaTeX 历史提炼联合读取相关修改，保留版本回应与后续修正，验证空白标记的实际关联，并区分差异清单与语义阅读；修改者未知及未解证据继续如实保留。
- 中英 README 同步来源分组、六字段、快照数量及训练暴露边界。公开记录使用匿名来源链接，原稿、批注原文、身份、原文件名、本机路径与私有版本历史仅在本地保存。
- 完成相关完整性、公开文件匿名性和运行集成检查；这些检查不证明数学正确、concern 无遗漏或诊断质量提升。本次未调用模型重新审稿。

Current scoped validation is recorded in [validation-v1.1.0-dev.3.json](docs/validation-v1.1.0-dev.3.json). Earlier validation documents retain their historical scope.

## 1.1.0-dev.2 — pre-release / 预发布版

2026-10-07. Source-fidelity development update, published as a new prerelease from the dev branch. Earlier release records retain their historical baseline scope.

- Add source-fidelity rules: raw extraction is a locator; page images govern decisive notation. Formula-dependent verification records bind observed expressions and symbol roles to page-image hashes.
- Freeze neutral inline split-word candidates and require Language to dispose of each with image evidence; page-level coverage alone is insufficient.
- Carry checked source transcriptions into report drafting and require readjudication of affected comments/actions when correcting a quotation contradicts their premise.
- Preserve frozen older protocol contracts and existing consolidation, Phase A/B and version 2 delivery gates. Both frozen corpora are unchanged. Local contract tests do not establish improved review accuracy or complete recall.

- 新增源文保真规则：提取文本用于定位，原页决定关键符号；依赖公式的复核记录将所见原式、符号作用与页图哈希绑定。
- 冻结中性的行内断词候选，Language 须逐项依据页图处置，整页已检查不能代替候选核查。
- 报告起草复用已核对的原文转写；修正摘录后若推翻意见前提，须重新裁定相关意见和修改动作。
- 保留旧冻结协议及现有合并、Phase A/B 和 v2 交付门槛；两套冻结语料未改。本地协议测试不能证明审阅准确率或召回率提升。

Local validation on 2026-10-07: 62 scoped tests passed across source fidelity, surface review, pipeline, consolidation, delivery integration and execution efficiency. Relevant Python syntax, skill scalar frontmatter and local links passed checks. A local manuscript regression located the demonstrated inline split-word candidate. No new model review or report regeneration was performed. Publication-specific checks are recorded in docs/validation-v1.1.0-dev.2.json.

2026-10-07 本地验证：源文保真、语言审阅、流程、合并、交付集成和执行效率的 62 项局部测试通过，相关 Python 语法、Skill 标量元数据和本地链接检查通过。本地稿件回归检查定位到已知的行内断词候选。本次未调用模型重新审阅或重新生成报告。发布检查见 docs/validation-v1.1.0-dev.2.json。

## 1.1.0-dev.1 — pre-release / 预发布版

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
