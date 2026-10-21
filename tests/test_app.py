from fastapi.testclient import TestClient
import pytest
from main import app, rooms, elapsed, QUESTIONS

@pytest.fixture
def client():
    rooms.clear()
    with TestClient(app) as c:
        yield c
    rooms.clear()

def make_room(client):
    resp = client.post('/api/rooms')
    assert resp.status_code == 200
    return resp.json()

def join(client,code,name):
    resp = client.post(f'/api/rooms/{code}/join',json={'name':name})
    assert resp.status_code == 200
    return resp.json()

def do_answer(client,code,token,q,choice):
    return client.post(f'/api/rooms/{code}/answer',json={
        'token':token,'question_id':q['id'],'choice':choice})

def solve_one(client,code,p):
    q=p.sequence[p.progress]
    i=q['options'].index(q['answer'])
    return do_answer(client,code,p.token,q,i)

def test_health_and_pages(client):
    assert client.get('/health').json()['questions']==20
    assert client.get('/teacher').status_code==200
    assert client.get('/race/TEST').status_code==200
    assert client.get('/static/style.css').status_code==200
    assert sum(q['direction']=='ko-vi' for q in QUESTIONS)==14
    assert sum(q['direction']=='vi-ko' for q in QUESTIONS)==6


def test_create_join_start_answer_wrong_retry_after_lock(client):
    r=make_room(client);code=r['code'];key=r['key']
    teacher=client.get(f'/api/rooms/{code}/teacher?key={key}')
    assert teacher.status_code==200
    assert client.get(f'/api/rooms/{code}/teacher?key=nope').status_code==403
    a=join(client,code,'Nguyễn Minh Anh');
    assert client.post(f'/api/rooms/{code}/join',json={'name':'Nguyễn Minh Anh'}).status_code==409
    assert client.post(f'/api/rooms/{code}/start?key={key}').status_code==200
    assert client.post(f'/api/rooms/{code}/join',json={'name':'Sinh viên mới'}).status_code==409
    p=next(iter(rooms[code].players.values()))
    assert len(p.sequence)==20
    snapshot=client.get(f'/api/rooms/{code}/student?token={a["token"]}').json()
    assert 'answer' not in str(snapshot) and snapshot['question']
    q=p.sequence[0]
    wrong=next(i for i,x in enumerate(q['options']) if x!=q['answer'])
    result=do_answer(client,code,p.token,q,wrong)
    assert result.status_code==200 and result.json()['locked'] and p.mistakes==1 and p.progress==0
    again=solve_one(client,code,p)
    assert again.status_code==200 and again.json()['locked'] and p.progress==0
    p.lock_until=0
    good=solve_one(client,code,p)
    assert good.status_code==200 and good.json()['correct'] and p.progress==1
    qr=client.get(f'/api/rooms/{code}/qr.png')
    assert qr.status_code==200 and qr.headers['content-type']=='image/png' and qr.content.startswith(b'\x89PNG')


def test_pause_resume_freezes_time_and_authorization(client):
    r=make_room(client);code=r['code'];key=r['key']
    a=join(client,code,'Hà');client.post(f'/api/rooms/{code}/start?key={key}')
    p=next(iter(rooms[code].players.values()))
    assert client.post(f'/api/rooms/{code}/pause?key=no').status_code==403
    assert client.post(f'/api/rooms/{code}/pause?key={key}').status_code==200
    paused=elapsed(rooms[code]);assert rooms[code].phase=='paused'
    assert solve_one(client,code,p).status_code==409
    assert client.post(f'/api/rooms/{code}/resume?key={key}').status_code==200
    assert rooms[code].phase=='running'
    assert abs(elapsed(rooms[code])-paused)<1
    assert solve_one(client,code,p).status_code==200


def test_finish_rank_csv_and_reset(client):
    r=make_room(client);code=r['code'];key=r['key']
    a=join(client,code,'Anh');b=join(client,code,'Bình')
    client.post(f'/api/rooms/{code}/start?key={key}')
    p1=next(p for p in rooms[code].players.values() if p.name=='Anh')
    p2=next(p for p in rooms[code].players.values() if p.name=='Bình')
    for i in range(20):
        result=solve_one(client,code,p1)
        assert result.status_code==200 and result.json()['correct']
    assert p1.progress==20 and rooms[code].phase=='running'
    for i in range(20):
        assert solve_one(client,code,p2).json()['correct']
    assert rooms[code].phase=='ended'
    final=client.get(f'/api/rooms/{code}/teacher?key={key}').json()
    assert final['finishedCount']==2 and final['players'][0]['name']=='Anh'
    assert final['players'][0]['rank']==1 and final['players'][1]['rank']==2
    assert client.get(f'/api/rooms/{code}/results.csv?key=wrong').status_code==403
    csv_resp=client.get(f'/api/rooms/{code}/results.csv?key={key}')
    assert csv_resp.status_code==200
    content=csv_resp.content.decode('utf-8-sig')
    assert 'Anh' in content and 'Bình' in content and 'Lượt trả lời sai' in content
    assert client.post(f'/api/rooms/{code}/reset?key={key}').status_code==200
    assert p1.progress==0 and rooms[code].phase=='lobby'
    assert join(client,code,'Ngọc')['name']=='Ngọc'


def test_websocket_updates_and_resume_player_token(client):
    r=make_room(client);code=r['code'];key=r['key']
    a=join(client,code,'Linh')
    resumed=client.post(f'/api/rooms/{code}/join',json={'name':'Whatever','token':a['token']}).json()
    assert resumed['resumed'] and resumed['name']=='Linh'
    with client.websocket_connect(f'/ws/{code}?role=teacher&key={key}') as teacher:
        s=teacher.receive_json();assert s['role']=='teacher' and s['phase']=='lobby'
        with client.websocket_connect(f'/ws/{code}?role=student&token={a["token"]}') as student:
            assert student.receive_json()['phase']=='lobby'
            assert client.post(f'/api/rooms/{code}/start?key={key}').status_code==200
            teach_update=teacher.receive_json();stud_update=student.receive_json()
            assert teach_update['phase']=='running' and stud_update['question']['id']
            assert 'answer' not in stud_update['question']


def test_manual_end_time_frozen(client):
    r=make_room(client);code=r['code'];key=r['key']
    join(client,code,'Test')
    client.post(f'/api/rooms/{code}/start?key={key}')
    assert client.post(f'/api/rooms/{code}/end?key={key}').status_code==200
    e=elapsed(rooms[code])
    assert e==elapsed(rooms[code])
