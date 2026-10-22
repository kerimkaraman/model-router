"""Offline, reference-aware cascade simulation. Never a deployable routing policy."""
import argparse
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from eval.run_model import QuestionResult, load_questions

ROOT = Path(__file__).resolve().parents[1]
MODELS = ("gpt-6-luna", "gpt-6-sol", "gpt-6-astra")
PRICING_PATH = ROOT / "eval" / "pricing.json"


@dataclass(frozen=True)
class Rate:
    input: Decimal
    cached_input: Decimal
    output: Decimal


def estimate_cost(row: QuestionResult, rate: Rate) -> Decimal:
    counts = (row.input_tokens, row.output_tokens, row.cached_input_tokens, row.reasoning_tokens)
    if any(n < 0 for n in counts) or row.cached_input_tokens > row.input_tokens:
        raise ValueError("Invalid token counts")
    if row.reasoning_tokens > row.output_tokens:
        raise ValueError("Reasoning tokens must be a subset of output tokens")
    if row.input_tokens > 272_000:
        raise ValueError("Pricing snapshot supports short-context requests only")
    return ((row.input_tokens - row.cached_input_tokens) * rate.input
            + row.cached_input_tokens * rate.cached_input
            + row.output_tokens * rate.output) / Decimal(1_000_000)


def validate_runs(runs: dict[str, list[QuestionResult]]) -> None:
    if set(runs) != set(MODELS):
        raise ValueError("All three selected model runs are required")
    expected_ids = None
    expected_metadata = None
    for model in MODELS:
        rows = runs[model]
        ids = [r.question_id for r in rows]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Runs must be nonempty with unique question IDs")
        metadata = {(r.dataset_split, r.dataset_sha256, r.scorer_version,
                     r.reasoning_effort, r.max_output_tokens) for r in rows}
        if len(metadata) != 1:
            raise ValueError("Mixed run settings or dataset metadata")
        split, digest, scorer, effort, budget = next(iter(metadata))
        if not digest or scorer == "legacy" or effort is None or budget is None:
            raise ValueError("Versioned dataset, scoring and generation settings required")
        if split not in ("dev", "test"):
            raise ValueError("Legacy runs are not supported")
        for row in rows:
            if row.model_name != model:
                raise ValueError("Result model does not match its file")
            if row.score_status not in ("correct", "incorrect", "unparseable", "incomplete"):
                raise ValueError("Unknown scoring status")
            success = row.response_status == "completed" and row.score_status == "correct"
            if row.is_correct != success:
                raise ValueError("Inconsistent correctness/status fields")
            if row.latency_seconds < 0:
                raise ValueError("Invalid latency")
        if expected_ids is not None and (set(ids) != expected_ids or metadata != expected_metadata):
            raise ValueError("Runs require matching questions, dataset, scorer and generation settings")
        expected_ids, expected_metadata = set(ids), metadata


def simulate(runs: dict[str, list[QuestionResult]], rates: dict[str, Rate],
             accept_answer=None, strategy: str = "oracle-cascade"):
    validate_runs(runs)
    by_model = {m: {r.question_id: r for r in runs[m]} for m in MODELS}
    # Validate all pricing inputs, including rows not reached by the cascade.
    costs = {m: {qid: estimate_cost(row, rates[m]) for qid, row in by_model[m].items()} for m in MODELS}
    traces = []
    calls = {m: 0 for m in MODELS}
    for first in runs[MODELS[0]]:
        qid = first.question_id
        attempted, elapsed, cost = [], 0.0, Decimal(0)
        for model in MODELS:
            row = by_model[model][qid]
            attempted.append(model)
            calls[model] += 1
            elapsed += row.latency_seconds
            cost += costs[model][qid]
            accepted = (row.is_correct if accept_answer is None else
                        accept_answer(row.question_id, row.model_answer, row.response_status))
            if accepted:
                break
        traces.append({"question_id": qid, "attempted_models": attempted,
                       "final_model": model, "is_correct": row.is_correct,
                       "accepted": accepted,
                       "simulated_latency_seconds": elapsed, "estimated_cost_usd": str(cost)})
    summaries = []
    for model in MODELS:
        rows = runs[model]
        summaries.append({"strategy": model, "correct_count": sum(r.is_correct for r in rows),
            "question_count": len(rows), "calls": len(rows),
            "average_latency_seconds": sum(r.latency_seconds for r in rows) / len(rows),
            "estimated_cost_usd": str(sum(costs[model].values(), Decimal(0)))})
    summaries.append({"strategy": strategy, "correct_count": sum(t["is_correct"] for t in traces),
        "question_count": len(traces), "calls": sum(calls.values()), "calls_by_model": calls,
        "average_latency_seconds": sum(t["simulated_latency_seconds"] for t in traces) / len(traces),
        "estimated_cost_usd": str(sum((Decimal(t["estimated_cost_usd"]) for t in traces), Decimal(0)))})
    return summaries, traces


