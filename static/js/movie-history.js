(function(){'use strict';
var AH='78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799',SK='mh_unlocked',DB='mh_db',TOKEN_KEY='mh_gh_token',
GH_OWNER='banhang-chogao',GH_REPO='reviewchanthat',GH_PATH='data/movie-history.json',GH_BRANCH='main';

var S={movies:[],filtered:[],currentWeekStart:null,searchQuery:'',filterStatus:'all',editingId:null};

function sha(s){var b=new TextEncoder().encode(s);return crypto.subtle.digest('SHA-256',b).then(function(h){var x='',u=new Uint8Array(h);for(var i=0;i<u.length;i++)x+=u[i].toString(16).padStart(2,'0');return x})}

function gId(){return Date.now().toString(36)+Math.random().toString(36).slice(2,10)}

function getGHReadURL(){return 'https://raw.githubusercontent.com/'+GH_OWNER+'/'+GH_REPO+'/'+GH_BRANCH+'/'+GH_PATH+'?_='+Date.now()}
function getGHAPIURL(){return 'https://api.github.com/repos/'+GH_OWNER+'/'+GH_REPO+'/contents/'+GH_PATH}

function getToken(){return localStorage.getItem(TOKEN_KEY)||''}
function setToken(t){if(t){localStorage.setItem(TOKEN_KEY,t)}else{localStorage.removeItem(TOKEN_KEY)}}

function loadMovies(){var url=getGHReadURL();return fetch(url,{cache:'no-cache'}).then(function(r){if(r.status===404)return{movies:[]};if(!r.ok)throw new Error('Read failed: '+r.status);return r.json()}).then(function(d){S.movies=Array.isArray(d.movies)?d.movies:[];rW();uC();rL()})['catch'](function(e){console.warn('Load failed:',e);S.movies=[];rW();uC();rL()})}

function saveMovies(){var token=getToken();if(!token){alert('Cần nhập GitHub token để lưu.');sT();return}var data={movies:S.movies,updatedAt:new Date().toISOString()};var apiUrl=getGHAPIURL();var json=JSON.stringify(data,null,2)+'\n';var content=btoa(unescape(encodeURIComponent(json)));return fetch(apiUrl,{headers:{'Accept':'application/vnd.github.v3+json'}}).then(function(r){if(r.status===404)return null;if(!r.ok)throw new Error('Get SHA failed: '+r.status);return r.json()}).then(function(existing){var body={message:'movie-history: save '+S.movies.length+' movies',content:content,branch:GH_BRANCH};if(existing)body.sha=existing.sha;return fetch(apiUrl,{method:'PUT',headers:{'Authorization':'token '+token,'Content-Type':'application/json','Accept':'application/vnd.github.v3+json'},body:JSON.stringify(body)})}).then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error('GitHub write failed: '+(e.message||r.status))});return r.json()})}

function sT(){var t=prompt('Nhập GitHub Personal Access Token (cần quyền contents write):',getToken());if(t!==null){setToken(t.trim());if(t.trim())alert('Token đã lưu.')}}

function iG(){var g=document.getElementById('mhGate'),a=document.getElementById('mhApp'),i=document.getElementById('mhGateInput'),b=document.getElementById('mhGateUnlock'),e=document.getElementById('mhGateError'),ac=0,la=0;if(sessionStorage.getItem(SK)==='1'){g.style.display='none';a.style.display='';aU();return}function dU(){var c=i.value.trim();if(!c||c.length!==4){e.textContent='Please enter all 4 digits.';return}var n=Date.now();if(n-la<2000){e.textContent='Too fast. Wait 2 seconds.';return}la=n;ac++;if(ac>5){e.textContent='Too many attempts. Reload to retry.';b.disabled=true;i.disabled=true;return}sha(c).then(function(h){if(h===AH){sessionStorage.setItem(SK,'1');g.style.display='none';a.style.display='';aU()}else{e.textContent='Wrong code. '+(5-ac)+' attempts left.';i.value='';i.focus()}})}b.addEventListener('click',dU);i.addEventListener('keydown',function(e){if(e.key==='Enter')dU()});i.focus()}

