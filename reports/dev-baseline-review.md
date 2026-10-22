# Development baseline review

Reviewed on 2026-10-22. No new API calls were made. Original outputs, references and saved `strict-v2` scores are unchanged.

## Completeness

All three models have 120 unique development results, covering the same question IDs. No responses are incomplete. These are development results, not held-out generalization estimates.

| Model | Strict-v2 correct | Accuracy | Mean request latency | Unparseable |
| --- | ---: | ---: | ---: | ---: |
| GPT-6 Luna | 116/120 | 96.7% | 2.19 s | 3 |
| GPT-6 Sol | 115/120 | 95.8% | 2.49 s | 3 |
| GPT-6 Astra | 119/120 | 99.2% | 2.93 s | 0 |

Raw records: `eval/results/dev/`. This report does not recalculate cost or claim routing savings.

## Findings from unsuccessful cases

### gsm8k-060 — correct numeric content, extra percentage suffix

The question asks what percentage the combined remora lengths are of the shark's length. The reference is `10`. Luna and Sol both produce `#### 10%`; both correctly compute 12/120 × 100.

- Strict protocol: unparseable, since the prompt requests a final number only.
- Content review: the numeric answer and percentage interpretation agree with the reference.
- Potential future policy: accept a percentage suffix only when the question explicitly expects a percentage. Preserve 10 percentage points here; do not silently convert to 0.1.

### gsm8k-070 — correct numeric content, extra unit suffix

The reference is `525`. Luna and Sol calculate a 105,000-calorie deficit over 200 days and finish with `#### 525 calories per day`.

- Strict protocol: unparseable because the final line includes units.
- Content review: both answers agree with the reference under the non-leap-year convention used in their solutions.
- Potential future policy: validate expected units as well as the numeric value, using an explicit question schema or rubric. Do not remove arbitrary trailing text from any answer.

### gsm8k-087 — missing information in the question

The prompt lists a towing package as an extra-cost feature but supplies no price for it. The listed, priced features sum to $43,500, which is the benchmark reference. Luna and Sol point out that the total including the towing package cannot be determined.

- Luna gives `#### $43,500 + towing package cost`.
- Sol explains the missing price without giving an unconditional final number.
- Both are unparseable under the current protocol.
- Their objection is supported by the question text. Do not relabel this as a proven reasoning failure or change the reference solely to favor a model.
- Retain the case in published benchmark counts; annotate it for review. Any exclusion should be reported separately with a changed denominator and versioned dataset policy.

### gsm8k-030 — ambiguous amount of food per feeding

The prompt says Imma has three cats and feeds her cats twice a day with 60 grams of food. The reference is `2` days, consistent with interpreting 60 grams as the amount for each cat at each feeding: 3 × 2 × 60 = 360 grams/day.

Luna interprets 60 grams as the total amount for all cats at each feeding and returns `6`: 2 × 60 = 120 grams/day.

- Benchmark scoring: incorrect against reference `2`.
- Content review: the alternative interpretation is plausible because the wording does not explicitly say “per cat.”
- Keep the reference score, annotate the ambiguity, and avoid attributing the disagreement exclusively to model capability.

### gsm8k-018 — mask-use interpretation

The prompt says Tyrion changes his mask twice each time he goes out, three outings per day for two days. Reference: `12`. Sol counts an initial mask plus two changes per outing and returns `18`.

- Benchmark scoring: incorrect.
- The response uses a different accounting convention: initial mask plus replacement masks.
- A clearer application-owned case would specify whether to count replacements only or every mask used. Preserve the benchmark result and flag the wording issue rather than deciding the model is definitively correct.

### mmlu-high_school_geography-014 — disagreement with reference

The question asks which factor does not play a role in gender relationships: biology, technological development, religion or custom. Reference: `A`. Luna answers A; Sol and Astra answer B.

- Benchmark scoring: Sol and Astra are incorrect.
- Their one-letter responses do not explain the reasoning. This review does not establish that the benchmark reference is wrong.
- A subject-matter review would be needed to challenge the key. Do not use model majority voting to replace it.

## Sensitivity to the scoring protocol

If only the two identified unit-suffix cases were accepted as content-correct, with every other label and the 120-case denominator retained:

| Model | Strict-v2 | Unit-normalized sensitivity analysis |
| --- | ---: | ---: |
| Luna | 116/120 (96.7%) | 118/120 (98.3%) |
| Sol | 115/120 (95.8%) | 117/120 (97.5%) |
| Astra | 119/120 (99.2%) | 119/120 (99.2%) |

This is a post-hoc manual sensitivity analysis, **not a new official scorer result**. The cases were inspected after seeing model outputs. It demonstrates how much of the measured difference is related to output-format policy. The raw results have not been overwritten, and the ambiguous cases remain in both counts.

## Implications for the router

- Four categories are nearly saturated: Luna answers all 60 multiple-choice questions correctly in this development run. Most differentiation comes from math word problems, output formatting and a few wording disputes.
- Sol's aggregate result does not improve on Luna here. That is a property of this sample and configuration, not a general ranking of the models.
- Do not derive a confident “hard question” classifier from a handful of disagreements.
- The existing experiment remains useful for validating evaluation plumbing and comparing benchmark performance. It does not establish a general-purpose routing policy for greetings, summarization, extraction and coding requests.
- Expand the development dataset with representative tasks before developing a general-purpose router. Use task-specific rubrics rather than requiring a single reference string for every task.

## Next steps

1. Choose and document the output contract: strict format compliance, numeric content with validated units, or both as separate metrics.
2. If changing the scorer, version the policy, add positive and negative unit tests and re-score **all** development outputs offline into a separate result directory. Preserve strict-v2 alongside it.
3. Keep ambiguity annotations separate from correctness labels. Report any curated subset explicitly; do not silently remove inconvenient cases.
4. Add representative development examples for general-purpose routing, with clear evaluation criteria.
5. Develop a simple policy using only information available before model execution. Reserve evaluation data for later and obtain fresh unseen questions for final claims.

No holdout results were inspected for this report. No code or dataset labels were modified.
