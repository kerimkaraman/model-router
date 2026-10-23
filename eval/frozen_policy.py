"""Evaluate the already selected 0.60 policy; no threshold tuning or API calls."""
import hashlib
import json
from pathlib import Path
from eval.choice_cascade import ROOT, load_inputs, replay
from eval.decisions_check import POLICY_HASH, POLICY_VERSION

POLICY_PATH = ROOT / 'eval/cascade_policy.json'


def verify_policy(policy):
    if (policy['escalation_threshold'] != .6 or policy['judge_policy_hash'] != POLICY_HASH
            or policy['judge_policy_version'] != POLICY_VERSION
            or policy['models'] != ['gpt-6-luna','gpt-6-sol']):
        raise ValueError('Frozen policy settings differ')
    for name,digest in policy['frozen_input_hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Frozen input changed: {name}')


def main():
    policy=json.loads(POLICY_PATH.read_text())
    verify_policy(policy)
    runs,judgments,rates,provenance,pricing=load_inputs('test')
    summaries,traces=replay(runs['luna'],runs['sol'],judgments,rates,
        escalation_threshold=policy['escalation_threshold'])
    result=summaries[-1]
    lines=['# Fixed 0.60 policy — reserved evaluation split','',
        'The threshold and judge rubric were fixed before collecting these OpenAI evaluation outputs. No threshold sweep is performed here.','',
        '| Strategy | Correct | Accuracy | Generation calls | Decisions calls | Estimated USD | Mean recorded/simulated seconds |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in summaries:
        lines.append(f"| {s['strategy']} | {s['correct']}/{s['questions']} | {100*s['correct']/s['questions']:.2f}% | "
            f"{s['generation_calls']} | {s['judge_calls']} | ${float(s['estimated_cost_usd']):.6f} | {s['mean_latency_seconds']:.3f} |")
    lines += ['',f"Sol escalations: {result['sol_calls']}; repaired: {result['repaired']}; regressed: {result['regressed']}.",'',
        '## Changed benchmark outcomes','',
        '| Case | Effect | Selected model |','| --- | --- | --- |']
    lines += [f"| {t['question_id']} | {t['transition']} | {t['selected_model']} |" for t in traces if t['transition'] in ('repaired','regressed')]
    lines += ['','## Interpretation','',
        '- Every task pays for Luna generation and a Decisions choice judgment. Sol is used only if choice=escalate and P(escalate)>=0.60. There is no Astra or second judgment.',
        '- Reference labels are used only to score selected outputs, not to make routing decisions. Strict-v2 benchmark labels remain unchanged.',
        '- The original source pool had historical Gemma outputs before splitting: this reserved split is not a pristine unseen holdout. This is a fixed-policy evaluation on a previously exposed source pool.',
        '- Baseline collection called both generation models for every question; the cascade figures are offline replay estimates, not actual invoice totals or live cascade timing. Judge cost/duration are included.',
        '- Scorer format penalties, ambiguous benchmark questions, small sample size and same-family judge errors remain limitations. Do not adjust the threshold against these results.',
        f"- Policy: `{policy['version']}`. Pricing: `{pricing['version']}`.",'',
        '## Reproduce','','```bash','python -m eval.frozen_policy','```','',
        '## Input hashes','']
    provenance['eval/cascade_policy.json']=hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()
    lines += [f'- `{name}`: `{digest}`' for name,digest in provenance.items()]
    text='\n'.join(lines)+'\n'
    stem=ROOT/'reports/fixed-policy-test'
    stem.parent.mkdir(exist_ok=True)
    stem.with_suffix('.md').write_text(text)
    stem.with_suffix('.json').write_text(json.dumps({'policy':policy,'summaries':summaries,'provenance':provenance,'pricing':pricing},indent=2)+'\n')
    stem.with_suffix('.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in traces))
    print(text.split('## Changed benchmark outcomes')[0])
    print(f'Report: {stem}.md')


if __name__=='__main__':
    main()
