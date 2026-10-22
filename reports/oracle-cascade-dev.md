# Oracle cascade — MMLU & GSM8K

**Offline theoretical reference: escalation uses saved reference-based correctness. This cannot operate on new questions without an actual failure detector.**

Split: `dev`. Pricing snapshot: `2026-10-22-standard-short-context-model-pages`. Scoring remains unchanged.

| Strategy | Correct | Accuracy | Calls | Estimated USD | Mean request/simulated latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-luna | 116/120 | 96.67% | 120 | $0.006770 | 2.186 s |
| gpt-6-sol | 115/120 | 95.83% | 120 | $0.089088 | 2.493 s |
| gpt-6-astra | 119/120 | 99.17% | 120 | $0.444790 | 2.928 s |
| oracle-cascade | 120/120 | 100.00% | 127 | $0.042274 | 2.377 s |

Estimated cost reduction versus always-Astra: **90.50%** (negative means more expensive).

## Escalated cases

| Question | Calls attempted | Final result | Estimated USD |
| --- | --- | --- | ---: |
| gsm8k-030 | gpt-6-luna → gpt-6-sol | correct | $0.001538 |
| gsm8k-060 | gpt-6-luna → gpt-6-sol → gpt-6-astra | correct | $0.005626 |
| gsm8k-070 | gpt-6-luna → gpt-6-sol → gpt-6-astra | correct | $0.012474 |
| gsm8k-087 | gpt-6-luna → gpt-6-sol → gpt-6-astra | correct | $0.016329 |

## Assumptions and limits

- Every question starts at Luna; each unsuccessful attempt is paid before escalation. The first reference-correct answer stops the chain; if none succeeds, the final answer is unsuccessful.
- Incorrect, unparseable and incomplete saved responses all trigger oracle escalation. There are no simulated request-error records because the current runner does not save those failures.
- Input and output are repriced using the explicit Standard short-context snapshot below. Cached input is charged separately; reasoning tokens are already included in output tokens. No tools, explicit cache writes, regional premiums or negotiated prices are modeled.
- These are hypothetical strategy costs, not refunds or actual invoice amounts. The baseline collection already called every model on every case.
- Cascade latency sums independently recorded request times for attempted models. It is not a live cascade measurement, and excludes any real verifier/router overhead. Later attempts reuse the original prompt without earlier answers.
- Oracle correctness is an optimistic reference for this fixed cascade and saved outputs, not a guaranteed or globally optimal cost/latency policy. A real verifier can miss wrong answers or reject correct ones.
- Strict-v2 format penalties and ambiguous benchmark cases remain included. See `dev-baseline-review.md` for the development-set review.
- This source pool was evaluated before splitting; it is not a pristine holdout. No new API calls are made by this command.

## Reproduction

```bash
python -m eval.oracle_cascade --split dev
```

## Input provenance

- `eval/data/dev.jsonl` SHA-256: `a155064d9dc06821d424fb017b34692a3173da58d6e798ebfd513a8ab221ec05`
- `pricing snapshot` SHA-256: `c09242d613323a85a2055c559325003f941e6322471e38436c16255248f68e52`
- `eval/results/dev/gpt-6-luna.jsonl` SHA-256: `5bbd473d7ceea63e6973c946d6cd5d914410a46484f489b0e665188ef03fd77e`
- `eval/results/dev/gpt-6-sol.jsonl` SHA-256: `c7bd858f077d21c15c86869af2508c6eb82189a8a067c22d28bf7ec003aa77c1`
- `eval/results/dev/gpt-6-astra.jsonl` SHA-256: `06d35bd2076489313de84bcae4f32f512ca244052df241c79ee3a7bffe5484ee`

## Pricing sources

- [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna): per 1M tokens, input $0.10, cached input $0.01, output $0.50.
- [gpt-6-sol](https://developers.openai.com/api/docs/models/gpt-6-sol): per 1M tokens, input $2.00, cached input $0.20, output $10.00.
- [gpt-6-astra](https://developers.openai.com/api/docs/models/gpt-6-astra): per 1M tokens, input $10.00, cached input $1.00, output $50.00.
