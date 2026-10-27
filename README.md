# MentorTrace

Version: [v1.2.0](VERSION)

[English](README.md) | [简体中文](README.zh-CN.md)


MentorTrace derives judgment patterns from an academic supervisor's actual comments and successive manuscript revisions, and draws on published papers that supervisor considers well written to help authors identify problems in a new manuscript's argument, technical support, organization and expression. During review, it follows the manuscript's argument chains, technical relationships and revision cues, continually asking whether explanations are sufficient, whether arguments are complete, and whether conclusions are supported by evidence. Each review comment identifies the relevant manuscript passage, explains the issue and its basis, and provides concrete revision suggestions. The results are organized into bilingual English–Chinese Markdown and PDF reports.

The current implementation runs as a **Codex skill with a Python workflow** and accepts **PDF manuscripts**. **LaTeX source input and output** are planned. It produces revision guidance and reports; automatically applying changes to the manuscript is not yet integrated.

## Changes from 1.1.0 to 1.2.0

- **Independent review with both libraries:** Advisor directly reviews the full manuscript. Concern guides problem checks; Expression guides concrete wording and later drafting. Both libraries remain complete.
- **Adaptive batching and concurrency:** size batches by model capacity and review workload, with up to three independent tasks running concurrently by default to reduce repeated input and waiting.
- **Leaner checks and reports:** combine repeated checks and explanations while retaining complete coverage, verification requirements and bilingual revision suggestions.

Capacity reserves, complete source coverage and frozen historical runs retain their contracts. The latest combined workflow has offline validation; elapsed time depends on the paper, model and necessary follow-ups, with no guaranteed two-hour runtime. See [workflow](.agents/skills/mentortrace/references/review-workflow.md), [batching](.agents/skills/mentortrace/references/advisor-batching.md) and [complete-request capacity](.agents/skills/mentortrace/references/request-capacity.md).

## Changes from 1.0.0 to 1.1.0

- **Two mentor libraries:** 493 Concern records describe what to explain or justify; 1,581 Expression examples show concrete wording, syntax and paragraph operations. Both ship with the skill and are enabled by default.
- **Organization and revision:** check paragraph tasks, information selection and transitions; draft concrete passages for retained issues and coordinate duplicate or conflicting suggestions.
- **Consistent modules and reports:** Reader, Expert, Advisor and Editor, with refined bilingual comments and suggested-revision presentation.

## Contents

