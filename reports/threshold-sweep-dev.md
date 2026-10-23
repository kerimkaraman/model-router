# Development sweep: selective Luna → Sol escalation

No API calls. Reuses the same saved choice probabilities, Luna/Sol answers and pricing.

Policy: use Sol only if choice=escalate AND P(escalate) >= threshold. P(escalate) = 1 - P(accept), not the separate confidence field. Equality is included.

| Strategy | Correct / 120 | Sol escalations | Repaired | Regressed | Estimated total USD | Mean recorded/simulated seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-6-luna | 116/120 | — | — | — | $0.006770 | 2.186 |
| gpt-6-sol | 115/120 | — | — | — | $0.089088 | 2.493 |
| Luna + Decisions choice → Sol | 115/120 | 17 | 1 | 2 | $0.026387 | 3.497 |
| Choice escalation probability >= 0.5 | 115/120 | 17 | 1 | 2 | $0.026387 | 3.497 |
| Choice escalation probability >= 0.6 | 117/120 | 11 | 1 | 0 | $0.021075 | 3.370 |
| Choice escalation probability >= 0.7 | 116/120 | 5 | 0 | 0 | $0.015649 | 2.510 |
| Choice escalation probability >= 0.8 | 116/120 | 4 | 0 | 0 | $0.015449 | 2.502 |
| Choice escalation probability >= 0.9 | 116/120 | 2 | 0 | 0 | $0.013715 | 2.470 |
| Choice escalation probability >= 0.95 | 116/120 | 0 | 0 | 0 | $0.011411 | 2.437 |
| Choice escalation probability >= 1.0 | 116/120 | 0 | 0 | 0 | $0.011411 | 2.437 |

## Comparison with using Luna alone

- Choice escalation probability >= 0.6: +1 correct; 3.11× Luna-only estimated cost.
- Choice escalation probability >= 0.7: +0 correct; 2.31× Luna-only estimated cost.
- Choice escalation probability >= 0.8: +0 correct; 2.28× Luna-only estimated cost.
- Choice escalation probability >= 0.9: +0 correct; 2.03× Luna-only estimated cost.
- Choice escalation probability >= 0.95: +0 correct; 1.69× Luna-only estimated cost.
- Choice escalation probability >= 1.0: +0 correct; 1.69× Luna-only estimated cost.

No tested cascade matches or improves Luna-only accuracy, cost and latency simultaneously. More accuracy may still be worth a higher cost, but requires an explicit preference.

## Limits

- Thresholds are explored on development data after seeing baseline results. Do not treat the best threshold as validated on unseen requests.
- Every cascade still pays for one Decisions judgment per question, even if the threshold causes no Sol escalations. The Luna-only baseline pays no judge overhead.
- A larger returned probability is not a calibrated correctness guarantee. The separate choice confidence is not used.
- Correctness is unchanged strict-v2: unit-format issues and ambiguous questions remain included. A one-case improvement is weak evidence, particularly on this small sample.
- All costs include attempted calls. Sequential durations are sums of recorded requests, not live end-to-end measurements. No extra generation, judging, Astra or test-split access occurs.
- Existing choice/predicate results and earlier reports are preserved. This module only writes threshold-sweep artifacts.

## Reproduce

```bash
python -m eval.threshold_sweep
```

## Input hashes

- `eval/data/dev.jsonl`: `a155064d9dc06821d424fb017b34692a3173da58d6e798ebfd513a8ab221ec05`
- `eval/results/dev/gpt-6-luna.jsonl`: `5bbd473d7ceea63e6973c946d6cd5d914410a46484f489b0e665188ef03fd77e`
- `eval/results/dev/gpt-6-sol.jsonl`: `c7bd858f077d21c15c86869af2508c6eb82189a8a067c22d28bf7ec003aa77c1`
- `eval/results/decisions/luna-dev-choice.jsonl`: `8c5e118794ce4779ae2587f18ff87f2e6ecdcdbb30b0849b408fb42e2107fa13`
- `eval/pricing.json`: `c09242d613323a85a2055c559325003f941e6322471e38436c16255248f68e52`
