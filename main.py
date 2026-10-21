"""Live Vocabulary Race — Chủ đề giao dịch ngân hàng (20 câu).

A single-process ASGI app for one classroom-sized group (multiple rooms supported).
Room data lives in process memory and is not durable on hosting restarts.
Do not configure multiple worker processes or multiple Render instances.
"""
import asyncio
import csv
import io
import json
import random
import re
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import qrcode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from questions import QUESTIONS

BASE = Path(__file__).parent
rooms: dict[str, 'Room'] = {}
ROOM_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
MAX_PLAYERS = 60
MAX_ROOMS = 100
WRONG_LOCK_SECONDS = 3


@dataclass
class Player:
    id: str
    token: str
    name: str
    sequence: list[dict] = field(default_factory=list)
    progress: int = 0
    mistakes: int = 0
    lock_until: float = 0
    finished_at: float | None = None
    finish_seconds: float | None = None
    joined_at: float = field(default_factory=time.time)
    reached_at: float | None = None
    color_index: int = 0


@dataclass
class Room:
    code: str
    secret: str
    phase: str = 'lobby'  # lobby, running, paused, ended
    players: dict[str, Player] = field(default_factory=dict)
    started_at: float | None = None
    paused_at: float | None = None
    ended_at: float | None = None
    pause_total: float = 0
    created_at: float = field(default_factory=time.time)
    sockets: dict[WebSocket, tuple[str, str | None]] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def get_room(code: str) -> Room:
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail='Không tìm thấy phòng thi.')
    return room


def teacher_ok(room: Room, key: str) -> None:
    if not key or not secrets.compare_digest(room.secret, key):
        raise HTTPException(status_code=403, detail='Không có quyền giáo viên.')


def get_player(room: Room, token: str) -> Player:
    for p in room.players.values():
        if token and secrets.compare_digest(token, p.token):
            return p
    raise HTTPException(status_code=403, detail='Phiên đăng nhập không hợp lệ. Hãy vào lại phòng.')


def elapsed(room: Room, at: float | None = None) -> float:
    if not room.started_at:
        return 0
    now = at if at is not None else (room.paused_at if room.phase == 'paused' else room.ended_at if room.phase == 'ended' else time.time())
    return max(0, now - room.started_at - room.pause_total)


def standings(room: Room) -> list[Player]:
    # Finalists sorted by elapsed completion time; unfinished racers by progress.
    return sorted(room.players.values(), key=lambda p: (
        0 if p.finish_seconds is not None else 1,
        p.finish_seconds if p.finish_seconds is not None else -p.progress,
        p.reached_at if p.reached_at is not None else p.joined_at,
        p.joined_at,
    ))


def teacher_state(room: Room) -> dict[str, Any]:
    ranks = standings(room)
    return {
        'type': 'state', 'role': 'teacher', 'code': room.code, 'phase': room.phase,
        'total': len(QUESTIONS), 'elapsed': round(elapsed(room), 1),
        'players': [{
            'id': p.id, 'name': p.name, 'progress': p.progress,
            'mistakes': p.mistakes, 'colorIndex': p.color_index, 'finishSeconds': round(p.finish_seconds, 2) if p.finish_seconds is not None else None,
            'locked': room.phase == 'running' and p.lock_until > time.time(),
            'reachedAt': p.reached_at,
            'rank': n + 1 if p.finish_seconds is not None else None,
        } for n, p in enumerate(ranks)],
        'finishedCount': sum(p.finished_at is not None for p in room.players.values()),
    }


def student_state(room: Room, p: Player) -> dict[str, Any]:
    item = p.sequence[p.progress] if p.sequence and p.progress < len(QUESTIONS) else None
    response = {
        'type': 'state', 'role': 'student', 'code': room.code, 'phase': room.phase,
        'name': p.name, 'progress': p.progress, 'total': len(QUESTIONS),
        'mistakes': p.mistakes, 'elapsed': round(elapsed(room), 1),
        'lockUntil': (int(p.lock_until * 1000) if room.phase == 'running' and p.lock_until > time.time() else 0),
        'lockRemainingMs': (max(0, int((p.lock_until - time.time()) * 1000)) if room.phase == 'running' else 0),
        'finishSeconds': round(p.finish_seconds, 2) if p.finish_seconds is not None else None,
        'rank': None, 'question': None,
    }
    if p.finished_at is not None:
        response['rank'] = next((i + 1 for i, x in enumerate(standings(room)) if x.id == p.id), None)
    if item and room.phase in ('running', 'paused'):
        response['question'] = {k: item[k] for k in ('id', 'direction', 'prompt', 'options')}
    if room.phase == 'ended':
        response['rank'] = next((i + 1 for i, x in enumerate(standings(room)) if x.id == p.id), None) if p.finished_at else None
    return response