- [Quick start](#quick-start)
- [Usage prompt](#usage-prompt)
- [Review architecture](#review-architecture)
- [Report contents](#report-contents)
- [Repository structure](#repository-structure)
- [Corpus sources](#corpus-sources)
- [Dependencies and execution guide](#dependencies-and-execution-guide)
- [Privacy and license](#privacy-and-license)

## Quick start

Ask Codex to download the repository and prepare the environment:

```text
Download the complete MentorTrace v1.2.0 repository or release package from https://github.com/stevenyyzhang/MentorTrace locally, verify VERSION, configure its required dependencies, check the environment, and tell me which repository directory to open in Codex.
```

Once setup is ready, open the downloaded repository root in Codex, place your PDF in a local `workspaces/` directory, and use the review prompt below. See [Dependencies and execution guide](#dependencies-and-execution-guide) for dependencies and model access.

MentorTrace is a repository-scoped skill requiring the scripts and corpora in the complete repository. Its entry point is [`.agents/skills/mentortrace/SKILL.md`](.agents/skills/mentortrace/SKILL.md); see the [official Codex guide](https://learn.chatgpt.com/docs/build-skills) for installation and repository skill discovery.

## Usage prompt

Once the environment is ready, replace the filename and enter this one sentence in Codex:

```text
$mentortrace Review workspaces/manuscript.pdf and produce bilingual English–Chinese Markdown and PDF reports with concrete revision suggestions.
```

The skill provides the review rules, individual checks and report requirements. Outputs are saved locally under `runs/`. If a model connection or dependency is unavailable, unfinished steps must be identified.

## Review architecture

The workflow prepares the PDF, reviews it through four lanes, merges and verifies the findings, develops revision proposals, and delivers bilingual Markdown and PDF reports.

```mermaid
---
config:
  htmlLabels: false
  flowchart:
    htmlLabels: false
---
flowchart TB
    F["Prepare PDF inputs<br/>Freeze inputs and rules"]
    O["Object and task plan"]
    C["Select and freeze cases"]
    R["Reader<br/>Comprehension<br/>and organization"]
    T["Expert<br/>Relationships<br/>and reasoning"]
    A["Advisor<br/>Independent review<br/>Concern + Expression"]
    L["Editor<br/>Wording, notation<br/>and formatting"]
    M["Consolidate retained findings"]
    V["Independent verification<br/>against manuscript evidence"]
    Q["Freeze initial results<br/>Source and execution checks<br/>Up to three independent packets"]
    D["Propose revisions<br/>Draft the bilingual report"]
    B["Coverage, facts and language checks<br/>Up to three independent packets"]
    OUT["Bilingual Markdown<br/>PDF and page inspection"]

    F --> O --> C
    C --> R
    C --> T
    F ----> A
    F ----> L
    R --> Q
    T --> Q
    A --> Q
    L --> Q
    Q --> M --> V --> D --> B --> OUT

    classDef input fill:#f8fafc,stroke:#94a3b8,color:#0f172a;
    classDef review fill:#eff6ff,stroke:#60a5fa,color:#172554;
    classDef output fill:#ecfdf5,stroke:#34d399,color:#064e3b;
    class F input;
    class O,C,R,T,A,L,M,V,Q,D,B review;
    class OUT output;
```

Arrows before review show data dependencies, not launch order. After prerequisites, the scheduler runs up to three initial calls concurrently: object and task planning and case selection serve Reader and Expert only. Advisor starts independently from the full manuscript, its current Concern batch and relevant examples from the bundled Expression library. Relevant Expression evidence also supports post-verification drafting.

| Module | Main inputs | Function |
| --- | --- | --- |
| Reader | Full manuscript, object and task plan, Reader cases | Check comprehension, argument flow and organization; identify explanatory gaps. |
| Expert | Full manuscript, object and task plan, Expert cases | Check technical relationships, assumptions, applicability and support for conclusions. |
| Advisor | Full manuscript, Concern requirements and relevant Expression examples | Independently check historical concerns and applicable wording or paragraph operations; retain only suggestions supported by the new manuscript. |
| Editor | Full manuscript, text units to inspect | Check language, notation, terminology consistency and formatting. |

Models perform all four review lanes. Historical concerns and paper cases guide the questions; every final finding still needs specific evidence from the new manuscript. In v1.2.0, source requirements and execution are checked together after initial freeze, followed by consolidation, verification and drafting. Frozen reports receive combined coverage, facts, conditions, bilingual and expression-realization checks. Tools check source hashes, accounting and exact excerpts; they do not certify scientific correctness. These changes still need controlled manuscript replay. See the [execution guide](.agents/skills/mentortrace/references/execution.md) for details.

## Report contents

The final files are **`report_bilingual.md`** and **`report_bilingual.pdf`**. See the [fictional Markdown example](examples/report_bilingual.md) and [PDF example](examples/report_bilingual.pdf) for the report format.

| Report section | Contents |
| --- | --- |
| How to use this report | Manuscript information, actual model and reasoning effort, revision priorities and use notes |
| **Content and technical comments** | Problems in claims, explanations, assumptions, methods, derivations or experiments, with locations, judgment grounds and revision actions |
| **Organization and flow comments** | Suggestions on information selection, order, transitions and organization, with applicability conditions and tradeoffs |
| **Language and presentation comments** | Specific corrections to wording, grammar, terminology, notation or presentation |
| Coverage and remaining checks | Actual review coverage, unresolved questions and facts the author must confirm or supply |

The three comment categories have separate numbering. Each comment presents the English location, original passage, explanation and suggested revision before its Chinese explanation; the original passage appears once. Confirmed issues, items requiring confirmation and optional suggestions remain distinct.

Content and technical comments receive a revision priority when applicable: **High** affects the main argument, method comprehension or reproducibility and should be addressed first; **Medium** concerns a local explanation, definition or claim scope. Priority describes revision importance, rather than confidence that a defect exists. Ordinary language corrections need no priority label.

Suggestions may include concrete English sentences, complete paragraphs, or instructions to move, delete or add material. Missing derivations, experimental details or implementation facts are identified as author-supplied information. Supported drafts and drafts conditional on specific confirmations are distinguished. The PDF is generated from the same Markdown, with content-preservation and page-layout checks.

See [report-language.md](.agents/skills/mentortrace/references/report-language.md) and [delivery-preservation.md](.agents/skills/mentortrace/references/delivery-preservation.md) for the full rules.

## Repository structure

```text
MentorTrace/
├── README.md                       English project guide
├── README.zh-CN.md                 Chinese project guide
├── .agents/skills/mentortrace/
│   ├── SKILL.md                    Skill entry point
│   ├── agents/openai.yaml          Skill display metadata
│   ├── references/                 Review, evidence and delivery rules
│   ├── scripts/                    Preservation audit and report renderer
│   └── assets/                     Report stylesheet
├── scripts/
│   ├── mentortrace_v1.py           Workflow and response validation
│   ├── prepare_paper.py            PDF annotation removal and extraction
│   ├── goodpaper_runtime.py        Published-case selection and loading
│   ├── run_authorized_stage.py     Optional isolated model calls
│   ├── prepare_revision_proposals.py
│   ├── audit_public_release.py     Public-file and corpus checks
│   ├── doctor.py                   Local dependency checks
│   └── ...                        Other validation and transport tools
├── config/                        Project and optional model settings
├── corpus/
│   ├── advisor-concerns-v4/        Current default: 493 conditional concerns
│   ├── advisor-expression-v1/      Enabled by default: 1,581 mentor expression examples
│   └── published-cases-v1/         Published-paper cases, indexes and citations
├── examples/                      Fictional bilingual report examples
├── docs/                          Corpus fields, case checks and validation
├── tests/                         Offline workflow and public-package tests
├── requirements.txt
├── VERSION
├── LICENSE                        MIT for code, instructions and documentation
├── LICENSE-CORPUS.md               CC BY 4.0 for analytical corpora
└── THIRD_PARTY_NOTICES.md          Original-paper and dependency rights
```

`workspaces/` and `runs/` are created during local use and ignored by Git. They hold manuscripts, execution records and generated reports.

## Corpus sources

The corpora draw on two sets of manuscript materials:

**Papers from the research group revised by the supervisor.** The materials cover **24 papers**, each with multiple available annotated or revised versions. They support two linked libraries: **Concern** records describe what the mentor asks authors to explain or justify, together with judgment grounds and applicability boundaries, such as concepts, information links, assumptions, derivations and claim support; **Expression** records preserve mentor-proposed wording, syntax and conditional deletion, movement or paragraph restructuring derived from actual edits. Concern guides what to check; Expression guides how to express it. Records may link across libraries or stand independently, and Advisor and later drafting use them according to the target manuscript. Separate revision phases of the same paper count as one paper. Original manuscripts, literal mentor comments and private revision histories are excluded. Needed manuscript/author excerpts in Expression remain separately labeled from analyst accounts. Learning means retrieving examples for model reference, not fine-tuning parameters.

**Published papers the supervisor considers well written.** The current cases cover **52 papers**, primarily in wireless communications. Reader and Expert cases are developed from specific arguments and writing passages: Reader cases concern explanations, information arrangement and comprehension; Expert cases concern technical relationships, prerequisites, argument support and claim scope. Models produced the case analyses; these have not received item-by-item supervisor confirmation. Recommending a paper does not imply endorsing every case interpretation. Cases retain public bibliographic references. Original paper PDFs are not bundled.

Cases record source observations and analytical summaries, including relationships or approaches recurring across multiple papers. They do not establish strengths shared by every paper or automatically prove that one writing approach is better. Source facts, analyst interpretations and transfer judgments are distinguished; applicability must be checked against the new manuscript.

## Dependencies and execution guide

| Dependency | Purpose |
| --- | --- |
| Python 3.10+ and `requirements.txt` | Workflow, validation and document processing |
| Poppler: `pdftotext`, `pdftoppm` | PDF text and page extraction |
| Pandoc | Markdown to HTML |
| Chrome/Chromium or Edge | Local PDF generation |
| English and Chinese fonts | Bilingual typesetting |
| Authorized model access | Actual review; the optional CLI path also needs an available Codex CLI login |

Non-Python dependencies are installed separately. For ordinary use, prepare the environment above and invoke the skill. Stage commands, case selection, capacity checks and recovery instructions are documented in [execution.md](.agents/skills/mentortrace/references/execution.md).

If the skill is missing, check that the complete repository root is open. Repair unreadable text, equations or pages before review. If a model's capacity is insufficient, rearrange complete inputs rather than truncating necessary manuscript content or records.

## Privacy and license

Original manuscripts, literal mentor comments, source pages, identity mappings, private revision histories and local paper paths are excluded. Expression contains only admission-reviewed accounts and separately labeled necessary manuscript excerpts. Inputs, reports, logs and credentials remain local. Inspect actual files before publishing: Git ignore rules do not remove tracked content.

Code, skill instructions and documentation use [MIT](LICENSE). Original analytical records under `corpus/` use [CC BY 4.0](LICENSE-CORPUS.md); copying, modifying or redistributing them requires project attribution, source citations and change notices. Original paper rights remain with their rights holders; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
