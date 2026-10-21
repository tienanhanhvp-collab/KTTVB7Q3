'use strict';
const $ = x => document.getElementById(x);
const room = decodeURIComponent(location.pathname.split('/').pop()).toUpperCase();
const savedKey = `vocab-race:${room}`;
let token=localStorage.getItem(savedKey)||'';
let socket=null, state=null, busy=false, feedback='', lastQuestion='', lastSync=Date.now();
const sections=['join','waiting','playing','paused','finished','ended'];
function show(id){for(const x of sections)$(x).classList.toggle('hidden',x!==id)}
function fmt(s){s=Math.max(0,Math.floor(s));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
async function api(route,opts={}){const res=await fetch(`/api/rooms/${encodeURIComponent(room)}${route}`,opts);const data=await res.json();if(!res.ok)throw Error(data.detail||'Có lỗi xảy ra.');return data}
function render(s){
 state=s;lastSync=Date.now();if(typeof s.lockRemainingMs==='number')s.lockUntil=Date.now()+s.lockRemainingMs;
 if(s.phase==='lobby'){show('waiting');$('my-name').textContent=s.name;$('my-code').textContent=s.code;return}
 if(s.finishSeconds!==null){show('finished');$('rank').textContent=s.rank?`Hạng ${s.rank}`:'Đã hoàn thành';$('final-stats').textContent=`Hoàn thành 20 câu trong ${fmt(s.finishSeconds)}, với ${s.mistakes} lần trả lời sai.`;return}
 if(s.phase==='paused'){show('paused');return}
 if(s.phase==='ended'){show('ended');$('ended-text').textContent=`Bạn đã hoàn thành ${s.progress}/20 câu; ${s.mistakes} lần trả lời sai.`;return}
 if(s.phase!=='running'){show('waiting');return}
 show('playing');$('q-count').textContent=`Câu ${s.progress+1} / ${s.total}`;$('progress-bar').style.width=(s.progress/s.total*100)+'%';$('progress-num').textContent=`${s.progress} / ${s.total} câu đúng`;
 const q=s.question;
 if(q){
  const id=`${s.progress}:${q.id}`;
  if(id!==lastQuestion){
   lastQuestion=id;feedback='';busy=false;
   $('q-type').textContent=q.direction==='ko-vi'?'Chọn nghĩa tiếng Việt chính xác':'Chọn từ tiếng Hàn chính xác';
   $('q-prompt').textContent=q.prompt;
   $('q-prompt').classList.toggle('vietnamese',q.direction==='vi-ko');
   $('answers').innerHTML='';
   q.options.forEach((option,i)=>{const btn=document.createElement('button');btn.className='answer';btn.type='button';btn.innerHTML=`<span class="letter">${'ABCD'[i]}</span><span class="answer-text"></span>`;btn.querySelector('.answer-text').textContent=option;btn.addEventListener('click',()=>submit(i,q.id));$('answers').appendChild(btn)});
  }
 }
 updateCountdown();
}
async function submit(choice,question_id){
 if(!state || state.phase!=='running'||busy||Date.now()<state.lockUntil)return;
 busy=true;setButtons();
 try{
  const result=await api('/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,choice,question_id})});
  if(result.correct){feedback='✓ Chính xác! Tiến thêm một bước.';setStatus(feedback,false);await refresh()}
  else{feedback='✕ Chưa đúng. Chờ 3 giây để thử lại.';state.lockUntil=Date.now()+result.waitMs;setStatus(feedback,true)}
 }catch(err){feedback=err.message;setStatus(feedback,true);await refresh()}
 finally{busy=false;setButtons()}
}
function setStatus(t,bad){$('answer-status').textContent=t;$('answer-status').classList.toggle('bad',bad)}
function setButtons(){const lock=!!state && Date.now()<state.lockUntil;document.querySelectorAll('.answer').forEach(x=>x.disabled=busy||lock||state?.phase!=='running')}
function updateCountdown(){
 if(!state||state.phase!=='running')return;
 const rem=state.lockUntil-Date.now();
 if(rem>0){setStatus(`✕ Sai rồi! Bạn có thể thử lại sau ${Math.ceil(rem/1000)} giây.`,true)}
 else if(feedback.startsWith('✕')){setStatus('Đã hết thời gian chờ. Chọn đáp án khác nhé!',false)}
 else if(feedback){setStatus(feedback,false)}
 else setStatus('Chọn một phương án để tiến lên!',false);
 setButtons();
 $('q-timer').textContent=fmt(state.elapsed+(Date.now()-lastSync)/1000);
}
async function refresh(){if(!token)return;try{const s=await api('/student?token='+encodeURIComponent(token));render(s)}catch(err){if(/không hợp lệ|Không tìm thấy/.test(err.message)){localStorage.removeItem(savedKey);token='';show('join');$('join-error').textContent=err.message;$('join-error').classList.remove('hidden')}}}
function connect(){
 if(!token)return;if(socket)socket.close();
 const proto=location.protocol==='https:'?'wss':'ws';
 socket=new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(room)}?role=student&token=${encodeURIComponent(token)}`);
 socket.onopen=()=>{$('conn-txt').textContent='Đang trực tuyến';$('conn-dot').classList.remove('offline')};
 socket.onmessage=e=>{try{render(JSON.parse(e.data))}catch(err){console.error(err)}};
 socket.onclose=()=>{$('conn-txt').textContent='Mất kết nối · đang thử lại';$('conn-dot').classList.add('offline');setTimeout(()=>{if(token)connect()},2800)};
}
$('join-form').addEventListener('submit',async e=>{e.preventDefault();const name=$('name').value.trim();if(!name)return;$('join-btn').disabled=true;try{const info=await api('/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});token=info.token;localStorage.setItem(savedKey,token);$('join-error').classList.add('hidden');await refresh();connect()}catch(err){$('join-error').textContent=err.message;$('join-error').classList.remove('hidden')}finally{$('join-btn').disabled=false}});
setInterval(()=>{updateCountdown(); if(socket?.readyState===1){socket.send('ping')}},700);
if(token){refresh().then(()=>{if(token)connect()})}
