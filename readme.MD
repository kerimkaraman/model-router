# Model Router

Evaluate OpenAI models on identical questions, then build a router balancing quality, latency and API cost.

## Status and models

Baseline evaluation is implemented; routing is not implemented yet. Ollama is no longer needed. Historical Gemma results are retained separately.

- `gpt-6-luna`: efficient baseline.
- `gpt-6-sol`: middle tier, explicitly GPT-6 Sol (not GPT-6.1 Sol).
- `gpt-6-astra`: high-capability baseline.

All use Responses API, `reasoning.effort=low`, Standard/default service tier, and a 4096-token output budget including reasoning tokens. No temperature is sent. Incomplete outputs are recorded and counted as unsuccessful. Availability depends on your API account.

## Setup

From this repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

A local `.env` is prepared. Add your real key locally:

```dotenv
OPENAI_API_KEY=your-key-here
```

For a fresh clone, copy `.env.example` to `.env`. `.env` is ignored by Git; environment variables take precedence. Never put real credentials in `.env.example`.

## Run

These commands make paid API calls. Start with three questions per model:

```bash
python -m eval.split_dataset
python -m eval.run_model --all --split dev --limit 3
python -m eval.summarize
```

Single model:

```bash
python -m eval.run_model gpt-6-luna --limit 10
```

Full development evaluation: 120 questions x 3 models = 360 requests:

```bash
python -m eval.run_model --all --split dev --overwrite
```

Existing files are protected unless `--overwrite` is explicit. `--step N` selects every Nth question; `--limit` applies afterward. On request failure the run stops, preserving already written rows. SDK retries are disabled to avoid hidden baseline retries.

Results record input/output/cached/reasoning tokens, request latency, response ID, returned model, completion status, and generation settings. Cached input is part of total input; reasoning tokens are part of output tokens. Do not add them twice. API cost calculation is not implemented yet; usage is retained for later pricing. No paid model evaluation was run during migration.

To inspect the old baseline:

```bash
python -m eval.summarize --split legacy gemma3:4b gemma3:12b
```

Summary comparisons require identical, unique question IDs. Default summary includes all available selected OpenAI models.

## Dataset and scoring

The existing 200 questions contain 100 MMLU and 100 GSM8K problems. To rebuild (downloads datasets):

```bash
python -m eval.build_test_set
```

Scorer `strict-v2` distinguishes correct, incorrect and unparseable outputs. Choice answers must follow a clear answer form; ambiguous explanations are rejected. Numeric answers require `####` followed by a complete numeric value on that line, or an entirely numeric response. Decimal, scientific notation, grouped thousands and fractions are supported. There is no fallback to the last number in prose. Incomplete model responses are unsuccessful separately from parsing failures.

## Development and evaluation separation

`python -m eval.split_dataset` creates a frozen, seeded, stratified 120/80 split from the original source pool. Category proportions are preserved and the three reviewed smoke-test cases remain in development. The source file and historical results are preserved. The manifest records the source hash and split seed; rerunning refuses to overwrite a different split.

**This is not a pristine holdout:** the original 200 questions already had Gemma results and aggregate analysis before splitting. Use dev for rule/prompt tuning; reserve test for later comparisons, but obtain new unseen questions for a final generalization claim. The split separates future workflows, not past exposure.

Default runs and summaries use dev. Results live under `eval/results/dev/` and `eval/results/test/`, with dataset hash and scorer version recorded. Old root-level results are available with `--split legacy`; their saved scores are not rewritten. Do not compare legacy scores as though they used strict-v2.

After freezing routing rules, evaluate the reserved portion explicitly:

```bash
python -m eval.run_model --all --split test
python -m eval.summarize --split test
```

Rebuilding the source dataset does not automatically replace frozen splits. If the source changes, create and document a new dataset/split version rather than overwriting the old one.

## Tests

```bash
python -m pytest -q
```

API tests are mocked and incur no API charges.

## Next milestone

Tighten scoring, separate development/holdout data, evaluate three baselines, then implement a rule-based router and compare quality, latency and estimated API cost. Gateway, caching, dashboard and Docker are later work.

## References

- https://developers.openai.com/api/docs/models/gpt-6-luna
- https://developers.openai.com/api/docs/models/gpt-6-sol
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/reference/python/resources/responses/methods/create