async def broadcast(room: Room) -> None:
    # Every socket gets a role-specific payload (never leaks answers to students).
    dead = []
    prepared = []
    for ws, (role, pid) in list(room.sockets.items()):
        if role == 'teacher':
            payload = teacher_state(room)
        else:
            p = room.players.get(pid or '')
            if not p:
                dead.append(ws)
                continue
            payload = student_state(room, p)
        prepared.append((ws, payload))
    if prepared:
        results = await asyncio.gather(*(ws.send_json(payload) for ws, payload in prepared), return_exceptions=True)
        dead.extend(ws for (ws, _), result in zip(prepared, results) if isinstance(result, Exception))
    for ws in dead:
        room.sockets.pop(ws, None)


def build_sequence() -> list[dict]:
    seq = []
    for q in random.sample(QUESTIONS, len(QUESTIONS)):
        opts = q['options'].copy()
        random.shuffle(opts)
        seq.append({**q, 'options': opts})
    return seq


class JoinInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    token: str | None = None


class AnswerInput(BaseModel):
    token: str
    question_id: int
    choice: int = Field(ge=0, le=3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title='Vocabulary Race — Ngân hàng (20 câu)', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


@app.get('/')
def home():
    return RedirectResponse('/teacher', status_code=302)


@app.get('/teacher')
def teacher_page():
    return FileResponse(BASE / 'static' / 'teacher.html')


@app.get('/race/{code}')
def student_page(code: str):
    return FileResponse(BASE / 'static' / 'student.html')


@app.get('/health')
def health():
    return {'ok': True, 'rooms': len(rooms), 'questions': len(QUESTIONS)}


@app.post('/api/rooms')
async def create_room():
    # Avoid accumulating too many idle rooms in one process.
    if len(rooms) >= MAX_ROOMS:
        stale = [key for key, r in rooms.items() if r.phase == 'ended' or time.time() - r.created_at > 24 * 3600]
        for key in stale:
            rooms.pop(key, None)
    if len(rooms) >= MAX_ROOMS:
        raise HTTPException(503, 'Hệ thống đang có quá nhiều phòng. Vui lòng thử lại sau.')
    code = ''.join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
    while code in rooms:
        code = ''.join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
    room = Room(code=code, secret=secrets.token_urlsafe(24))
    rooms[code] = room
    return {'code': code, 'key': room.secret, 'total': len(QUESTIONS)}


@app.get('/api/rooms/{code}/teacher')
async def teacher_snapshot(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    return teacher_state(room)


@app.get('/api/rooms/{code}/qr.png')
async def room_qr(code: str, request: Request):
    room = get_room(code)
    url = str(request.base_url).rstrip('/') + '/race/' + room.code
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')


@app.post('/api/rooms/{code}/join')
async def join(code: str, data: JoinInput):
    room = get_room(code)
    async with room.lock:
        if data.token:
            for p in room.players.values():
                if secrets.compare_digest(data.token, p.token):
                    return {'token': p.token, 'name': p.name, 'code': code.upper(), 'resumed': True}
        if room.phase != 'lobby':
            raise HTTPException(409, 'Cuộc đua đã bắt đầu. Không thể tham gia mới.')
        name = ' '.join(data.name.split())
        if not name or len(name) > 30:
            raise HTTPException(400, 'Tên phải có 1–30 ký tự.')
        if len(room.players) >= MAX_PLAYERS:
            raise HTTPException(409, 'Phòng đã đủ 60 người.')
        if any(p.name.casefold() == name.casefold() for p in room.players.values()):
            raise HTTPException(409, 'Tên này đã có trong phòng. Vui lòng thêm số hoặc ký hiệu để phân biệt.')
        p = Player(id=secrets.token_hex(8), token=secrets.token_urlsafe(24), name=name, color_index=len(room.players))
        room.players[p.id] = p
        response = {'token': p.token, 'name': p.name, 'code': room.code, 'resumed': False}
        await broadcast(room)
        return response


@app.get('/api/rooms/{code}/student')
async def student_snapshot(code: str, token: str):
    room = get_room(code)
    p = get_player(room, token)
    return student_state(room, p)


@app.post('/api/rooms/{code}/start')
async def start(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    async with room.lock:
        if room.phase != 'lobby':
            raise HTTPException(409, 'Phòng không ở trạng thái chờ.')
        if not room.players:
            raise HTTPException(409, 'Cần có ít nhất một sinh viên tham gia.')
        for p in room.players.values():
            p.sequence = build_sequence()
            p.progress = 0
            p.reached_at = None
            p.mistakes = 0
            p.lock_until = 0
            p.finished_at = None
            p.finish_seconds = None
        room.started_at = time.time()
        room.pause_total = 0
        room.paused_at = None
        room.ended_at = None
        room.phase = 'running'
        await broadcast(room)
        return teacher_state(room)


@app.post('/api/rooms/{code}/pause')
async def pause(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    async with room.lock:
        if room.phase != 'running':
            raise HTTPException(409, 'Chỉ có thể tạm dừng khi cuộc đua đang chạy.')
        room.paused_at = time.time()
        room.phase = 'paused'
        await broadcast(room)
        return teacher_state(room)


@app.post('/api/rooms/{code}/resume')
async def resume(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    async with room.lock:
        if room.phase != 'paused' or room.paused_at is None:
            raise HTTPException(409, 'Cuộc đua chưa tạm dừng.')
        diff = time.time() - room.paused_at
        room.pause_total += diff
        for p in room.players.values():
            if p.lock_until > room.paused_at:
                p.lock_until += diff
        room.paused_at = None
        room.ended_at = None
        room.phase = 'running'
        await broadcast(room)
        return teacher_state(room)


@app.post('/api/rooms/{code}/end')
async def end(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    async with room.lock:
        if room.phase not in ('running', 'paused'):
            raise HTTPException(409, 'Cuộc đua chưa bắt đầu hoặc đã kết thúc.')
        if room.phase == 'paused' and room.paused_at is not None:
            room.pause_total += time.time() - room.paused_at
            room.paused_at = None
        room.phase = 'ended'
        room.ended_at = time.time()
        await broadcast(room)
        return teacher_state(room)


@app.post('/api/rooms/{code}/reset')
async def reset(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    async with room.lock:
        room.phase = 'lobby'
        room.started_at = None
        room.paused_at = None
        room.ended_at = None
        room.pause_total = 0
        for p in room.players.values():
            p.sequence = []
            p.progress = 0
            p.reached_at = None
            p.mistakes = 0
            p.lock_until = 0
            p.finished_at = None
            p.finish_seconds = None
        await broadcast(room)
        return teacher_state(room)


@app.post('/api/rooms/{code}/answer')
async def answer(code: str, data: AnswerInput):
    room = get_room(code)
    async with room.lock:
        p = get_player(room, data.token)
        if room.phase == 'paused':
            raise HTTPException(409, 'Giáo viên đã tạm dừng cuộc đua.')
        if room.phase != 'running':
            raise HTTPException(409, 'Cuộc đua chưa bắt đầu hoặc đã kết thúc.')
        now = time.time()
        if p.finished_at is not None:
            raise HTTPException(409, 'Bạn đã về đích.')
        if now < p.lock_until:
            return {'correct': False, 'locked': True, 'waitMs': int((p.lock_until - now) * 1000 + 0.999)}
        q = p.sequence[p.progress]
        if data.question_id != q['id']:
            raise HTTPException(409, 'Câu hỏi đã thay đổi. Vui lòng tải trạng thái mới.')
        correct = q['options'][data.choice] == q['answer']
        if correct:
            p.progress += 1
            p.reached_at = now
            p.lock_until = 0
            if p.progress == len(QUESTIONS):
                p.finished_at = now
                p.finish_seconds = elapsed(room, at=now)
                if all(x.finished_at is not None for x in room.players.values()):
                    room.phase = 'ended'
                    room.ended_at = now
        else:
            p.mistakes += 1
            p.lock_until = now + WRONG_LOCK_SECONDS
        await broadcast(room)
        return {'correct': correct, 'locked': not correct, 'waitMs': WRONG_LOCK_SECONDS * 1000 if not correct else 0,
                'progress': p.progress, 'finished': p.finished_at is not None}


@app.get('/api/rooms/{code}/results.csv')
async def results(code: str, key: str):
    room = get_room(code)
    teacher_ok(room, key)
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Excel Vietnamese and Korean
    writer = csv.writer(output)
    writer.writerow(['Xếp hạng', 'Sinh viên', 'Câu đúng', 'Tổng câu', 'Lượt trả lời sai', 'Thời gian hoàn thành (giây)', 'Trạng thái'])
    for index, p in enumerate(standings(room), 1):
        writer.writerow([
            index if p.finished_at else '', p.name, p.progress, len(QUESTIONS), p.mistakes,
            f'{p.finish_seconds:.2f}' if p.finish_seconds is not None else '',
            'Hoàn thành' if p.finished_at else 'Chưa hoàn thành',
        ])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue().encode('utf-8')]), media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition': f'attachment; filename="vocabulary-race-{room.code}.csv"'})


@app.websocket('/ws/{code}')
async def websocket_room(ws: WebSocket, code: str):
    room = rooms.get(code.upper())
    if not room:
        await ws.close(code=4404)
        return
    role = ws.query_params.get('role')
    key = ws.query_params.get('key', '')
    token = ws.query_params.get('token', '')
    try:
        if role == 'teacher':
            teacher_ok(room, key)
            pid = None
        elif role == 'student':
            pid = get_player(room, token).id
        else:
            await ws.close(code=4403)
            return
    except HTTPException:
        await ws.close(code=4403)
        return
    await ws.accept()
    room.sockets[ws] = (role, pid)
    try:
        if role == 'teacher':
            await ws.send_json(teacher_state(room))
        else:
            await ws.send_json(student_state(room, room.players[pid]))
        while True:
            # Pings used to maintain socket and renew lock countdown.
            await ws.receive_text()
            if role == 'teacher':
                await ws.send_json(teacher_state(room))
            else:
                await ws.send_json(student_state(room, room.players[pid]))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        room.sockets.pop(ws, None)
