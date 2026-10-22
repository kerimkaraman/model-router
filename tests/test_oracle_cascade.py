from decimal import Decimal
import pytest
from eval.oracle_cascade import MODELS, Rate, estimate_cost, simulate
from eval.run_model import QuestionResult


def row(model, qid, correct):
    return QuestionResult(question_id=qid, model_name=model, model_answer='A', is_correct=correct,
        input_tokens=100, output_tokens=20, cached_input_tokens=50, reasoning_tokens=10,
        latency_seconds=1, response_status='completed', score_status='correct' if correct else 'incorrect',
        scorer_version='strict-v2', dataset_split='dev', dataset_sha256='fixture',
        reasoning_effort='low', max_output_tokens=4096)


def fixture_runs():
    # stop at Luna / Sol / Astra / all wrong
    outcomes = [(True, False, False), (False, True, False), (False, False, True), (False, False, False)]
    return {m: [row(m, str(i), o[j]) for i, o in enumerate(outcomes)] for j, m in enumerate(MODELS)}


def rates():
    return {m: Rate(Decimal(2), Decimal(1), Decimal(10)) for m in MODELS}


def test_cascade_pays_for_every_attempt_and_stops_on_success():
    summaries, traces = simulate(fixture_runs(), rates())
    cascade = summaries[-1]
    assert cascade['correct_count'] == 3
    assert cascade['calls_by_model'] == dict(zip(MODELS, [4, 3, 2]))
    assert cascade['calls'] == 9
    assert cascade['average_latency_seconds'] == 2.25
    assert Decimal(cascade['estimated_cost_usd']) == Decimal('0.00315')
    assert len(traces[0]['attempted_models']) == 1
    assert not traces[-1]['is_correct']


def test_cached_and_reasoning_tokens_are_not_double_counted():
    assert estimate_cost(row(MODELS[0], 'q', True), rates()[MODELS[0]]) == Decimal('0.00035')


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'metadata', 'model', 'status'])
def test_invalid_comparisons_rejected(change):
    runs = fixture_runs()
    if change == 'missing': runs[MODELS[1]].pop()
    elif change == 'duplicate': runs[MODELS[1]][1] = runs[MODELS[1]][0]
    elif change == 'metadata': runs[MODELS[1]][0].scorer_version = 'different'
    elif change == 'model': runs[MODELS[1]][0].model_name = 'other'
    else: runs[MODELS[0]][0].response_status = 'incomplete'
    with pytest.raises(ValueError): simulate(runs, rates())


@pytest.mark.parametrize('field,value', [('input_tokens', -1), ('cached_input_tokens', 101), ('reasoning_tokens', 21), ('input_tokens', 300000)])
def test_invalid_pricing_inputs_rejected(field, value):
    result = row(MODELS[0], 'q', True)
    setattr(result, field, value)
    with pytest.raises(ValueError): estimate_cost(result, rates()[MODELS[0]])
