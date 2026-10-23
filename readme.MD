# Model Router

**Model Routing Evaluation on MMLU & GSM8K**

An experiment in choosing the right language model for each question—and measuring whether routing is worth it.

The goal is to compare a router against fixed-model baselines on answer quality, latency and estimated API cost. A useful result might be lower cost at similar quality; finding that a routing strategy does not help is also a valid outcome.

**Status: first evaluation complete.** Fixed-model baselines, oracle/format replays, Decisions predicate/choice judging and a development-selected cascade policy have been evaluated. This repository is a reproducible evaluation project; a live routing gateway is not implemented.

## Main result

**On the reserved 80-question evaluation split, the fixed Decisions cascade matched Luna’s benchmark accuracy but cost about 3.2× as much.** Seven questions were escalated to Sol; none changed from unsuccessful to correct or from correct to unsuccessful.

| Strategy | Correct | Accuracy | Estimated scenario cost | Mean recorded/simulated latency |
| --- | ---: | ---: | ---: | ---: |
| gpt-6-luna | 75/80 | 93.75% | $0.004304 | 2.592 s |
| gpt-6-sol | 76/80 | 95.00% | $0.059370 | 1.714 s |
| Luna → Decisions choice → Sol (0.60) | 75/80 | 93.75% | $0.013869 | 3.060 s |

The candidate was chosen on 120 development questions: a 0.60 escalation-probability threshold produced 117/120 correct versus Luna’s 116/120, at roughly 3.1× estimated cost. The threshold and judge rubric were then frozen before collecting the OpenAI evaluation outputs; they were not retuned against the evaluation result.

**Conclusion:** this experiment did not demonstrate that the tested Decisions-based escalation policy improves the quality/cost trade-off over using Luna alone. This does not establish that all routing or cascade approaches fail.

Costs include every attempted call in the simulated strategy, including Decisions overhead. Cascade latency is a sum of recorded standalone request durations, not a live end-to-end measurement. The historical source pool had already been evaluated with Gemma, so the reserved split is not a pristine unseen holdout. Strict-v2 format penalties and question ambiguity also limit interpretation.

### Read the experiment

- [Final fixed-policy evaluation](reports/fixed-policy-test.md) — the main comparison.
- [Development threshold sweep](reports/threshold-sweep-dev.md) — how 0.60 was selected.
- [Development answer review](reports/dev-baseline-review.md) — format issues and ambiguous questions.
- [Predicate Decisions review](reports/decisions-luna-dev.md) and [choice review](reports/decisions-luna-dev-choice.md).
- [Evaluation collection notes](reports/fixed-policy-collection-notes.md) — one failed request and recovery without regenerating saved answers.

### Reproduce from saved outputs — no paid requests

```bash
python -m pytest -q
python -m eval.choice_cascade
python -m eval.threshold_sweep
python -m eval.frozen_policy
```

All required baseline outputs and judgments are included. The fixed-policy command verifies frozen input hashes. Model-generation and Decisions-collection commands later in this README are optional paid recollection steps; they are not required to inspect or reproduce the saved analysis.

## What's implemented

- OpenAI Responses API client for **GPT-6 Luna, Sol and Astra**.
- A 200-question dataset built from MMLU and GSM8K.
- Frozen, stratified development and evaluation splits.
- Versioned scoring with separate incorrect, unparseable and incomplete outcomes.
- Per-question JSONL records and pairwise model comparisons.
- Offline tests for scoring, dataset splitting, mocked API behavior and cascade accounting.
- Decisions-based acceptance judgments, selective escalation sweeps and fixed-policy evaluation.
- Dated pricing estimates, per-case repairs/regressions and input provenance hashes.

Historical Ollama/Gemma runs remain in the repository as earlier experiments. Running the current project does not require Ollama or a local GPU.

## Quick start

Use Python 3.11 or newer. Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For a fresh checkout, create your local configuration:

```bash
cp .env.example .env
```

If `.env` already exists, edit it instead of replacing it. Set your key locally:

```dotenv
OPENAI_API_KEY=your-key-here
```

The application loads `.env` from the repository root. Existing environment variables take precedence. `.env` is ignored by Git; `.env.example` must contain no credentials.

Verify the setup without paid requests:

```bash
python -m pytest -q
python -m eval.run_model --help
```

### First API run

The following evaluation commands make **paid API requests**. Begin with three development questions per model—nine requests in total:

```bash
python -m eval.run_model --all --split dev --limit 3
python -m eval.summarize --split dev
```

To evaluate a single model:

```bash
python -m eval.run_model gpt-6-luna --split dev --limit 10
```

Results are protected against accidental replacement. If you previously ran the small sample and now want the full development baseline, explicitly replace that split's model result files:

```bash
python -m eval.run_model --all --split dev --overwrite
python -m eval.summarize --split dev
```

The full development run makes **360 requests: 120 questions × three models**. `--overwrite` replaces existing results; it does not resume them. Copy any experiment you want to retain before replacing it.

## Model configuration

| Role in this experiment | API model ID |
| --- | --- |
| Efficient baseline | `gpt-6-luna` |
| Middle tier | `gpt-6-sol` |
| High-capability baseline | `gpt-6-astra` |

Sol is explicitly GPT-6 Sol, rather than GPT-6.1 Sol. Roles describe the intended comparison; they do not establish which model performs best on every question.

The client in [`models/openai_client.py`](models/openai_client.py) uses:

- Responses API with `reasoning.effort=low` for all three models.
- A maximum output budget of 4,096 tokens, including reasoning tokens.
- Standard/default service tier, without a temperature override.
- A 120-second SDK timeout and no automatic SDK retries.
- `store=False`.

Model access and rate limits depend on your OpenAI API account. An API failure stops the current run; rows already written remain available. Automatic resume and per-case request-error records are not implemented.

## Dataset

The source pool is stored in `eval/data/test_set.jsonl`; despite its historical filename, it is the source for both splits.

| Category | Source pool | Development | Evaluation |
| --- | ---: | ---: | ---: |
| Elementary mathematics | 25 | 15 | 10 |
| High-school geography | 25 | 15 | 10 |
| College physics | 25 | 15 | 10 |
| Formal logic | 25 | 15 | 10 |
| Math word problems | 100 | 60 | 40 |
| **Total** | **200** | **120** | **80** |

The first four categories come from MMLU; math word problems come from GSM8K.

The generated split files are included in the repository. To reproduce or verify them without API calls:

```bash
python -m eval.split_dataset
```

Splitting uses seed 42, preserves category proportions and keeps the three previously reviewed smoke-test questions in development. The manifest records the source SHA-256 and split details. The command refuses to replace existing files if the generated content differs.

**The evaluation split is not a pristine holdout.** The original question pool had already been evaluated with Gemma and its aggregate results reviewed before splitting. Use development data for future routing and prompt changes, reserve evaluation data for later comparisons, and collect new unseen questions before making final generalization claims.

Once routing rules are frozen, run the reserved evaluation portion explicitly:

```bash
python -m eval.run_model --all --split test
python -m eval.summarize --split test
```

This makes 240 requests. Avoid repeatedly tuning against these results.

To download the source benchmarks and rebuild the original pool:

```bash
python -m eval.build_test_set
```

Rebuilding the source does not update frozen splits automatically. A changed source requires a deliberately versioned dataset/split update.

## Scoring

[`eval/scoring.py`](eval/scoring.py) implements `strict-v2`:

- **Multiple choice:** accept a clear answer such as `C`, `**C**` or `The answer is C`. Reject ambiguous responses such as `B or C` and explanations that do not match the accepted answer form.
- **Numbers:** accept one complete numeric value after a single `####` marker, or a response consisting entirely of a numeric value. Supported forms include decimals, grouped thousands, scientific notation and fractions.
- **No last-number fallback:** a number merely mentioned in prose is not treated as the final answer.

Parsed answers are marked `correct` or `incorrect`; answers that cannot be parsed are `unparseable`. A non-completed API response is recorded separately as `incomplete` and cannot count as correct. These unsuccessful cases remain in the accuracy denominator.

Scoring measures these benchmark answer formats, not general conversational quality. Historical saved scores are preserved and are not automatically recalculated with the new scorer.

## Results and comparison

```text
eval/results/
├── dev/                 # Current development runs
├── test/                # Reserved evaluation runs
└── *.jsonl              # Historical Gemma and OpenAI smoke-test runs
```

Each new row records:

- Question ID, requested model, returned model ID and raw answer.
- Extracted answer, scoring outcome and scorer version.
- Dataset split and the full split file's SHA-256.
- Input, output, cached-input and reasoning-token counts.
- End-to-end request duration, response ID and completion details.
- Reasoning effort and maximum output-token setting.

