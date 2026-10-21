'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const qs = new URLSearchParams(location.search);
let room = qs.get('room') || '', key = qs.get('key') || '', socket = null, latest = null;
let lastSyncAt = Date.now();
const phaseNames = {lobby:'Chờ sinh viên',running:'Đang đua',paused:'Đã tạm dừng',ended:'Đã kết thúc'};
async function api(path, method='GET') {
 const res = await fetch(`/api/rooms/${encodeURIComponent(room)}${path}`,{method});
 let data; try{data=await res.json()}catch{throw Error('Không đọc được phản hồi máy chủ.')}
 if(!res.ok)throw Error(data.detail || 'Có lỗi xảy ra.'); return data;
}
function error(msg){$('teacher-info').textContent=msg; $('teacher-info').className='notice error'}
function message(msg){$('teacher-info').textContent=msg; $('teacher-info').className='notice'}
async function action(endpoint, confirmText){
 if(confirmText&&!confirm(confirmText))return;
 try{await api(`${endpoint}?key=${encodeURIComponent(key)}`,'POST')}catch(e){error(e.message)}
}
async function init(){
 if(!room||!key)return;
 try{latest=await api(`/teacher?key=${encodeURIComponent(key)}`)}catch(e){$('create-error').textContent='Không thể mở phòng cũ: '+e.message; $('create-error').classList.remove('hidden');return}
 $('welcome').classList.add('hidden');$('dashboard').classList.remove('hidden');
 $('room-code').textContent=room;
 let studentUrl=`${location.origin}/race/${encodeURIComponent(room)}`;
 $('student-url').textContent=studentUrl;
 $('qr').src=`/api/rooms/${encodeURIComponent(room)}/qr.png`;
 $('copy-student').onclick=()=>copy(studentUrl,'Đã sao chép liên kết sinh viên.');
 $('teacher-link').onclick=()=>copy(location.href,'Đã sao chép liên kết bí mật dành cho giáo viên.');
 $('csv').onclick=()=>{window.location.href=`/api/rooms/${room}/results.csv?key=${encodeURIComponent(key)}`};
 $('start').onclick=()=>action('/start');$('pause').onclick=()=>action('/pause');$('resume').onclick=()=>action('/resume');
 $('end').onclick=()=>action('/end','Kết thúc cuộc đua ngay bây giờ? Các sinh viên chưa về đích sẽ không thể trả lời tiếp.');
 $('reset').onclick=()=>action('/reset','Thi lại từ đầu? Tiến độ, thời gian và số câu sai hiện tại sẽ bị xóa. Hãy tải kết quả CSV trước nếu cần.');
 render(latest); connect();
 setInterval(()=>{if(latest && latest.phase==='running')$('s-time').textContent=formatTime(latest.elapsed+(Date.now()-lastSyncAt)/1000)},500);
}
function copy(text,msg){
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(()=>message(msg)).catch(()=>fallbackCopy(text,msg))}
 else fallbackCopy(text,msg);
}
function fallbackCopy(text,msg){const ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.top='0';document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();message(msg)}
function formatTime(seconds){let s=Math.floor(Math.max(0,seconds));return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`}
// Stable, distinct color per registered learner; independent of changing rank.
const starterColors=['#198f7c','#c4556f','#4b7fbf','#bd8731','#8b65bb','#198fa5','#bd6575','#6f902c','#d06c40','#5867c2','#3a9470','#b5529a'];
function colorFor(index){
 index=Math.max(0,Number(index)||0);
 if(index<starterColors.length)return starterColors[index];
 const hue=((index*137.50776405+24)%360).toFixed(2);
 return `hsl(${hue} 66% ${37+(Math.floor(index/12)%3)*7}%)`;
}
function makeNode(tag,cls,text){const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;return el}
function updateRacer(el,p,rank,total){
 el.style.setProperty('--racer-color',colorFor(p.colorIndex));
 el.querySelector('.racer-rank').textContent=String(rank).padStart(2,'0');
 el.querySelector('.racer-name').textContent=p.name;
 el.querySelector('.racer-dot').style.background='var(--racer-color)';
 el.querySelector('.racer-small').textContent=`${p.mistakes} lần sai · ${p.progress}/${total} câu đúng`;
 const track=el.querySelector('.track');
 if(track.children.length!==total){track.replaceChildren(...Array.from({length:total},()=>makeNode('span','')))}
 [...track.children].forEach((piece,i)=>piece.classList.toggle('done',i<p.progress));
 track.setAttribute('role','progressbar');track.setAttribute('aria-label','Tiến độ '+p.name);
 track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax',String(total));track.setAttribute('aria-valuenow',String(p.progress));
 el.querySelector('.finish').textContent=p.finishSeconds!==null?'🏁 '+formatTime(p.finishSeconds):p.locked?'⏳ 3s':p.progress+'/'+total;
}
function renderRaces(players,total){
 const host=$('races');host.className=players.length?'':'empty';
 if(!players.length){host.textContent='Chưa có sinh viên nào vào phòng.';return}
 const previous=new Map();const heights=new Map();
 for(const el of [...host.children])if(el.dataset.playerId){previous.set(el.dataset.playerId,el);heights.set(el.dataset.playerId,el.getBoundingClientRect().top)}
 const fragment=document.createDocumentFragment();
 players.forEach((p,i)=>{
  let row=previous.get(p.id);
  if(!row){
   row=makeNode('div','racer');row.dataset.playerId=p.id;
   const info=makeNode('div','racer-info'),nameLine=makeNode('div','racer-name-line');
   nameLine.append(makeNode('span','racer-rank'),makeNode('span','racer-dot'),makeNode('span','racer-name'));
   info.append(nameLine,makeNode('div','racer-small'));
   row.append(info,makeNode('div','track'),makeNode('div','finish'));
  }
  updateRacer(row,p,i+1,total);fragment.append(row);
 });
 host.replaceChildren(fragment);
 if(heights.size)requestAnimationFrame(()=>{
  [...host.children].forEach(row=>{const old=heights.get(row.dataset.playerId);if(old===undefined)return;
   const delta=old-row.getBoundingClientRect().top;
   if(Math.abs(delta)>3&&row.animate)row.animate([{transform:`translateY(${delta}px)`},{transform:'translateY(0px)'}],{duration:420,easing:'cubic-bezier(.2,.7,.2,1)'});
  });
 });
}
function render(data){
 latest=data;lastSyncAt=Date.now();
 $('phase').textContent=phaseNames[data.phase]||data.phase;
 $('phase').className='pill'+(data.phase==='running'?'':data.phase==='paused'?' orange':data.phase==='ended'?' red':'');
 $('s-players').textContent=data.players.length; $('s-finish').textContent=data.finishedCount;$('s-time').textContent=formatTime(data.elapsed);
 $('start').disabled= data.phase!=='lobby'||data.players.length===0;
 $('start').classList.toggle('hidden',data.phase!=='lobby');
 $('pause').classList.toggle('hidden',data.phase!=='running');
 $('resume').classList.toggle('hidden',data.phase!=='paused');
 $('end').disabled= !['running','paused'].includes(data.phase);
 renderRaces(data.players, data.total);
 if(data.phase==='lobby')message('Phòng đã sẵn sàng. Đợi sinh viên tham gia và nhấn Bắt đầu.');
 else if(data.phase==='running')message('Đang đua. Tiến độ sẽ tự cập nhật khi các em trả lời đúng.');
 else if(data.phase==='paused')message('Đã tạm dừng. Đồng hồ và câu hỏi của sinh viên được đóng băng.');
 else message('Cuộc đua đã kết thúc. Bạn có thể tải kết quả CSV.');
}
function connect(){
 if(socket)socket.close();
 const protocol=location.protocol==='https:'?'wss':'ws';
 socket=new WebSocket(`${protocol}://${location.host}/ws/${encodeURIComponent(room)}?role=teacher&key=${encodeURIComponent(key)}`);
 socket.onopen=()=>{$('conn-txt').textContent='Trực tuyến';$('conn-dot').classList.remove('offline')};
 socket.onmessage=event=>{try{render(JSON.parse(event.data))}catch(e){console.error(e)}};
 socket.onclose=()=>{$('conn-txt').textContent='Đang nối lại';$('conn-dot').classList.add('offline');setTimeout(()=>{if(room)connect()},2500)};
}
$('create').addEventListener('click',async()=>{
 $('create').disabled=true; $('create').textContent='Đang tạo phòng...';
 try{const res=await fetch('/api/rooms',{method:'POST'});const data=await res.json();if(!res.ok)throw Error(data.detail||'Lỗi tạo phòng');room=data.code;key=data.key;history.replaceState({},'',`/teacher?room=${encodeURIComponent(room)}&key=${encodeURIComponent(key)}`);await init()}
 catch(e){$('create-error').textContent=e.message;$('create-error').classList.remove('hidden')}
 finally{$('create').disabled=false;$('create').textContent='＋ Tạo phòng đua mới'}
});
init();
