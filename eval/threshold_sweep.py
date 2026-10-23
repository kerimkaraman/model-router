"""Development-only threshold sweep of saved choice judgments. No API calls."""
import json
from decimal import Decimal
from pathlib import Path
from eval.choice_cascade import ROOT, load_inputs, replay

THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0)


def sweep(luna, sol, judgments, rates):
    baseline, _ = replay(luna, sol, judgments, rates)
    summaries = [baseline[0], baseline[1], baseline[-1]]
    traces = {}
    for threshold in THRESHOLDS:
        result, cases = replay(luna, sol, judgments, rates, escalation_threshold=threshold)
        summaries.append(result[-1])
        traces[str(threshold)] = cases
    return summaries, traces


def report(summaries, provenance):
    lines = ["# Development sweep: selective Luna → Sol escalation", "",
        "No API calls. Reuses the same saved choice probabilities, Luna/Sol answers and pricing.", "",
        "Policy: use Sol only if choice=escalate AND P(escalate) >= threshold. P(escalate) = 1 - P(accept), not the separate confidence field. Equality is included.", "",
        "| Strategy | Correct / 120 | Sol escalations | Repaired | Regressed | Estimated total USD | Mean recorded/simulated seconds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for s in summaries:
        lines.append(f"| {s['strategy']} | {s['correct']}/{s['questions']} | "
            f"{s.get('sol_calls','—')} | {s.get('repaired','—')} | {s.get('regressed','—')} | "
            f"${Decimal(s['estimated_cost_usd']):.6f} | {s['mean_latency_seconds']:.3f} |")
    baseline = summaries[0]
    candidates = [s for s in summaries[2:] if s['correct'] >= baseline['correct']]
    lines += ["", "## Comparison with using Luna alone", ""]
    if candidates:
        for s in candidates:
            delta = s['correct'] - baseline['correct']
            ratio = Decimal(s['estimated_cost_usd']) / Decimal(baseline['estimated_cost_usd'])
            lines.append(f"- {s['strategy']}: {delta:+d} correct; {ratio:.2f}× Luna-only estimated cost.")
    else:
        lines.append("No tested cascade matches Luna-only benchmark correctness.")
    dominant = [s for s in candidates if Decimal(s['estimated_cost_usd']) <= Decimal(baseline['estimated_cost_usd'])
        and s['mean_latency_seconds'] <= baseline['mean_latency_seconds']]
    lines += ["", "A tested cascade matches or improves Luna-only accuracy, cost and latency." if dominant else
        "No tested cascade matches or improves Luna-only accuracy, cost and latency simultaneously. More accuracy may still be worth a higher cost, but requires an explicit preference.",
        "", "## Limits", "",
        "- Thresholds are explored on development data after seeing baseline results. Do not treat the best threshold as validated on unseen requests.",
        "- Every cascade still pays for one Decisions judgment per question, even if the threshold causes no Sol escalations. The Luna-only baseline pays no judge overhead.",
        "- A larger returned probability is not a calibrated correctness guarantee. The separate choice confidence is not used.",
        "- Correctness is unchanged strict-v2: unit-format issues and ambiguous questions remain included. A one-case improvement is weak evidence, particularly on this small sample.",
        "- All costs include attempted calls. Sequential durations are sums of recorded requests, not live end-to-end measurements. No extra generation, judging, Astra or test-split access occurs.",
        "- Existing choice/predicate results and earlier reports are preserved. This module only writes threshold-sweep artifacts.",
        "", "## Reproduce", "", "```bash", "python -m eval.threshold_sweep", "```", "",
        "## Input hashes", ""]
    lines += [f"- `{name}`: `{digest}`" for name,digest in provenance.items()]
    return '\n'.join(lines)+'\n'


def main():
    runs, judgments, rates, provenance, pricing = load_inputs()
    summaries, traces = sweep(runs['luna'],runs['sol'],judgments,rates)
    text = report(summaries,provenance)
    stem = ROOT/'reports/threshold-sweep-dev'
    stem.parent.mkdir(exist_ok=True)
    stem.with_suffix('.md').write_text(text)
    stem.with_suffix('.json').write_text(json.dumps({'development_only':True,'thresholds':THRESHOLDS,
        'summaries':summaries,'provenance':provenance,'generation_pricing':pricing},indent=2)+'\n')
    stem.with_suffix('.jsonl').write_text(''.join(json.dumps({'threshold':threshold,**case})+'\n'
        for threshold,cases in traces.items() for case in cases))
    print(text.split('## Limits')[0])
    print(f'Report: {stem}.md')


if __name__ == '__main__':
    main()
