"""Replay one Luna-to-Sol escalation using saved Decisions choice judgments."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from eval.decisions_check import (
    Judgment, POLICY_HASH, POLICY_VERSION, PRICE_PER_MILLION_INPUT, request_body,
)
from eval.oracle_cascade import Rate, estimate_cost
from eval.run_model import QuestionResult, load_questions
from eval.summarize import summarize_agreement

ROOT = Path(__file__).resolve().parents[1]
LUNA = "gpt-6-luna"
SOL = "gpt-6-sol"


def select_model(selected_choice: str, accept_probability: float | None = None,
                 escalation_threshold: float | None = None) -> str:
    # Selection has no access to benchmark correctness or reference answers.
    if escalation_threshold is not None:
        if not 0 <= escalation_threshold <= 1:
            raise ValueError("Escalation threshold must be between 0 and 1")
        if accept_probability is None or not 0 <= accept_probability <= 1:
            raise ValueError("Valid accept probability required for threshold policy")
    if selected_choice == "accept":
        return LUNA
    if selected_choice == "escalate":
        if escalation_threshold is None:
            return SOL
        escalation_probability = Decimal(1) - Decimal(str(accept_probability))
        return SOL if escalation_probability >= Decimal(str(escalation_threshold)) else LUNA
    raise ValueError("Only explicit accept/escalate choices are supported")


def replay(luna, sol, judgments, rates, escalation_threshold: float | None = None):
    if not luna or not sol:
        raise ValueError("Nonempty model runs required")
    summarize_agreement(luna, sol)  # Identical IDs and dataset/scorer settings.
    if any(row.model_name != LUNA for row in luna) or any(row.model_name != SOL for row in sol):
        raise ValueError("Unexpected baseline model identity")
    for rows in (luna, sol):
        if len({(row.reasoning_effort, row.max_output_tokens) for row in rows}) != 1:
            raise ValueError("Mixed generation settings")
        for row in rows:
            if row.is_correct != (row.score_status == "correct" and row.response_status == "completed"):
                raise ValueError("Inconsistent saved correctness")
            if row.latency_seconds < 0:
                raise ValueError("Negative duration")
    if (luna[0].reasoning_effort, luna[0].max_output_tokens) != (sol[0].reasoning_effort, sol[0].max_output_tokens):
        raise ValueError("Baseline generation settings differ")
    by_sol = {row.question_id: row for row in sol}
    by_judge = {j.question_id: j for j in judgments}
    if len(by_judge) != len(judgments) or set(by_judge) != {row.question_id for row in luna}:
        raise ValueError("Complete unique matching judgments required")
    for j in judgments:
        if j.mode != "choice" or j.status != "choice" or j.threshold is not None:
            raise ValueError("Only successful choice judgments can be replayed")
        model = select_model(j.selected_choice)
        if j.accept != (model == LUNA):
            raise ValueError("Inconsistent saved choice")
        if j.policy_sha256 != POLICY_HASH or j.policy_version != POLICY_VERSION:
            raise ValueError("Unexpected evaluator policy")
        if (j.dataset_sha256 != luna[0].dataset_sha256 or j.model != LUNA):
            raise ValueError("Judge dataset or model mismatch")
    traces = []
    for first in luna:
        second, decision = by_sol[first.question_id], by_judge[first.question_id]
        selected = select_model(decision.selected_choice, decision.probability, escalation_threshold)
        final = first if selected == LUNA else second
        escalated = selected == SOL
        first_cost = estimate_cost(first, rates[LUNA])
        second_cost = estimate_cost(second, rates[SOL])
        judge_cost = Decimal(decision.input_tokens) * PRICE_PER_MILLION_INPUT / Decimal(1_000_000)
        transition = ("repaired" if not first.is_correct and final.is_correct else
                      "regressed" if first.is_correct and not final.is_correct else
                      "unchanged_correct" if final.is_correct else "unchanged_unsuccessful")
        traces.append({"question_id": first.question_id, "choice": decision.selected_choice,
            "selected_model": selected, "luna_correct": first.is_correct,
            "final_correct": final.is_correct, "transition": transition,
            "luna_cost_usd": str(first_cost), "judge_cost_usd": str(judge_cost),
            "sol_cost_usd": str(second_cost if escalated else Decimal(0)),
            "estimated_cost_usd": str(first_cost + judge_cost + (second_cost if escalated else 0)),
            "simulated_latency_seconds": first.latency_seconds + decision.latency_seconds
                + (second.latency_seconds if escalated else 0)})
    summaries = []
    for name, rows in ((LUNA, luna), (SOL, sol)):
        summaries.append({"strategy": name, "correct": sum(row.is_correct for row in rows),
            "questions": len(rows), "generation_calls": len(rows), "judge_calls": 0,
            "estimated_cost_usd": str(sum((estimate_cost(row, rates[name]) for row in rows), Decimal(0))),
            "mean_latency_seconds": sum(row.latency_seconds for row in rows) / len(rows)})
    escalations = sum(t['selected_model'] == SOL for t in traces)
    summaries.append({"strategy": "Luna + Decisions choice → Sol" if escalation_threshold is None else f"Choice escalation probability >= {escalation_threshold}",
        "escalation_threshold": escalation_threshold, "correct": sum(t['final_correct'] for t in traces),
        "questions": len(traces), "generation_calls": len(traces) + escalations,
        "judge_calls": len(traces), "luna_calls": len(traces), "sol_calls": escalations,
        "estimated_cost_usd": str(sum((Decimal(t['estimated_cost_usd']) for t in traces), Decimal(0))),
        "judge_cost_usd": str(sum((Decimal(t['judge_cost_usd']) for t in traces), Decimal(0))),
        "mean_latency_seconds": sum(t['simulated_latency_seconds'] for t in traces) / len(traces),
        "repaired": sum(t['transition'] == 'repaired' for t in traces),
        "regressed": sum(t['transition'] == 'regressed' for t in traces)})
    return summaries, traces


def make_report(summaries, traces, provenance, pricing):
    result = summaries[-1]
    lines = ["# Luna → Decisions choice → Sol", "",
        "Offline replay of a single escalation. No new API calls. Astra is not used or read.", "",
        "| Strategy | Correct | Accuracy | Generation calls | Decisions calls | Estimated USD | Mean recorded/simulated latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for s in summaries:
        lines.append(f"| {s['strategy']} | {s['correct']}/{s['questions']} | "
            f"{100*s['correct']/s['questions']:.2f}% | {s['generation_calls']} | {s['judge_calls']} | "
            f"${Decimal(s['estimated_cost_usd']):.6f} | {s['mean_latency_seconds']:.3f} s |")
    lines += ["", f"Escalations: **{result['sol_calls']}**. Repaired benchmark outcomes: **{result['repaired']}**. Regressed outcomes: **{result['regressed']}**.",
        f"Decisions cost is included in the total: ${Decimal(result['judge_cost_usd']):.6f}.",
        "", "## All escalations", "",
        "| Case | Luna correct | Sol final correct | Effect | Estimated case USD |",
        "| --- | --- | --- | --- | ---: |"]
    for t in traces:
        if t['selected_model'] == SOL:
            lines.append(f"| {t['question_id']} | {t['luna_correct']} | {t['final_correct']} | {t['transition']} | ${Decimal(t['estimated_cost_usd']):.6f} |")
    lines += ["", "## Final unsuccessful cases", ""]
    lines += [f"- `{t['question_id']}`: selected `{t['selected_model']}`; {t['transition']}." for t in traces if not t['final_correct']]
    lines += ["", "## Meaning of the result", "",
        "- Every task first incurs Luna generation plus one saved Decisions request. Accept retains Luna; escalate uses Sol once and stops, regardless of Sol's correctness. There is no second judge or Astra fallback.",
        "- Selection uses only the saved accept/escalate choice. Correctness labels are consulted after selection for evaluation, not to choose the final model.",
        "- A stronger model is not guaranteed to repair a rejected answer. The report counts both repairs and regressions explicitly.",
        "- Correctness retains strict-v2 benchmark scoring, including unit-format penalties and ambiguous cases. It is not a fresh adjudication of substantive truth.",
        "- This is development-set replay, not live or held-out performance. Durations sum standalone recorded Luna, judge and optionally Sol calls. Network/cache conditions and executor overhead may differ live.",
        "- Costs include all attempted generation and judging. Generation uses the dated short-context Standard pricing snapshot; Decisions uses the documented $0.10/1M input-token estimate from its saved experiment. These are scenario estimates, not invoices, and exclude regional/long-context adjustments.",
        f"- Generation pricing snapshot: `{pricing['version']}`. Decisions policy: `{POLICY_VERSION}`, choice mode, no confidence threshold.",
        "- Inputs, original judgments and baseline scores are preserved. Predicate, format and oracle results are not modified. Test split is not read.",
        "", "## Reproduce", "", "```bash", "python -m eval.choice_cascade", "```", "",
        "## Input hashes", ""]
    lines += [f"- `{name}`: `{digest}`" for name, digest in provenance.items()]
    return '\n'.join(lines) + '\n'


def load_inputs(split: str = "dev"):
    if split not in ("dev", "test"):
        raise ValueError("Unknown split")
    paths = {'dataset': ROOT / f'eval/data/{split}.jsonl', 'luna': ROOT / f'eval/results/{split}/gpt-6-luna.jsonl',
             'sol': ROOT / f'eval/results/{split}/gpt-6-sol.jsonl',
             'judgments': ROOT / f'eval/results/decisions/luna-{split}-choice.jsonl',
             'pricing': ROOT/'eval/pricing.json'}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
    questions = {q.question_id:q for q in load_questions(paths['dataset'])}
    runs = {name:[QuestionResult.model_validate_json(s) for s in raw[name].decode().splitlines() if s.strip()] for name in ('luna','sol')}
    for name, rows in runs.items():
        if {row.question_id for row in rows} != set(questions):
            raise ValueError(f'{name}: complete selected split required')
        if any(row.dataset_split != split or row.dataset_sha256 != hashes['dataset'] for row in rows):
            raise ValueError(f'{name}: dataset hash mismatch')
    judgments = [Judgment.model_validate_json(s) for s in raw['judgments'].decode().splitlines() if s.strip()]
    luna_by_id = {row.question_id:row for row in runs['luna']}
    for j in judgments:
        if j.question_id not in questions:
            raise ValueError('Unknown judgment ID')
        body = request_body(questions[j.question_id].prompt, luna_by_id[j.question_id].model_answer, 'choice')
        request_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if j.luna_results_sha256 != hashes['luna'] or j.request_sha256 != request_hash:
            raise ValueError('Judgment does not match source answer or request policy')
    pricing = json.loads(raw['pricing'])
    rates = {model:Rate(*(Decimal(pricing['models'][model][k]) for k in ('input','cached_input','output'))) for model in (LUNA,SOL)}
    if any(not value.is_finite() or value < 0 for rate in rates.values() for value in (rate.input,rate.cached_input,rate.output)):
        raise ValueError('Invalid price')
    provenance = {str(paths[name].relative_to(ROOT)):digest for name,digest in hashes.items()}
    return runs, judgments, rates, provenance, pricing


def main():
    runs, judgments, rates, provenance, pricing = load_inputs()
    summaries, traces = replay(runs['luna'],runs['sol'],judgments,rates)
    text = make_report(summaries,traces,provenance,pricing)
    stem = ROOT/'reports/choice-cascade-dev'
    stem.parent.mkdir(exist_ok=True)
    stem.with_suffix('.md').write_text(text)
    stem.with_suffix('.json').write_text(json.dumps({'offline_replay':True,'summaries':summaries,'provenance':provenance,
        'generation_pricing':pricing,'decisions_input_usd_per_million':str(PRICE_PER_MILLION_INPUT)},indent=2)+'\n')
    stem.with_suffix('.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in traces))
    print(text.split('## All escalations')[0])
    print(f'Report: {stem}.md')


if __name__ == '__main__':
    main()