Cached input is a subset of input tokens; reasoning tokens are part of output tokens. Do not add either subset a second time when calculating totals.

The summary reports accuracy, average request latency, token totals, unparseable/incomplete counts and pairwise answer agreement. Pairwise comparisons require matching dataset/scorer metadata and identical, unique question IDs. Use the same sampling and generation settings for comparable experiments.

Cascade reports estimate API cost using the explicit dated pricing snapshot in `eval/pricing.json` and the recorded Decisions pricing assumption. They are not billing statements. Latency percentiles and confidence intervals are not implemented.

Inspect older runs explicitly:

```bash
python -m eval.summarize --split legacy gemma3:4b gemma3:12b
python -m eval.summarize --split legacy gpt-6-luna gpt-6-sol gpt-6-astra
```

These commands read saved results and make no API calls. Historical latency definitions and scorer versions may differ from current runs.

### CLI options

| Option | Behavior |
| --- | --- |
| `model_name` | Evaluate one selected model |
| `--all` | Evaluate all three models; cannot be combined with `model_name` |
| `--split dev\|test` | Select questions and result directory; defaults to `dev` |
| `--limit N` | Use at most N questions per model |
| `--step N` | Select every Nth question before applying the limit |
| `--overwrite` | Replace existing result files for the selected models and split |

## Project structure

```text
models/openai_client.py       # API client and shared model settings
eval/question.py              # Question schema
eval/build_test_set.py        # Benchmark download and source-pool builder
eval/split_dataset.py         # Reproducible development/evaluation split
eval/scoring.py               # Answer parsing and scoring
eval/run_model.py             # Evaluation CLI and result records
eval/summarize.py             # Offline summaries and pairwise comparisons
eval/decisions_check.py       # Paid judge collection and offline judge reports
eval/choice_cascade.py        # One-step choice-based replay
eval/threshold_sweep.py       # Development-only threshold exploration
eval/frozen_policy.py        # Fixed candidate evaluation
eval/cascade_policy.json      # Frozen settings and input hashes
reports/                     # Findings, summaries and case-level traces
eval/data/                    # Source pool, frozen splits and manifest
eval/results/                 # Saved model outputs
tests/                        # Offline tests
```

## Scope and future work

The first evaluation is complete. Its scope is MMLU/GSM8K question answering, not a general-purpose router. The reserved evaluation set has now been used; further policy tuning requires a new validation plan rather than treating it as untouched data.

Possible follow-up experiments include a new representative dataset, a more reliable answer verifier, or a different model pair. Any new approach should retain fixed-model baselines and account for its judging/routing overhead. A live gateway, caching, dashboard and Docker packaging are outside this first evaluation.

## Official references

- [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)

## Oracle cascade simulation

The offline oracle tries Luna first, then Sol if Luna's saved answer is unsuccessful, then Astra if Sol is also unsuccessful. It uses reference-based saved correctness to decide when to escalate: this is a theoretical comparator, not a usable failure detector.

```bash
python -m eval.oracle_cascade --split dev
```

No API calls are made. Complete, matching result sets are required. Original model outputs are preserved; Markdown, JSON summaries and per-case JSONL traces are written to `reports/oracle-cascade-dev.*`.

Each attempted call contributes its full estimated token cost and recorded request duration, including unsuccessful lower-tier attempts. All three fixed-model baselines are reported alongside the oracle. Costs use `eval/pricing.json`, an explicit dated Standard short-context model-page snapshot; they are estimates rather than invoice totals. Cached input and reasoning tokens are not double-counted. Long-context pricing, explicit cache writes, tools and regional adjustments are outside this calculation.

Simulated latency sums recorded standalone calls. A live cascade would also incur routing/verification overhead and may have different cache/network conditions. Existing strict-v2 format penalties and benchmark ambiguity remain unchanged. Pricing sources and input file hashes are recorded with the report. `--pricing PATH` selects another compatible pricing snapshot; `--report-dir PATH` selects an output directory. The 80-question evaluation split is not read when running with `--split dev`.

## Format-only cascade replay

```bash
python -m eval.format_cascade --split dev
```

This offline policy tries Luna first and escalates only when a response is incomplete or cannot be parsed under the task's answer-format contract. Selection receives answer type, response text and completion status; reference answers and saved correctness do not determine escalation. A well-formed wrong answer is accepted, which is an intentional limitation to measure.

