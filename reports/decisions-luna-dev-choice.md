# Decisions review of saved Luna answers

Evaluated **120/120 development answers**. Policy `answer-review-v1`, mode `choice`. Decision rule: returned accept/escalate choice (no threshold).

Yes = accept; No = send to a stronger model. Refusal is unknown, not No.

| Decision | Benchmark correct | Benchmark unsuccessful |
| --- | ---: | ---: |
| Yes / accept | 101 | 2 |
| No / escalate | 15 | 2 |

Refusals: 0. Input tokens: 46403. Estimated Decisions cost: $0.004640.
Mean Decisions request duration: 0.252 s.

## Cases requiring review

| Case | Decisions | Accept probability | Benchmark outcome |
| --- | --- | ---: | --- |
| gsm8k-030 | no | 0.3400 | incorrect |
| mmlu-college_physics-002 | no | 0.3500 | correct |
| gsm8k-052 | no | 0.4000 | correct |
| mmlu-college_physics-020 | no | 0.3100 | correct |
| mmlu-elementary_mathematics-010 | no | 0.0700 | correct |
| gsm8k-060 | yes | 1.0000 | unparseable |
| gsm8k-018 | no | 0.4900 | correct |
| mmlu-formal_logic-011 | no | 0.4300 | correct |
| mmlu-elementary_mathematics-002 | no | 0.3100 | correct |
| mmlu-high_school_geography-014 | no | 0.5000 | correct |
| gsm8k-001 | no | 0.3700 | correct |
| gsm8k-062 | no | 0.4800 | correct |
| gsm8k-066 | no | 0.4700 | correct |
| mmlu-elementary_mathematics-006 | no | 0.2900 | correct |
| gsm8k-070 | no | 0.0900 | unparseable |
| mmlu-elementary_mathematics-009 | no | 0.2000 | correct |
| gsm8k-078 | no | 0.1900 | correct |
| mmlu-college_physics-023 | no | 0.4200 | correct |
| gsm8k-087 | yes | 0.8900 | unparseable |

## Interpretation

- Only task text and saved candidate answer were sent. No reference answer, correctness label, score status, model identity or benchmark subject was included in the evaluation input.
- The benchmark comparison happens after the decision. Correctness here means strict-v2 protocol success; unsuccessful cases include valid numeric content with unit suffixes and ambiguous questions. These are not four proven substantive errors.
- The judge rubric accepts harmless units and justified missing-information objections. A disagreement with strict-v2 is not automatically a judge mistake; inspect the existing development review.
- Predicate uses a fixed 0.5 threshold; choice uses the returned category, without a confidence threshold. Probabilities and confidence are not correctness guarantees. Luna judging Luna can reproduce the same mistakes.
- There are very few benchmark-unsuccessful cases. Do not generalize failure-detection quality from this small development sample.
- This measures the judge only. No Sol/Astra calls or live cascade were made. Judge cost and duration would be additional overhead in a live cascade.
- Pricing estimate uses $0.10 per 1M Decisions input tokens, no output/cache charges, excluding regional or long-context adjustments. Successful judgments only; an interrupted request might incur usage without a saved record.
- [Official Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [API reference](https://developers.openai.com/api/reference/python/resources/decisions/methods/create)