function aU(){loadMovies()}

function rW(){var now=new Date();S.currentWeekStart=S.currentWeekStart||getWeekStart(now);uW();uC()}

function uW(){var ws=S.currentWeekStart,we=getWeekEnd(ws),wn=getWeekNumber(ws);document.getElementById('mhWeekLabel').textContent='Week '+wn+' ('+ws.getFullYear()+') — '+formatDateVi(ws)+' — '+formatDateVi(we)}

function uC(){var cal=document.getElementById('mhCalendar'),ws=S.currentWeekStart;var cells=cal.querySelectorAll('.mh-calendar__day');cells.forEach(function(c){c.remove()});for(var i=0;i<7;i++){var d=new Date(ws);d.setDate(d.getDate()+i);var ds=getISODate(d);var cell=document.createElement('div');cell.className='mh-calendar__day';cell.dataset.date=ds;var now=new Date(),td=getISODate(now);if(ds===td)cell.classList.add('mh-calendar__day--today');var dayMovies=S.movies.filter(function(m){return m.date===ds});if(dayMovies.length>0){cell.classList.add('mh-calendar__day--has-movie');var emoji=document.createElement('span');emoji.className='mh-calendar__emoji';var statusEmojis={upcoming:'📅',watching:'▶️',watched:'✅'};emoji.textContent=dayMovies.length<=3?dayMovies.map(function(m){return statusEmojis[m.status]||'🎬'}).join(''):'🎬×'+dayMovies.length;cell.appendChild(emoji)}var dateEl=document.createElement('span');dateEl.className='mh-calendar__date';dateEl.textContent=d.getDate();cell.appendChild(dateEl);cell.addEventListener('click',function(){var ds=this.dataset.date;var dayMovies=S.movies.filter(function(m){return m.date===ds});if(dayMovies.length>0){document.getElementById('mhSearch').value='';S.filterStatus='all';document.getElementById('mhFilter').value='all';S.searchQuery='';aF();rL();var cards=document.querySelectorAll('.mh-movie-card');cards.forEach(function(c){if(c.dataset.date!==ds)c.style.display='none'});window.scrollTo({top:document.querySelector('.mh-movie-list').offsetTop-100,behavior:'smooth'})}});cal.appendChild(cell)}}

document.getElementById('mhPrevWeek').addEventListener('click',function(){var ws=new Date(S.currentWeekStart);ws.setDate(ws.getDate()-7);S.currentWeekStart=ws;uW();uC();rL()});
document.getElementById('mhNextWeek').addEventListener('click',function(){var ws=new Date(S.currentWeekStart);ws.setDate(ws.getDate()+7);S.currentWeekStart=ws;uW();uC();rL()});

function aF(){var f=S.movies.slice(),q=S.searchQuery.toLowerCase();if(S.filterStatus!=='all')f=f.filter(function(m){return m.status===S.filterStatus});if(q){f=f.filter(function(m){return(m.title||'').toLowerCase().indexOf(q)!==-1||(m.summary||'').toLowerCase().indexOf(q)!==-1||(m.specials||[]).some(function(s){return s.toLowerCase().indexOf(q)!==-1})})}f.sort(function(a,b){return(b.year||0)-a.year||(b.rating||0)-a.rating});S.filtered=f}

document.getElementById('mhSearch').addEventListener('input',function(){S.searchQuery=this.value.trim();aF();rL()});
document.getElementById('mhFilter').addEventListener('change',function(){S.filterStatus=this.value;aF();rL()});
document.getElementById('mhAddBtn').addEventListener('click',function(){oS()});
document.getElementById('mhTokenBtn').addEventListener('click',function(){sT()});