The report compares fixed-model baselines, oracle and format-only cascade using identical saved outputs and pricing. All attempted calls contribute cost and simulated sequential duration. Final correctness is evaluated after selection. Results are written to `reports/format-cascade-dev.md`, `.json` and `.jsonl`; no new API calls occur. This is a replay of a runtime-available policy, not a live cascade executor; API-error fallback and verifier overhead are not implemented.

## Decisions review of saved Luna answers

```bash
python -m eval.decisions_check --limit 1
python -m eval.decisions_check --resume
python -m eval.decisions_check --report-only
```

The first two commands make paid Decisions requests. The first checks one answer; resume evaluates remaining development answers without repeating saved judgments. Luna generation is not rerun. Only question text and candidate answer are sent; expected answers and benchmark labels remain local. A fixed predicate probability threshold of 0.5 maps to yes/accept or no/escalate; a refusal is unknown. No cascade calls are made yet.

The rubric evaluates substantive answer quality and permits harmless unit suffixes and justified ambiguity objections, so disagreements with strict-v2 need manual review. Counts show accepted/rejected answers against saved benchmark correctness. With only four unsuccessful benchmark cases, this is an exploratory development experiment, not a reliable general failure-detector benchmark.

Judgments are append-only in `eval/results/decisions/luna-dev.jsonl`; input and policy hashes protect resume. Report-only requires no API calls. API errors stop the run; inspect before resuming because a lost response may have incurred a charge. The report estimates Decisions input cost separately from generation cost. The SDK HTTP client calls `/decisions` directly for SDK versions lacking a typed Decisions method.

### Compare Decisions choice mode

```bash
python -m eval.decisions_check --mode choice
python -m eval.decisions_check --mode choice --report-only
```

Choice mode returns `accept` or `escalate` directly; no confidence threshold is applied. It uses the same task/answer inputs and evaluation instructions as predicate, plus explicit choice descriptions. Choice probability distribution and confidence are saved separately. Results and reports have a `-choice` suffix, so existing predicate records remain unchanged. `--resume` and `--limit` work in either mode. Comparisons are exploratory single runs, not proof that differences are caused only by API mode.

### Replay one escalation: Luna → Decisions choice → Sol

```bash
python -m eval.choice_cascade
```

This offline report uses existing development outputs and saved choice judgments. Accept keeps Luna; escalate replaces it with Sol once, with no second judge or Astra stage. It compares final accuracy with Luna/Sol baselines and explicitly counts repaired and regressed answers. Total estimated cost includes Luna, every Decisions call, and Sol only for escalations; simulated latency includes the same sequential steps. No API calls are made. Inputs and judgments are validated by IDs, dataset/scorer settings and hashes. Reports are written to `reports/choice-cascade-dev.md`, `.json` and `.jsonl`.

### Explore selective escalation thresholds (development only)

```bash
python -m eval.threshold_sweep
```

Replays the saved choice experiment at escalation-probability thresholds 0.5, 0.6, 0.7, 0.8, 0.9, 0.95 and 1.0. Sol is used only when the returned choice is `escalate` and `1 - P(accept)` meets the threshold. This does not use the separate confidence field. Every cascade retains Decisions cost and duration on every question, even when no Sol calls occur. The report includes a true Luna-only baseline without judge overhead, and counts repairs/regressions. No API calls occur. Artifacts are saved as `reports/threshold-sweep-dev.*`. Selecting a development threshold is not held-out validation.

### Fixed candidate policy evaluation

Candidate `choice-luna-sol-060-v1` freezes the development-selected 0.60 escalation threshold and judge rubric in `eval/cascade_policy.json` before evaluation collection. It uses Luna and Sol only.

```bash
python -m eval.run_model gpt-6-luna --split test
python -m eval.run_model gpt-6-sol --split test
python -m eval.decisions_check --mode choice --split test
python -m eval.frozen_policy
```

The first three commands make paid requests (80 Luna, 80 Sol, 80 Decisions for a complete fresh evaluation). The last command replays the fixed rule offline, includes judge overhead and reports repairs/regressions. Do not tune the threshold on these results. Frozen code/data hashes are checked before replay. The reserved source pool was historically evaluated with Gemma, so it is not a pristine holdout.