def markdown_report(summaries, traces, pricing, split, provenance):
    lines = ["# Oracle cascade — MMLU & GSM8K", "",
        "**Offline theoretical reference: escalation uses saved reference-based correctness. This cannot operate on new questions without an actual failure detector.**", "",
        f"Split: `{split}`. Pricing snapshot: `{pricing['version']}`. Scoring remains unchanged.", "",
        "| Strategy | Correct | Accuracy | Calls | Estimated USD | Mean request/simulated latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for s in summaries:
        lines.append(f"| {s['strategy']} | {s['correct_count']}/{s['question_count']} | "
            f"{100*s['correct_count']/s['question_count']:.2f}% | {s['calls']} | "
            f"${Decimal(s['estimated_cost_usd']):.6f} | {s['average_latency_seconds']:.3f} s |")
    cascade = summaries[-1]
    astra_cost = Decimal(summaries[2]['estimated_cost_usd'])
    if astra_cost:
        savings = 100 * (1 - Decimal(cascade['estimated_cost_usd']) / astra_cost)
        lines += ["", f"Estimated cost reduction versus always-Astra: **{savings:.2f}%** (negative means more expensive)."]
    lines += ["", "## Escalated cases", "",
        "| Question | Calls attempted | Final result | Estimated USD |",
        "| --- | --- | --- | ---: |"]
    for t in traces:
        if len(t['attempted_models']) > 1:
            lines.append(f"| {t['question_id']} | {' → '.join(t['attempted_models'])} | "
                f"{'correct' if t['is_correct'] else 'unsuccessful'} | ${Decimal(t['estimated_cost_usd']):.6f} |")
    lines += ["", "## Assumptions and limits", "",
        "- Every question starts at Luna; each unsuccessful attempt is paid before escalation. The first reference-correct answer stops the chain; if none succeeds, the final answer is unsuccessful.",
        "- Incorrect, unparseable and incomplete saved responses all trigger oracle escalation. There are no simulated request-error records because the current runner does not save those failures.",
        "- Input and output are repriced using the explicit Standard short-context snapshot below. Cached input is charged separately; reasoning tokens are already included in output tokens. No tools, explicit cache writes, regional premiums or negotiated prices are modeled.",
        "- These are hypothetical strategy costs, not refunds or actual invoice amounts. The baseline collection already called every model on every case.",
        "- Cascade latency sums independently recorded request times for attempted models. It is not a live cascade measurement, and excludes any real verifier/router overhead. Later attempts reuse the original prompt without earlier answers.",
        "- Oracle correctness is an optimistic reference for this fixed cascade and saved outputs, not a guaranteed or globally optimal cost/latency policy. A real verifier can miss wrong answers or reject correct ones.",
        "- Strict-v2 format penalties and ambiguous benchmark cases remain included. See `dev-baseline-review.md` for the development-set review.",
        "- This source pool was evaluated before splitting; it is not a pristine holdout. No new API calls are made by this command.",
        "", "## Reproduction", "", "```bash", f"python -m eval.oracle_cascade --split {split}", "```", "",
        "## Input provenance", ""]
    for path, digest in provenance.items():
        lines.append(f"- `{path}` SHA-256: `{digest}`")
    lines += ["", "## Pricing sources", ""]
    for model, entry in pricing['models'].items():
        lines.append(f"- [{model}]({entry['source']}): per 1M tokens, input ${entry['input']}, cached input ${entry['cached_input']}, output ${entry['output']}.")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('dev', 'test'), default='dev')
    parser.add_argument('--pricing', type=Path, default=PRICING_PATH)
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    dataset = ROOT / 'eval' / 'data' / f'{args.split}.jsonl'
    expected_ids = {q.question_id for q in load_questions(dataset)}
    dataset_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    pricing_raw = args.pricing.read_bytes()
    pricing = json.loads(pricing_raw)
    rates = {m: Rate(*(Decimal(pricing['models'][m][key]) for key in ('input', 'cached_input', 'output'))) for m in MODELS}
    if any(n < 0 for rate in rates.values() for n in (rate.input, rate.cached_input, rate.output)):
        raise ValueError('Prices must be nonnegative')
    runs, provenance = {}, {str(dataset.relative_to(ROOT)): dataset_hash,
        'pricing snapshot': hashlib.sha256(pricing_raw).hexdigest()}
    for model in MODELS:
        path = ROOT / 'eval' / 'results' / args.split / f'{model}.jsonl'
        raw = path.read_bytes()
        rows = [QuestionResult.model_validate_json(line) for line in raw.decode().splitlines() if line.strip()]
        if {row.question_id for row in rows} != expected_ids:
            raise ValueError(f'{model}: full selected split required')
        if any(row.dataset_split != args.split or row.dataset_sha256 != dataset_hash for row in rows):
            raise ValueError(f'{model}: dataset metadata mismatch')
        runs[model] = rows
        provenance[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    summaries, traces = simulate(runs, rates)
    report = markdown_report(summaries, traces, pricing, args.split, provenance)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = args.report_dir / f'oracle-cascade-{args.split}'
    stem.with_suffix('.md').write_text(report)
    stem.with_suffix('.json').write_text(json.dumps({'theoretical': True, 'split': args.split,
        'pricing': pricing, 'provenance': provenance, 'summaries': summaries}, indent=2) + '\n')
    stem.with_suffix('.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in traces))
    print(report.split('## Escalated cases')[0])
    print(f'Reports written to {stem}.md / .json / .jsonl')


if __name__ == '__main__':
    main()