function rL(){var list=document.getElementById('mhMovieList'),loading=document.getElementById('mhLoading');loading.style.display='none';list.innerHTML='';var movies=S.filtered;if(!movies||movies.length===0){list.innerHTML='<div class="mh-empty"><div class="mh-empty__icon">🎬</div><p class="mh-empty__text">No movies found</p><p class="mh-empty__sub">Add your first movie by clicking "＋ Add Movie".</p></div>';return}for(var i=0;i<movies.length;i++){var m=movies[i];var card=document.createElement('div');card.className='mh-movie-card';card.dataset.date=m.date||'';card.innerHTML=rC(m);list.appendChild(card)}}function rC(m){var rating='',specials='',statusClass='mh-movie-card__status--'+(m.status||'upcoming'),statusLabels={upcoming:'📅 Upcoming',watching:'▶ Watching',watched:'✅ Watched'};for(var i=0;i<5;i++){rating+='<span class="mh-form__star'+(i<(m.rating||0)?' mh-form__star--active':'')+'">★</span>'}if(m.specials&&m.specials.length>0){specials='<div class="mh-specials">'+m.specials.map(function(s){return'<span class="mh-special">'+es(s)+'</span>'}).join('')+'</div>'}var meta='<span>'+(m.year||'—')+'</span><span class="mh-movie-card__rating">'+rating+'</span>';return'<div class="mh-movie-card__top"><div class="mh-movie-card__poster mh-movie-card__poster--empty">🎬</div><div class="mh-movie-card__info"><h3 class="mh-movie-card__title">'+es(m.title||'Untitled')+'</h3><div class="mh-movie-card__meta">'+meta+'</div>'+(specials?'<div class="mh-movie-card__specials">'+specials+'</div>':'')+(m.summary?'<p class="mh-movie-card__summary">'+es(m.summary)+'</p>':'')+'</div></div><div class="mh-movie-card__bottom"><span class="mh-movie-card__status '+statusClass+'">'+(statusLabels[m.status]||'📅 Upcoming')+'</span><div class="mh-movie-card__actions"><button class="mh-movie-card__action" data-edit="'+m.id+'">✏ Edit</button><button class="mh-movie-card__action mh-movie-card__action--danger" data-delete="'+m.id+'">🗑 Delete</button></div></div>'}

document.getElementById('mhMovieList').addEventListener('click',function(e){var t=e.target;if(t.dataset.edit){var m=S.movies.find(function(x){return x.id===t.dataset.edit});if(m)oS(m)}else if(t.dataset.delete){if(!confirm('Delete "'+(S.movies.find(function(x){return x.id===t.dataset.delete})||{}).title+'"?'))return;S.movies=S.movies.filter(function(x){return x.id!==t.dataset.delete});var btn=document.getElementById('mhSaveStatus');if(btn){btn.textContent='Saving...';btn.style.display=''}saveMovies().then(function(){if(btn){btn.textContent='Saved ✅';setTimeout(function(){btn.style.display='none'},3000)}aF();rL();uC()})['catch'](function(err){alert('Save failed: '+err.message);aF();rL();uC()})}});

function oS(m){var ov=document.getElementById('mhOverlay'),title=document.getElementById('mhModalTitle'),id=document.getElementById('mhEditId'),fTitle=document.getElementById('mhFormTitle'),fYear=document.getElementById('mhFormYear'),fSummary=document.getElementById('mhFormSummary'),saveBtn=document.getElementById('mhFormSave');S.editingId=m?m.id:null;if(m){title.textContent='Edit Movie';id.value=m.id;fTitle.value=m.title;fYear.value=m.year||'';fSummary.value=m.summary||'';setStars(m.rating||0);setStatus(m.status||'watching');setSpecials(m.specials||[])}else{title.textContent='Add Movie';id.value='';fTitle.value='';fYear.value='';fSummary.value='';setStars(0);setStatus('watching');setSpecials([])}saveBtn.textContent=m?'💾 Update':'💾 Save';ov.style.display=''}

document.getElementById('mhModalClose').addEventListener('click',function(){document.getElementById('mhOverlay').style.display='none'});
document.getElementById('mhFormCancel').addEventListener('click',function(){document.getElementById('mhOverlay').style.display='none'});
document.getElementById('mhOverlay').addEventListener('click',function(e){if(e.target===this)this.style.display='none'});

