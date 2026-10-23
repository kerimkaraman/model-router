# Fixed 0.60 policy — reserved evaluation split

The threshold and judge rubric were fixed before collecting these OpenAI evaluation outputs. No threshold sweep is performed here.

| Strategy | Correct | Accuracy | Generation calls | Decisions calls | Estimated USD | Mean recorded/simulated seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-6-luna | 75/80 | 93.75% | 80 | 0 | $0.004304 | 2.592 |
| gpt-6-sol | 76/80 | 95.00% | 80 | 0 | $0.059370 | 1.714 |
| Choice escalation probability >= 0.6 | 75/80 | 93.75% | 87 | 80 | $0.013869 | 3.060 |

Sol escalations: 7; repaired: 0; regressed: 0.

## Changed benchmark outcomes

| Case | Effect | Selected model |
| --- | --- | --- |

## Interpretation

- Every task pays for Luna generation and a Decisions choice judgment. Sol is used only if choice=escalate and P(escalate)>=0.60. There is no Astra or second judgment.
- Reference labels are used only to score selected outputs, not to make routing decisions. Strict-v2 benchmark labels remain unchanged.
- The original source pool had historical Gemma outputs before splitting: this reserved split is not a pristine unseen holdout. This is a fixed-policy evaluation on a previously exposed source pool.
- Baseline collection called both generation models for every question; the cascade figures are offline replay estimates, not actual invoice totals or live cascade timing. Judge cost/duration are included.
- Scorer format penalties, ambiguous benchmark questions, small sample size and same-family judge errors remain limitations. Do not adjust the threshold against these results.
- Policy: `choice-luna-sol-060-v1`. Pricing: `2026-10-22-standard-short-context-model-pages`.

## Reproduce

```bash
python -m eval.frozen_policy
```

## Input hashes

- `eval/data/test.jsonl`: `83479e9f8c0bf36663e42410143318bcbc55221fc356253047ab46efdb83e004`
- `eval/results/test/gpt-6-luna.jsonl`: `5ae289ff4a4728f8375099a955691475a225f96bd8003bb5ba43efd0c993a504`
- `eval/results/test/gpt-6-sol.jsonl`: `ed976a98a59e831990497f2729f3950e1fd13923136f7903d50ad6bde3cf2a72`
- `eval/results/decisions/luna-test-choice.jsonl`: `914e1ebc19ba7106b4c0427a72bc7b9ca6566fa222bc010f7314ead7152f6a32`
- `eval/pricing.json`: `c09242d613323a85a2055c559325003f941e6322471e38436c16255248f68e52`
- `eval/cascade_policy.json`: `16c0ec31f3558ff0963c49bc6e3d6c308991ea9a6d4f8e1154d604b5e2783d85`
