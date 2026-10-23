from decimal import Decimal
import pytest
from eval.choice_cascade import LUNA,SOL,replay,select_model
from eval.decisions_check import Judgment
from eval.oracle_cascade import Rate
from eval.run_model import QuestionResult


def row(model,qid,correct):
    return QuestionResult(question_id=qid,model_name=model,model_answer='B',is_correct=correct,
        input_tokens=10,output_tokens=5,latency_seconds=1,score_status='correct' if correct else 'incorrect',
        dataset_split='dev',dataset_sha256='fixture',scorer_version='strict-v2',reasoning_effort='low',max_output_tokens=4096)


def decisions(choices):
    return [Judgment(question_id=str(i),mode='choice',status='choice',selected_choice=c,
        accept=c=='accept',threshold=None,input_tokens=100,latency_seconds=.5,
        dataset_sha256='fixture',luna_results_sha256='l',request_sha256='r') for i,c in enumerate(choices)]


def test_repairs_regressions_and_full_cost():
    luna=[row(LUNA,str(i),v) for i,v in enumerate([True,False,True,False])]
    sol=[row(SOL,str(i),v) for i,v in enumerate([False,True,False,True])]
    rates={m:Rate(Decimal(1),Decimal(0),Decimal(1)) for m in (LUNA,SOL)}
    summaries,traces=replay(luna,sol,decisions(['accept','escalate','escalate','accept']),rates)
    result=summaries[-1]
    assert result['correct']==2
    assert result['repaired']==1 and result['regressed']==1
    assert result['generation_calls']==6 and result['judge_calls']==4
    assert result['mean_latency_seconds']==2
    assert Decimal(result['estimated_cost_usd'])==Decimal('0.00013')
    assert [t['selected_model'] for t in traces]==[LUNA,SOL,SOL,LUNA]


def test_unknown_choice_rejected():
    with pytest.raises(ValueError):select_model('unknown')


def test_missing_judgments_rejected():
    with pytest.raises(ValueError):
        replay([row(LUNA,'0',True)],[row(SOL,'0',True)],[],{LUNA:Rate(Decimal(1),Decimal(0),Decimal(1)),SOL:Rate(Decimal(1),Decimal(0),Decimal(1))})


def test_selection_has_no_correctness_input():
    assert select_model('accept')==LUNA
    assert select_model('escalate')==SOL


@pytest.mark.parametrize('choice,p_accept,threshold,expected',[
    ('escalate',.2,.8,SOL),
    ('escalate',.21,.8,LUNA),
    ('accept',.1,.8,LUNA),
    ('escalate',0,1,SOL),
    ('escalate',.5,.5,SOL),
])
def test_probability_threshold_policy(choice,p_accept,threshold,expected):
    assert select_model(choice,p_accept,threshold)==expected


@pytest.mark.parametrize('threshold,p_accept',[(1.1,.2),(-.1,.2),(.8,None),(.8,1.1)])
def test_invalid_threshold_or_probability(threshold,p_accept):
    with pytest.raises(ValueError):select_model('escalate',p_accept,threshold)


def test_judge_overhead_remains_when_threshold_blocks_sol():
    luna=[row(LUNA,'0',True)]
    sol=[row(SOL,'0',False)]
    js=decisions(['escalate'])
    js[0].probability=.4
    rates={m:Rate(Decimal(1),Decimal(0),Decimal(1)) for m in (LUNA,SOL)}
    summary,traces=replay(luna,sol,js,rates,escalation_threshold=.9)
    assert summary[-1]['sol_calls']==0
    assert summary[-1]['judge_calls']==1
    assert summary[-1]['correct']==1
    assert Decimal(summary[-1]['estimated_cost_usd'])==Decimal('0.000025')
    assert summary[-1]['mean_latency_seconds']==1.5
