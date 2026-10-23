# Luna → Decisions choice → Sol

Offline replay of a single escalation. No new API calls. Astra is not used or read.

| Strategy | Correct | Accuracy | Generation calls | Decisions calls | Estimated USD | Mean recorded/simulated latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-6-luna | 116/120 | 96.67% | 120 | 0 | $0.006770 | 2.186 s |
| gpt-6-sol | 115/120 | 95.83% | 120 | 0 | $0.089088 | 2.493 s |
| Luna + Decisions choice → Sol | 115/120 | 95.83% | 137 | 120 | $0.026387 | 3.497 s |

Escalations: **17**. Repaired benchmark outcomes: **1**. Regressed outcomes: **2**.
Decisions cost is included in the total: $0.004640.

## All escalations

| Case | Luna correct | Sol final correct | Effect | Estimated case USD |
| --- | --- | --- | --- | ---: |
| gsm8k-030 | False | True | repaired | $0.001575 |
| mmlu-college_physics-002 | True | True | unchanged_correct | $0.000617 |
| gsm8k-052 | True | True | unchanged_correct | $0.001139 |
| mmlu-college_physics-020 | True | True | unchanged_correct | $0.000540 |
| mmlu-elementary_mathematics-010 | True | True | unchanged_correct | $0.000721 |
| gsm8k-018 | True | False | regressed | $0.001910 |
| mmlu-formal_logic-011 | True | True | unchanged_correct | $0.000878 |
| mmlu-elementary_mathematics-002 | True | True | unchanged_correct | $0.000389 |
| mmlu-high_school_geography-014 | True | False | regressed | $0.000764 |
| gsm8k-001 | True | True | unchanged_correct | $0.001867 |
| gsm8k-062 | True | True | unchanged_correct | $0.000863 |
| gsm8k-066 | True | True | unchanged_correct | $0.001278 |
| mmlu-elementary_mathematics-006 | True | True | unchanged_correct | $0.000254 |
| gsm8k-070 | False | False | unchanged_unsuccessful | $0.001859 |
| mmlu-elementary_mathematics-009 | True | True | unchanged_correct | $0.000543 |
| gsm8k-078 | True | True | unchanged_correct | $0.001414 |
| mmlu-college_physics-023 | True | True | unchanged_correct | $0.000259 |

## Final unsuccessful cases

- `gsm8k-060`: selected `gpt-6-luna`; unchanged_unsuccessful.
- `gsm8k-018`: selected `gpt-6-sol`; regressed.
- `mmlu-high_school_geography-014`: selected `gpt-6-sol`; regressed.
- `gsm8k-070`: selected `gpt-6-sol`; unchanged_unsuccessful.
- `gsm8k-087`: selected `gpt-6-luna`; unchanged_unsuccessful.

## Meaning of the result

- Every task first incurs Luna generation plus one saved Decisions request. Accept retains Luna; escalate uses Sol once and stops, regardless of Sol's correctness. There is no second judge or Astra fallback.
- Selection uses only the saved accept/escalate choice. Correctness labels are consulted after selection for evaluation, not to choose the final model.
- A stronger model is not guaranteed to repair a rejected answer. The report counts both repairs and regressions explicitly.
- Correctness retains strict-v2 benchmark scoring, including unit-format penalties and ambiguous cases. It is not a fresh adjudication of substantive truth.
- This is development-set replay, not live or held-out performance. Durations sum standalone recorded Luna, judge and optionally Sol calls. Network/cache conditions and executor overhead may differ live.
- Costs include all attempted generation and judging. Generation uses the dated short-context Standard pricing snapshot; Decisions uses the documented $0.10/1M input-token estimate from its saved experiment. These are scenario estimates, not invoices, and exclude regional/long-context adjustments.
- Generation pricing snapshot: `2026-10-22-standard-short-context-model-pages`. Decisions policy: `answer-review-v1`, choice mode, no confidence threshold.
- Inputs, original judgments and baseline scores are preserved. Predicate, format and oracle results are not modified. Test split is not read.

## Reproduce

```bash
python -m eval.choice_cascade
```

## Input hashes

- `eval/data/dev.jsonl`: `a155064d9dc06821d424fb017b34692a3173da58d6e798ebfd513a8ab221ec05`
- `eval/results/dev/gpt-6-luna.jsonl`: `5bbd473d7ceea63e6973c946d6cd5d914410a46484f489b0e665188ef03fd77e`
- `eval/results/dev/gpt-6-sol.jsonl`: `c7bd858f077d21c15c86869af2508c6eb82189a8a067c22d28bf7ec003aa77c1`
- `eval/results/decisions/luna-dev-choice.jsonl`: `8c5e118794ce4779ae2587f18ff87f2e6ecdcdbb30b0849b408fb42e2107fa13`
- `eval/pricing.json`: `c09242d613323a85a2055c559325003f941e6322471e38436c16255248f68e52`