document.getElementById('mhForm').addEventListener('submit',function(e){e.preventDefault();var title=document.getElementById('mhFormTitle').value.trim();if(!title){alert('Movie title is required.');return}var year=parseInt(document.getElementById('mhFormYear').value,10)||null;var summary=document.getElementById('mhFormSummary').value.trim();var rating=S._selectedRating||0;var status=S._selectedStatus||'watching';var specials=S._selectedSpecials||[];var editId=S.editingId;if(editId){var idx=S.movies.findIndex(function(x){return x.id===editId});if(idx!==-1){S.movies[idx]={id:editId,title:title,year:year,rating:rating,status:status,summary:summary,specials:specials,date:S.movies[idx].date,created:S.movies[idx].created,updated:Date.now()}}}else{var now=new Date();var ws=S.currentWeekStart;var we=getWeekEnd(ws);var midDate=new Date(ws);midDate.setDate(midDate.getDate()+3);S.movies.push({id:gId(),title:title,year:year,rating:rating,status:status,summary:summary,specials:specials,date:getISODate(midDate),created:Date.now(),updated:Date.now()})}document.getElementById('mhOverlay').style.display='none';var btn=document.getElementById('mhSaveStatus');if(btn){btn.textContent='Saving...';btn.style.display=''}saveMovies().then(function(){if(btn){btn.textContent='Saved ✅ Commit pushed';setTimeout(function(){btn.style.display='none'},4000)}aF();rL();uC()})['catch'](function(err){alert('Save failed: '+err.message+'\nPlease try again.')})});

var stars=document.querySelectorAll('#mhFormStars .mh-form__star');
stars.forEach(function(s){s.addEventListener('click',function(){var v=parseInt(this.dataset.value,10);setStars(v)})});
function setStars(v){S._selectedRating=v;stars.forEach(function(s){s.classList.toggle('mh-form__star--active',parseInt(s.dataset.value,10)<=v)})}

var statusOpts=document.querySelectorAll('#mhFormStatus .mh-form__status-option');
statusOpts.forEach(function(s){s.addEventListener('click',function(){setStatus(this.dataset.value)})});
function setStatus(v){S._selectedStatus=v;statusOpts.forEach(function(s){s.classList.toggle('mh-form__status-option--active',s.dataset.value===v)})}

var specialChips=document.querySelectorAll('#mhFormSpecials .mh-form__special');
specialChips.forEach(function(s){s.addEventListener('click',function(){var v=this.dataset.value;if(!S._selectedSpecials)S._selectedSpecials=[];var idx=S._selectedSpecials.indexOf(v);if(idx!==-1){S._selectedSpecials.splice(idx,1);this.classList.remove('mh-form__special--active')}else{S._selectedSpecials.push(v);this.classList.add('mh-form__special--active')}})});
function setSpecials(v){S._selectedSpecials=v||[];specialChips.forEach(function(s){s.classList.toggle('mh-form__special--active',(v||[]).indexOf(s.dataset.value)!==-1)})}

function getISODate(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function getWeekStart(d){var dt=new Date(d);dt.setDate(dt.getDate()-dt.getDay()+(dt.getDay()===0?-6:1));dt.setHours(0,0,0,0);return dt}
function getWeekEnd(ws){var we=new Date(ws);we.setDate(we.getDate()+6);return we}
function formatDateVi(d){var days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];return days[d.getDay()===0?6:d.getDay()-1]+' '+d.getDate()+'/'+(d.getMonth()+1)+'/'+d.getFullYear()}
function getWeekNumber(d){var dt=new Date(d);dt.setHours(0,0,0,1);var ws=new Date(dt);ws.setDate(ws.getDate()-((ws.getDay()||7)-1));var ysw=new Date(ws.getFullYear(),0,1);return Math.ceil(((ws-ysw)/86400000+ysw.getDay()+1)/7)}
function es(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function lV(){var BASE=(document.body&&document.body.getAttribute('data-site-base'))||'';fetch(BASE.replace(/\/$/,'')+'/build-info.json').then(function(r){if(!r.ok)return null;return r.json()})['catch'](function(){return null}).then(function(info){var el=document.getElementById('mhVersionBadge');if(!el)return;if(!info){el.textContent='v1.0-dev';return}el.textContent='v1.0-'+info.short_sha})}
iG();lV();
})();
