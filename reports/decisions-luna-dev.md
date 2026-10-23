# Decisions review of saved Luna answers

Evaluated **120/120 development answers**. Policy `answer-review-v1`, fixed threshold `0.5`.

Yes = accept; No = send to a stronger model. Refusal is unknown, not No.

| Decision | Benchmark correct | Benchmark unsuccessful |
| --- | ---: | ---: |
| Yes / accept | 100 | 2 |
| No / escalate | 16 | 2 |

Refusals: 0. Input tokens: 48923. Estimated Decisions cost: $0.004892.
Mean Decisions request duration: 0.372 s.

## Cases requiring review

| Case | Decisions | Accept probability | Benchmark outcome |
| --- | --- | ---: | --- |
| mmlu-formal_logic-012 | no | 0.1800 | correct |
| gsm8k-030 | no | 0.2900 | incorrect |
| mmlu-college_physics-002 | no | 0.4500 | correct |
| gsm8k-052 | no | 0.4100 | correct |
| mmlu-formal_logic-018 | no | 0.1300 | correct |
| mmlu-elementary_mathematics-000 | no | 0.0400 | correct |
| mmlu-elementary_mathematics-010 | no | 0.0300 | correct |
| gsm8k-060 | yes | 1.0000 | unparseable |
| mmlu-formal_logic-011 | no | 0.0600 | correct |
| mmlu-formal_logic-002 | no | 0.2700 | correct |
| mmlu-elementary_mathematics-002 | no | 0.0000 | correct |
| mmlu-elementary_mathematics-023 | no | 0.3500 | correct |
| mmlu-high_school_geography-014 | no | 0.1700 | correct |
| mmlu-elementary_mathematics-006 | no | 0.3400 | correct |
| gsm8k-070 | no | 0.4900 | unparseable |
| mmlu-elementary_mathematics-009 | no | 0.0400 | correct |
| gsm8k-078 | no | 0.2100 | correct |
| mmlu-college_physics-023 | no | 0.0200 | correct |
| mmlu-elementary_mathematics-001 | no | 0.4300 | correct |
| gsm8k-087 | yes | 0.9700 | unparseable |

## Interpretation

- Only task text and saved candidate answer were sent. No reference answer, correctness label, score status, model identity or benchmark subject was included in the evaluation input.
- The benchmark comparison happens after the decision. Correctness here means strict-v2 protocol success; unsuccessful cases include valid numeric content with unit suffixes and ambiguous questions. These are not four proven substantive errors.
- The judge rubric accepts harmless units and justified missing-information objections. A disagreement with strict-v2 is not automatically a judge mistake; inspect the existing development review.
- The threshold was fixed before observing these decisions; probabilities are estimates, not calibrated guarantees. Luna judging Luna can reproduce the same mistakes.
- There are very few benchmark-unsuccessful cases. Do not generalize failure-detection quality from this small development sample.
- This measures the judge only. No Sol/Astra calls or live cascade were made. Judge cost and duration would be additional overhead in a live cascade.
- Pricing estimate uses $0.10 per 1M Decisions input tokens, no output/cache charges, excluding regional or long-context adjustments. Successful judgments only; an interrupted request might incur usage without a saved record.
- [Official Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [API reference](https://developers.openai.com/api/reference/python/resources/decisions/methods/create)
