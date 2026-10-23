import json
from types import SimpleNamespace
from openai import OpenAI
import httpx
import pytest
from eval.decisions_check import request_body,judge,summarize,Judgment


def test_payload_contains_no_reference_or_labels():
    body=request_body('QUESTION_SENTINEL','CANDIDATE_SENTINEL')
    data=json.loads(body['input'])
    assert data=={'task':'QUESTION_SENTINEL','candidate_answer':'CANDIDATE_SENTINEL'}
    assert set(body)=={'model','input','questions'}


@pytest.mark.parametrize('probability,expected',[(0.49,False),(0.5,True),(0.9,True)])
def test_sdk_http_transport_and_fixed_threshold(probability,expected):
    def handler(request):
        assert request.url.path=='/v1/decisions'
        body=json.loads(request.content)
        assert body['questions'][0]['type']=='predicate'
        return httpx.Response(200,json={'model':'gpt-6-luna','answers':[{'type':'predicate','name':'acceptable','probability':probability}],'usage':{'input_tokens':123}})
    client=OpenAI(api_key='offline-test-placeholder',max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    result=judge('question','answer',client)
    assert result['accept'] is expected
    assert result['input_tokens']==123


def test_confusion_counts_are_scored_after_decision():
    base=dict(status='predicate',input_tokens=1,latency_seconds=1,dataset_sha256='d',luna_results_sha256='l',request_sha256='r')
    rows=[Judgment(question_id='a',probability=.9,accept=True,**base),
          Judgment(question_id='b',probability=.1,accept=False,**base)]
    counts=summarize(rows,{'a':SimpleNamespace(is_correct=False),'b':SimpleNamespace(is_correct=True)})
    assert counts['accept_benchmark_unsuccessful']==1
    assert counts['escalate_benchmark_correct']==1


@pytest.mark.parametrize("choice,expected", [("accept",True),("escalate",False)])
def test_choice_uses_returned_selection_not_confidence(choice,expected):
    def handler(request):
        body=json.loads(request.content)
        assert body['questions'][0]['type']=='choice'
        assert {c['value'] for c in body['questions'][0]['choices']}=={'accept','escalate'}
        assert set(json.loads(body['input']))=={'task','candidate_answer'}
        return httpx.Response(200,json={'model':'gpt-6-luna','answers':[{'type':'choice','name':'acceptable','choice':choice,
            'probabilities':[{'value':'accept','probability':.6 if expected else .4},{'value':'escalate','probability':.4 if expected else .6}],
            'confidence':.1}],'usage':{'input_tokens':150}})
    client=OpenAI(api_key='offline-test',http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    result=judge('question','answer',client,'choice')
    assert result['accept'] is expected
    assert result['selected_choice']==choice
    assert result['threshold'] is None
    assert result['confidence']==.1


def test_choice_refusal_is_unknown():
    client=OpenAI(api_key='offline-test',http_client=httpx.Client(transport=httpx.MockTransport(
        lambda req:httpx.Response(200,json={'model':'gpt-6-luna','answers':[{'type':'refusal','name':'acceptable'}],
            'usage':{'input_tokens':2}}))))
    result=judge('q','a',client,'choice')
    assert result['accept'] is None and result['selected_choice'] is None
