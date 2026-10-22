"""Offline replay using response completion and format only for escalation."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from eval.oracle_cascade import MODELS, PRICING_PATH, ROOT, Rate, simulate
from eval.question import AnswerType
from eval.run_model import QuestionResult, load_questions
from eval.scoring import extract_choice_letter, extract_final_number

POLICY_VERSION = "format-v1"


def accept_format(answer_type: AnswerType, answer: str, response_status: str) -> bool:
    # No expected answer, correctness label or subject is accessible here.
    if response_status != "completed":
        return False
    if answer_type == AnswerType.MULTIPLE_CHOICE:
        return extract_choice_letter(answer) is not None
    if answer_type == AnswerType.NUMBER:
        return extract_final_number(answer) is not None
    raise ValueError("Unsupported answer type")


def format_simulation(runs, rates, answer_types):
    expected_ids = {row.question_id for row in runs[MODELS[0]]}
    if set(answer_types) != expected_ids:
        raise ValueError("Answer types must match the evaluated question IDs")
    return simulate(runs, rates,
        accept_answer=lambda qid, answer, status: accept_format(answer_types[qid], answer, status),
        strategy="format-cascade")


def build_report(summaries, traces, pricing, split, provenance):
    lines = ["# Format-only cascade — MMLU & GSM8K", "",
        "Offline replay: routing checks completion status and answer format; it never reads reference correctness. Correctness is used only to evaluate the selected final answer.", "",
        f"Policy: `{POLICY_VERSION}`. Split: `{split}`. Pricing: `{pricing['version']}`.", "",
        "| Strategy | Correct | Accuracy | Calls | Estimated USD | Mean request/simulated latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for s in summaries:
        lines.append(f"| {s['strategy']} | {s['correct_count']}/{s['question_count']} | "
            f"{100*s['correct_count']/s['question_count']:.2f}% | {s['calls']} | "
            f"${Decimal(s['estimated_cost_usd']):.6f} | {s['average_latency_seconds']:.3f} s |")
    lines += ["", "## Escalated cases", "",
        "| Question | Attempted models | Final format accepted | Final answer correct |",
        "| --- | --- | --- | --- |"]
    for t in traces:
        if len(t['attempted_models']) > 1:
            lines.append(f"| {t['question_id']} | {' → '.join(t['attempted_models'])} | {t['accepted']} | {t['is_correct']} |")
    missed = [t['question_id'] for t in traces if t['accepted'] and not t['is_correct']]
    lines += ["", f"Accepted but wrong final answers: {', '.join(missed) if missed else 'none'}.", "",
        "## Interpretation and limits", "",
        "- Luna is always first. Only incomplete or unparseable answers escalate. A well-formed wrong answer stops the chain.",
        "- The policy receives only answer type, raw response and completion status. It does not see reference answers, correctness labels or benchmark subjects. Answer type is assumed to be part of the task contract.",
        "- If Astra also fails format validation, the chain ends with accepted=false. Correctness still comes from the unchanged benchmark scorer.",
        "- Oracle uses correctness to escalate and is a theoretical comparison, not a deployable alternative. Format-only replay uses signals available at runtime, but no live executor or API-error fallback has been implemented here.",
        "- Every attempted call is included in cost and simulated sequential latency. Original prompts are reused, without passing previous model responses to later models. Verification overhead is not measured.",
        "- Costs use the same dated Standard short-context pricing snapshot as oracle; cached input is discounted and reasoning is not double-counted. Estimates are not invoices. Actual baseline collection already paid for all three models.",
        "- Strict-v2 format penalties, ambiguity and previous exposure of this dataset remain. This replay is not a held-out generalization result.",
        "- No API requests are made and saved baseline results are unchanged.", "",
        "## Reproduce", "", "```bash", f"python -m eval.format_cascade --split {split}", "```", "",
        "## Provenance", ""]
    lines += [f"- `{name}`: `{digest}`" for name, digest in provenance.items()]
    lines += ["", "## Pricing sources", ""]
    lines += [f"- [{m}]({pricing['models'][m]['source']})" for m in MODELS]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('dev', 'test'), default='dev')
    parser.add_argument('--pricing', type=Path, default=PRICING_PATH)
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    dataset = ROOT / 'eval' / 'data' / f'{args.split}.jsonl'
    questions = load_questions(dataset)
    answer_types = {q.question_id: q.answer_type for q in questions}
    if len(answer_types) != len(questions):
        raise ValueError('Duplicate dataset IDs')
    dataset_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    pricing_raw = args.pricing.read_bytes()
    pricing = json.loads(pricing_raw)
    rates = {m: Rate(*(Decimal(pricing['models'][m][key]) for key in ('input', 'cached_input', 'output'))) for m in MODELS}
    if any(v < 0 for rate in rates.values() for v in (rate.input, rate.cached_input, rate.output)):
        raise ValueError('Negative pricing')
    provenance = {str(dataset.relative_to(ROOT)): dataset_hash,
        'pricing snapshot': hashlib.sha256(pricing_raw).hexdigest()}
    runs = {}
    for model in MODELS:
        path = ROOT / 'eval' / 'results' / args.split / f'{model}.jsonl'
        raw = path.read_bytes()
        rows = [QuestionResult.model_validate_json(line) for line in raw.decode().splitlines() if line.strip()]
        if {row.question_id for row in rows} != set(answer_types):
            raise ValueError(f'{model}: full selected split required')
        if any(row.dataset_split != args.split or row.dataset_sha256 != dataset_hash for row in rows):
            raise ValueError(f'{model}: dataset hash/split mismatch')
        runs[model] = rows
        provenance[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    baseline_and_oracle, _ = simulate(runs, rates)
    format_summaries, traces = format_simulation(runs, rates, answer_types)
    summaries = baseline_and_oracle + [format_summaries[-1]]
    report = build_report(summaries, traces, pricing, args.split, provenance)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = args.report_dir / f'format-cascade-{args.split}'
    stem.with_suffix('.md').write_text(report)
    stem.with_suffix('.json').write_text(json.dumps({'policy': POLICY_VERSION,
        'offline_replay': True, 'split': args.split, 'pricing': pricing,
        'provenance': provenance, 'summaries': summaries}, indent=2) + '\n')
    stem.with_suffix('.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in traces))
    print(report.split('## Escalated cases')[0])
    print(f'Report: {stem}.md')


if __name__ == '__main__':
    main()
