# Format-only cascade — MMLU & GSM8K

Offline replay: routing checks completion status and answer format; it never reads reference correctness. Correctness is used only to evaluate the selected final answer.

Policy: `format-v1`. Split: `dev`. Pricing: `2026-10-22-standard-short-context-model-pages`.

| Strategy | Correct | Accuracy | Calls | Estimated USD | Mean request/simulated latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-luna | 116/120 | 96.67% | 120 | $0.006770 | 2.186 s |
| gpt-6-sol | 115/120 | 95.83% | 120 | $0.089088 | 2.493 s |
| gpt-6-astra | 119/120 | 99.17% | 120 | $0.444790 | 2.928 s |
| oracle-cascade | 120/120 | 100.00% | 127 | $0.042274 | 2.377 s |
| format-cascade | 119/120 | 99.17% | 126 | $0.040840 | 2.355 s |

## Escalated cases

| Question | Attempted models | Final format accepted | Final answer correct |
| --- | --- | --- | --- |
| gsm8k-060 | gpt-6-luna → gpt-6-sol → gpt-6-astra | True | True |
| gsm8k-070 | gpt-6-luna → gpt-6-sol → gpt-6-astra | True | True |
| gsm8k-087 | gpt-6-luna → gpt-6-sol → gpt-6-astra | True | True |

Accepted but wrong final answers: gsm8k-030.

## Interpretation and limits

- Luna is always first. Only incomplete or unparseable answers escalate. A well-formed wrong answer stops the chain.
- The policy receives only answer type, raw response and completion status. It does not see reference answers, correctness labels or benchmark subjects. Answer type is assumed to be part of the task contract.
- If Astra also fails format validation, the chain ends with accepted=false. Correctness still comes from the unchanged benchmark scorer.
- Oracle uses correctness to escalate and is a theoretical comparison, not a deployable alternative. Format-only replay uses signals available at runtime, but no live executor or API-error fallback has been implemented here.
- Every attempted call is included in cost and simulated sequential latency. Original prompts are reused, without passing previous model responses to later models. Verification overhead is not measured.
- Costs use the same dated Standard short-context pricing snapshot as oracle; cached input is discounted and reasoning is not double-counted. Estimates are not invoices. Actual baseline collection already paid for all three models.
- Strict-v2 format penalties, ambiguity and previous exposure of this dataset remain. This replay is not a held-out generalization result.
- No API requests are made and saved baseline results are unchanged.

## Reproduce

```bash
python -m eval.format_cascade --split dev
```

## Provenance

- `eval/data/dev.jsonl`: `a155064d9dc06821d424fb017b34692a3173da58d6e798ebfd513a8ab221ec05`
- `pricing snapshot`: `c09242d613323a85a2055c559325003f941e6322471e38436c16255248f68e52`
- `eval/results/dev/gpt-6-luna.jsonl`: `5bbd473d7ceea63e6973c946d6cd5d914410a46484f489b0e665188ef03fd77e`
- `eval/results/dev/gpt-6-sol.jsonl`: `c7bd858f077d21c15c86869af2508c6eb82189a8a067c22d28bf7ec003aa77c1`
- `eval/results/dev/gpt-6-astra.jsonl`: `06d35bd2076489313de84bcae4f32f512ca244052df241c79ee3a7bffe5484ee`

## Pricing sources

- [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [gpt-6-sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [gpt-6-astra](https://developers.openai.com/api/docs/models/gpt-6-astra)
