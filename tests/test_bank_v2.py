import pytest
from fastapi.testclient import TestClient
from main import app,rooms,QUESTIONS,teacher_state,standings

@pytest.fixture
def client():
    rooms.clear()
    with TestClient(app) as c:
        yield c
    rooms.clear()

def test_bank_content_and_security(client):
    assert len(QUESTIONS) == 20
    assert {x['id'] for x in QUESTIONS} == set(range(1,21))
    assert [sum(q['direction']==d for q in QUESTIONS) for d in ('ko-vi','vi-ko')] == [14,6]
    assert all(len(q['options'])==4 and q['answer'] in q['options'] for q in QUESTIONS)
    r=client.post('/api/rooms').json();code,key=r['code'],r['key']
    assert client.get(f'/api/rooms/{code}/teacher?key=wrong').status_code==403
    student=client.post(f'/api/rooms/{code}/join',json={'name':'Thử nghiệm'}).json()
    client.post(f'/api/rooms/{code}/start?key={key}')
    snap=client.get(f'/api/rooms/{code}/student?token={student["token"]}').json()
    assert 'answer' not in snap['question'] and len(snap['question']['options'])==4
    assert snap['total']==20

def test_ranking_reorders_without_changing_color(client):
    r=client.post('/api/rooms').json();code,key=r['code'],r['key']
    for name in ('An','Bình','Chi'):
        client.post(f'/api/rooms/{code}/join',json={'name':name})
    room=rooms[code]
    people={p.name:p for p in room.players.values()}
    assert {p.name:p.color_index for p in room.players.values()}=={'An':0,'Bình':1,'Chi':2}
    client.post(f'/api/rooms/{code}/start?key={key}')
    def advance(p):
        q=p.sequence[p.progress]
        return client.post(f'/api/rooms/{code}/answer',json={'token':p.token,'question_id':q['id'],'choice':q['options'].index(q['answer'])})
    assert advance(people['An']).json()['correct']
    assert advance(people['Chi']).json()['correct']
    assert teacher_state(room)['players'][0]['name']=='An'  # đạt 1 câu trước
    assert advance(people['Chi']).json()['correct']
    state=teacher_state(room)
    assert [p['name'] for p in state['players']]==['Chi','An','Bình']
    assert [p['colorIndex'] for p in state['players']]==[2,0,1]
    assert [p['progress'] for p in state['players']]==[2,1,0]

