# Decisions review of saved Luna answers

Evaluated **80/80 test answers**. Policy `answer-review-v1`, mode `choice`. Decision rule: returned accept/escalate choice (no threshold).

Yes = accept; No = send to a stronger model. Refusal is unknown, not No.

| Decision | Benchmark correct | Benchmark unsuccessful |
| --- | ---: | ---: |
| Yes / accept | 66 | 4 |
| No / escalate | 9 | 1 |

Refusals: 0. Input tokens: 30975. Estimated Decisions cost: $0.003098.
Mean Decisions request duration: 0.327 s.

## Cases requiring review

| Case | Decisions | Accept probability | Benchmark outcome |
| --- | --- | ---: | --- |
| mmlu-college_physics-024 | no | 0.2000 | correct |
| gsm8k-005 | no | 0.3500 | correct |
| mmlu-formal_logic-006 | no | 0.3300 | correct |
| mmlu-high_school_geography-004 | yes | 0.5900 | incorrect |
| gsm8k-071 | yes | 0.9000 | incorrect |
| gsm8k-035 | no | 0.2300 | correct |
| mmlu-formal_logic-024 | no | 0.2000 | correct |
| gsm8k-027 | no | 0.4300 | unparseable |
| gsm8k-024 | yes | 0.7400 | incorrect |
| gsm8k-064 | no | 0.5000 | correct |
| gsm8k-090 | yes | 1.0000 | unparseable |
| mmlu-formal_logic-005 | no | 0.1200 | correct |
| mmlu-college_physics-008 | no | 0.0700 | correct |
| gsm8k-000 | no | 0.4600 | correct |

## Interpretation

- Only task text and saved candidate answer were sent. No reference answer, correctness label, score status, model identity or benchmark subject was included in the evaluation input.
- The benchmark comparison happens after the decision. Correctness here means strict-v2 protocol success; unsuccessful cases include valid numeric content with unit suffixes and ambiguous questions. Benchmark-unsuccessful cases are not necessarily proven substantive errors.
- The judge rubric accepts harmless units and justified missing-information objections. A disagreement with strict-v2 is not automatically a judge mistake; inspect the existing development review.
- Predicate uses a fixed 0.5 threshold; choice uses the returned category, without a confidence threshold. Probabilities and confidence are not correctness guarantees. Luna judging Luna can reproduce the same mistakes.
- There are very few benchmark-unsuccessful cases. Do not generalize failure-detection quality from this small sample.
- This measures the judge only. No Sol/Astra calls or live cascade were made. Judge cost and duration would be additional overhead in a live cascade.
- Pricing estimate uses $0.10 per 1M Decisions input tokens, no output/cache charges, excluding regional or long-context adjustments. Successful judgments only; an interrupted request might incur usage without a saved record.
- [Official Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [API reference](https://developers.openai.com/api/reference/python/resources/decisions/methods/create)
