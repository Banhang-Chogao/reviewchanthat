(function(){'use strict';
var AH='78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799',SK='mh_unlocked',DB='mh_db',TOKEN_KEY='mh_gh_token',
GH_OWNER='banhang-chogao',GH_REPO='reviewchanthat',GH_PATH='data/movie-history.json',GH_BRANCH='main';

var S={movies:[],filtered:[],currentMonthStart:null,searchQuery:'',filterStatus:'all',editingId:null,_pendingDate:null,_selectedMovie:null,_view:'calendar',_nextUpId:null};
var MAX_MOVIES_PER_DAY=10;
var STATUS_MAP={watching:{key:'watching',label:'Watching',emoji:'🟢',color:'#4caf50'},'coming-soon':{key:'coming-soon',label:'Coming Soon',emoji:'🔵',color:'#2196f3'},'need-ticket':{key:'need-ticket',label:'Need Ticket',emoji:'🟡',color:'#ff9800'},waiting:{key:'waiting',label:'Waiting',emoji:'🟠',color:'#ff5722'},'sold-out':{key:'sold-out',label:'Sold Out',emoji:'🔴',color:'#f44336'},cancelled:{key:'cancelled',label:'Cancelled',emoji:'⚫',color:'#9e9e9e'}};
var STATUS_LEGACY={upcoming:'coming-soon',watched:'sold-out'};

function getStatus(s){return STATUS_MAP[s]||STATUS_MAP[STATUS_LEGACY[s]]||STATUS_MAP['coming-soon']}
function sha(s){var b=new TextEncoder().encode(s);return crypto.subtle.digest('SHA-256',b).then(function(h){var x='',u=new Uint8Array(h);for(var i=0;i<u.length;i++)x+=u[i].toString(16).padStart(2,'0');return x})}
function gId(){return Date.now().toString(36)+Math.random().toString(36).slice(2,10)}
function getGHReadURL(){return 'https://raw.githubusercontent.com/'+GH_OWNER+'/'+GH_REPO+'/'+GH_BRANCH+'/'+GH_PATH+'?_='+Date.now()}
function getGHAPIURL(){return 'https://api.github.com/repos/'+GH_OWNER+'/'+GH_REPO+'/contents/'+GH_PATH}
function getToken(){return localStorage.getItem(TOKEN_KEY)||''}
function setToken(t){if(t){localStorage.setItem(TOKEN_KEY,t)}else{localStorage.removeItem(TOKEN_KEY)}}

function loadMovies(){var url=getGHReadURL();return fetch(url,{cache:'no-cache'}).then(function(r){if(r.status===404)return{movies:[]};if(!r.ok)throw new Error('Read failed: '+r.status);return r.json()}).then(function(d){S.movies=Array.isArray(d.movies)?d.movies.map(function(m){m.status=STATUS_LEGACY[m.status]||m.status;return m}):[];aF();rM();uC();showIdleList();refreshExtras()})['catch'](function(e){console.warn('Load failed:',e);S.movies=[];aF();rM();uC();showIdleList();refreshExtras()})}

function saveMovies(){var token=getToken();if(!token){alert('Cần nhập GitHub token để lưu.');sT();return Promise.reject('No token')}return sR(2)}
function sR(retries){var token=getToken();var data={movies:S.movies,updatedAt:new Date().toISOString()};var json=JSON.stringify(data,null,2)+'\n';var content=btoa(unescape(encodeURIComponent(json)));var pb=document.getElementById('mhProgressBar'),pf=document.getElementById('mhProgressFill'),ps=document.getElementById('mhProgressStage'),psha=document.getElementById('mhProgressSha');function ss(icon,text,pct){if(!ps)return;ps.innerHTML='<span class="mh-progress-bar__icon">'+icon+'</span><span class="mh-progress-bar__text">'+text+'</span>';if(pf)pf.style.width=pct+'%'}if(pb)pb.style.display='';if(psha)psha.textContent='';if(pf){pf.style.background='';pf.style.width='0%'}ss('🔍','Đang kết nối GitHub...',20);var apiUrl=getGHAPIURL();return fetch(apiUrl,{headers:{'Accept':'application/vnd.github.v3+json'}}).then(function(r){if(r.status===404)return null;if(!r.ok)throw new Error('Get SHA failed: '+r.status);return r.json()}).then(function(existing){ss('📤','Đang đẩy dữ liệu lên GitHub ('+S.movies.length+' phim)...',55);var body={message:'movie-history: save '+S.movies.length+' movies',content:content,branch:GH_BRANCH};if(existing)body.sha=existing.sha;return fetch(apiUrl,{method:'PUT',headers:{'Authorization':'token '+token,'Content-Type':'application/json','Accept':'application/vnd.github.v3+json'},body:JSON.stringify(body)})}).then(function(r){if(!r.ok)return r.json().then(function(e){if(e.message&&e.message.indexOf('does not match')!==-1&&retries>0)return sR(retries-1);throw new Error('GitHub write failed: '+(e.message||r.status))});return r.json()}).then(function(res){ss('✅','Lưu thành công!',100);var sha=(res&&res.content&&res.content.sha)||'';if(sha&&psha)psha.textContent='Commit: '+sha.slice(0,7);if(pb)setTimeout(function(){pb.style.display='none'},1800);hSC()})['catch'](function(err){ss('❌','Lỗi: '+err.message,100);if(pf)pf.style.background='var(--mh-red,#e74c3c)';if(pb)setTimeout(function(){pb.style.display='none';if(pf)pf.style.background=''},5000);throw err})}

function sT(){var t=prompt('Nhập GitHub Personal Access Token (cần quyền contents write):',getToken());if(t!==null){setToken(t.trim());if(t.trim())alert('Token đã lưu.')}}

function iG(){var g=document.getElementById('mhGate'),a=document.getElementById('mhApp'),i=document.getElementById('mhGateInput'),b=document.getElementById('mhGateUnlock'),e=document.getElementById('mhGateError'),ac=0,la=0;if(sessionStorage.getItem(SK)==='1'){g.style.display='none';a.style.display='';aU();return}function dU(){var c=i.value.trim();if(!c||c.length!==4){e.textContent='Please enter all 4 digits.';return}var n=Date.now();if(n-la<2000){e.textContent='Too fast. Wait 2 seconds.';return}la=n;ac++;if(ac>5){e.textContent='Too many attempts. Reload to retry.';b.disabled=true;i.disabled=true;return}sha(c).then(function(h){if(h===AH){sessionStorage.setItem(SK,'1');g.style.display='none';a.style.display='';aU()}else{e.textContent='Wrong code. '+(5-ac)+' attempts left.';i.value='';i.focus()}})}b.addEventListener('click',dU);i.addEventListener('keydown',function(e){if(e.key==='Enter')dU()});i.focus()}

function aU(){loadMovies()}
// Calendar-first UX: only show movie details when user selects a day/cell with data
function clearDaySelection(){var sel=document.querySelectorAll('.mh-calendar__day--selected');sel.forEach(function(c){c.classList.remove('mh-calendar__day--selected')});S._pendingDate=null}
function markDaySelected(ds){var cal=document.getElementById('mhCalendar');if(!cal)return;var prev=cal.querySelectorAll('.mh-calendar__day--selected');prev.forEach(function(c){c.classList.remove('mh-calendar__day--selected')});var cell=cal.querySelector('.mh-calendar__day[data-date="'+ds+'"]');if(cell)cell.classList.add('mh-calendar__day--selected');S._pendingDate=ds}
function showIdleList(){var list=document.getElementById('mhMovieList'),loading=document.getElementById('mhLoading');if(loading)loading.style.display='none';if(!list)return;list.innerHTML='<div class="mh-empty mh-empty--idle"><div class="mh-empty__icon">📅</div><p class="mh-empty__text">Chọn ngày trên lịch để xem phim</p><p class="mh-empty__sub">Thêm phim bằng ＋ Add Movie, import Excel, hoặc chọn ngày có chip trên lịch. Next up & Year in review cập nhật tự động.</p></div>';hideSelectedPanel();S._pendingDate=null}
function showEmptyDay(ds){var list=document.getElementById('mhMovieList'),loading=document.getElementById('mhLoading');if(loading)loading.style.display='none';if(!list)return;var label=ds?formatDate(new Date(ds+'T00:00:00')):('ngày này');list.innerHTML='<div class="mh-empty mh-empty--idle"><div class="mh-empty__icon">📭</div><p class="mh-empty__text">Không có phim ngày '+es(label)+'</p><p class="mh-empty__sub">Chọn ngày khác có thẻ phim trên calendar, hoặc bấm ＋ Add Movie.</p></div>';hideSelectedPanel()}
function hideSelectedPanel(){var panel=document.getElementById('mhSelectedPanel');if(panel){panel.hidden=true;panel.classList.remove('is-open');panel.style.display=''}var sw=document.getElementById('mhPanelDaySwitch');if(sw){sw.hidden=true;sw.innerHTML=''}var main=document.querySelector('.mh-main');if(main)main.classList.remove('mh-main--detail');S._selectedMovie=null;document.querySelectorAll('.mh-movie-card--active').forEach(function(c){c.classList.remove('mh-movie-card--active')});document.querySelectorAll('.mh-event-card--active').forEach(function(c){c.classList.remove('mh-event-card--active')})}
function clearMovieList(){var list=document.getElementById('mhMovieList'),loading=document.getElementById('mhLoading');if(loading)loading.style.display='none';if(list)list.innerHTML=''}
/* Sibling chips live INSIDE the single detail card — never a second section */
function fillDayChips(ds,activeId){var host=document.getElementById('mhPanelDaySwitch');if(!host)return;var dm=S.movies.filter(function(m){return m.date===ds}).sort(function(a,b){if(a.time&&b.time)return a.time.localeCompare(b.time);if(a.time)return-1;if(b.time)return 1;return 0});if(dm.length<=1){host.hidden=true;host.innerHTML='';return}var html='<div class="mh-day-switch" role="tablist" aria-label="Phim trong ngày">';dm.forEach(function(m){var st=getStatus(m.status);var active=m.id===activeId?' mh-day-switch__chip--active':'';html+='<button type="button" class="mh-day-switch__chip'+active+'" role="tab" data-movie-id="'+m.id+'" data-date="'+ds+'" aria-selected="'+(m.id===activeId?'true':'false')+'"><span class="mh-day-switch__dot mh-day-switch__dot--'+st.key+'" aria-hidden="true"></span><span class="mh-day-switch__title">'+es(m.title||'Untitled')+'</span>'+(m.time?'<span class="mh-day-switch__time">'+es(m.time)+'</span>':'')+'</button>'});html+='</div>';host.innerHTML=html;host.hidden=false;host.querySelectorAll('.mh-day-switch__chip').forEach(function(btn){btn.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();selectCalendarDay(this.dataset.date,{force:true,movieId:this.dataset.movieId})})})}
function selectCalendarDay(ds,opts){opts=opts||{};if(!ds){clearDaySelection();showIdleList();return}if(!opts.force&&S._pendingDate===ds&&!opts.movieId){clearDaySelection();showIdleList();return}markDaySelected(ds);var dm=S.movies.filter(function(m){return m.date===ds});if(!dm.length){showEmptyDay(ds);return}
/* Selected movie => ONLY the unified detail card (list cleared). Multi without pick => compact list only. */
if(opts.movieId){var mv=S.movies.find(function(x){return x.id===opts.movieId});if(!mv){showEmptyDay(ds);return}clearMovieList();showSelectedMovie(mv);return}
if(dm.length===1){clearMovieList();showSelectedMovie(dm[0]);return}
hideSelectedPanel();filterByDate(ds)}
function autoSelectToday(){/* visual only — do not open details without explicit user click */}
function rM(){var now=new Date();if(!S.currentMonthStart)S.currentMonthStart=new Date(now.getFullYear(),now.getMonth(),1);uMLabel()}
function uMLabel(){var ms=S.currentMonthStart;var months=['January','February','March','April','May','June','July','August','September','October','November','December'];var el=document.getElementById('mhWeekLabel');if(el)el.textContent=months[ms.getMonth()]+' '+ms.getFullYear()}


function countMoviesOnDate(ds,excludeId){if(!ds)return 0;return S.movies.filter(function(m){return m.date===ds&&(!excludeId||m.id!==excludeId)}).length}
function enforceMaxMoviesPerDay(list,maxPerDay){maxPerDay=maxPerDay||MAX_MOVIES_PER_DAY;var byDate={},order=[],dropped=[];list.forEach(function(m){var d=m.date||'__none__';if(!byDate[d]){byDate[d]=[];order.push(d)}byDate[d].push(m)});var out=[];order.forEach(function(d){var arr=byDate[d].slice();if(d!=='__none__'){arr.sort(function(a,b){if(a.time&&b.time)return a.time.localeCompare(b.time);if(a.time)return-1;if(b.time)return 1;return String(a.title||'').localeCompare(String(b.title||''))});if(arr.length>maxPerDay){dropped=dropped.concat(arr.slice(maxPerDay).map(function(m){return{date:d,title:m.title||'Untitled'}}));arr=arr.slice(0,maxPerDay)}}out=out.concat(arr)});return{movies:out,dropped:dropped}}
function uC(){var cal=document.getElementById('mhCalendar');if(!cal)return;var olds=cal.querySelectorAll('.mh-calendar__day');olds.forEach(function(c){c.remove()});var ms=S.currentMonthStart;var fd=new Date(ms.getFullYear(),ms.getMonth(),1).getDay();var so=fd===0?6:fd-1;var dim=new Date(ms.getFullYear(),ms.getMonth()+1,0).getDate();for(var p=0;p<so;p++){var em=document.createElement('div');em.className='mh-calendar__day mh-calendar__day--empty';cal.appendChild(em)}for(var i=0;i<dim;i++){var d=new Date(ms.getFullYear(),ms.getMonth(),i+1);var ds=getISODate(d);var cell=document.createElement('div');cell.className='mh-calendar__day';cell.dataset.date=ds;var now=new Date(),td=getISODate(now);if(ds===td)cell.classList.add('mh-calendar__day--today');var dn=document.createElement('span');dn.className='mh-calendar__date';dn.textContent=d.getDate();cell.appendChild(dn);var dayMovies=S.movies.filter(function(m){return m.date===ds});if(dayMovies.length){var cnt=document.createElement('span');cnt.className='mh-calendar__count';cnt.textContent=dayMovies.length+'/'+MAX_MOVIES_PER_DAY;cnt.title=dayMovies.length+' phim (tối đa '+MAX_MOVIES_PER_DAY+'/ngày)';dn.appendChild(cnt)}dayMovies.sort(function(a,b){if(a.time&&b.time)return a.time.localeCompare(b.time);if(a.time)return-1;if(b.time)return 1;return 0});var maxV=MAX_MOVIES_PER_DAY,mc=0;if(dayMovies.length>0){cell.classList.add('mh-calendar__day--has-movies')}if(dayMovies.length>=4){cell.classList.add('mh-calendar__day--packed')}if(dayMovies.length>=7){cell.classList.add('mh-calendar__day--dense')}cell.dataset.count=String(dayMovies.length);dayMovies.forEach(function(m,idx){if(idx>=maxV){mc++;return}var card=document.createElement('div');var st=getStatus(m.status);card.className='mh-event-card mh-event-card--'+st.key;card.dataset.movieId=m.id;var urg=daysUntilMovie(m);if(urg===0)card.classList.add('mh-event-card--today');else if(urg!==null&&urg>=0&&urg<=2)card.classList.add('mh-event-card--urgent');var row1=document.createElement('div');row1.className='mh-event-card__row';var dot=document.createElement('span');dot.className='mh-event-dot mh-event-dot--'+st.key;row1.appendChild(dot);var ts=document.createElement('span');ts.className='mh-event-title';ts.textContent=m.title||'Untitled';row1.appendChild(ts);card.appendChild(row1);var metaBits=[];if(m.time)metaBits.push(m.time);if(m.cinema)metaBits.push(m.cinema);if(urg!==null&&urg>=0&&urg<=7)metaBits.push(urg===0?'Today':('D-'+urg));if(metaBits.length){var row2=document.createElement('div');row2.className='mh-event-card__row mh-event-card__row--meta';var meta=document.createElement('span');meta.className='mh-event-meta-line';meta.textContent=metaBits.join(' · ');row2.appendChild(meta);card.appendChild(row2)}card.addEventListener('click',function(e){e.stopPropagation();var mid=this.dataset.movieId;var ds=this.parentElement&&this.parentElement.dataset.date;if(ds)selectCalendarDay(ds,{force:true,movieId:mid});else{var mv=S.movies.find(function(x){return x.id===mid});if(mv){if(mv.date)selectCalendarDay(mv.date,{force:true,movieId:mid});else showSelectedMovie(mv)}}});cell.appendChild(card)});if(mc>0){var mo=document.createElement('div');mo.className='mh-event-more';mo.textContent='+'+mc+' more (max '+MAX_MOVIES_PER_DAY+'/day)';mo.addEventListener('click',function(e){e.stopPropagation();var ds=this.parentElement.dataset.date;selectCalendarDay(ds,{force:true})});cell.appendChild(mo)}cell.addEventListener('click',function(){selectCalendarDay(this.dataset.date)});cal.appendChild(cell)}}

function metaItem(icon,label,value){return'<div class="mh-detail__meta-item"><span class="mh-detail__meta-icon" aria-hidden="true">'+icon+'</span><div class="mh-detail__meta-body"><span class="mh-detail__meta-label">'+label+'</span><span class="mh-detail__meta-value">'+value+'</span></div></div>'}
function shareMovie(m){var lines=[m.title||'Untitled'];if(m.date)lines.push('📅 '+formatDate(new Date(m.date+'T00:00:00')));if(m.time)lines.push('🕒 '+m.time);if(m.cinema)lines.push('🎬 '+m.cinema);if(m.hall)lines.push('🎟 '+m.hall);var text=lines.join('\n');if(navigator.share){navigator.share({title:m.title||'Movie',text:text})['catch'](function(){})}else if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){alert('Copied movie details to clipboard.')})['catch'](function(){prompt('Copy movie details:',text)})}else{prompt('Copy movie details:',text)}}
function exportOneMovie(m){var blob=new Blob([JSON.stringify(m,null,2)],{type:'application/json'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=(m.title||'movie').replace(/[^\w\-]+/g,'_').slice(0,60)+'.json';a.click();URL.revokeObjectURL(url)}
function setupSynopsisCollapse(){var syn=document.getElementById('mhPanelSynopsis'),btn=document.getElementById('mhPanelReadMore');if(!syn||!btn)return;syn.classList.remove('is-expanded');btn.hidden=true;btn.setAttribute('aria-expanded','false');btn.textContent='Read more';requestAnimationFrame(function(){var needs=syn.scrollHeight>syn.clientHeight+4;if(needs){btn.hidden=false;btn.onclick=function(){var open=syn.classList.toggle('is-expanded');btn.setAttribute('aria-expanded',open?'true':'false');btn.textContent=open?'Show less':'Read more'}}})}
function showSelectedMovie(m){var panel=document.getElementById('mhSelectedPanel'),card=document.getElementById('mhDetailCard'),titleEl=document.getElementById('mhPanelTitle'),posterEl=document.getElementById('mhPanelPoster'),statusEl=document.getElementById('mhPanelStatus'),ratingEl=document.getElementById('mhPanelRating'),tagsEl=document.getElementById('mhPanelTags'),metaEl=document.getElementById('mhPanelMeta'),synWrap=document.getElementById('mhPanelSynopsisWrap'),synEl=document.getElementById('mhPanelSynopsis');if(!panel||!m)return;/* reuse single panel DOM — never create a second detail tree */S._selectedMovie=m;if(m.date){fillDayChips(m.date,m.id)}else{var _h=document.getElementById('mhPanelDaySwitch');if(_h){_h.hidden=true;_h.innerHTML=''}}document.querySelectorAll('.mh-movie-card--active').forEach(function(c){c.classList.remove('mh-movie-card--active')});document.querySelectorAll('.mh-event-card--active').forEach(function(c){c.classList.remove('mh-event-card--active')});var listCard=document.querySelector('.mh-movie-card[data-movie-id="'+m.id+'"]');if(listCard)listCard.classList.add('mh-movie-card--active');var evCard=document.querySelector('.mh-event-card[data-movie-id="'+m.id+'"]');if(evCard)evCard.classList.add('mh-event-card--active');if(m.date)markDaySelected(m.date);if(titleEl)titleEl.textContent=m.title||'Untitled';var st=getStatus(m.status);if(statusEl){statusEl.className='mh-detail__status mh-detail__status--'+st.key;statusEl.textContent=st.emoji+' '+st.label}var cdEl=document.getElementById('mhPanelCountdown');if(cdEl){var dLeft=daysUntilMovie(m);if(dLeft===null){cdEl.hidden=true;cdEl.textContent=''}else if(dLeft<0){cdEl.hidden=false;cdEl.className='mh-detail__countdown is-past';cdEl.textContent='Đã qua ' + Math.abs(dLeft) + ' ngày'}else if(dLeft===0){cdEl.hidden=false;cdEl.className='mh-detail__countdown is-urgent';cdEl.textContent='🔥 Hôm nay'+(m.time?(' · '+m.time):'')}else if(dLeft<=3){cdEl.hidden=false;cdEl.className='mh-detail__countdown is-urgent';cdEl.textContent='⚡ Còn '+dLeft+' ngày'+(m.time?(' · '+m.time):'')}else{cdEl.hidden=false;cdEl.className='mh-detail__countdown';cdEl.textContent='Còn '+dLeft+' ngày'}}if(ratingEl){if(m.rating&&m.rating>0){ratingEl.hidden=false;ratingEl.setAttribute('aria-label','Rating '+m.rating+' of 5');ratingEl.textContent='⭐'.repeat(m.rating)+'☆'.repeat(Math.max(0,5-m.rating))}else{ratingEl.hidden=true;ratingEl.textContent=''}}if(tagsEl){if(m.specials&&m.specials.length){tagsEl.hidden=false;tagsEl.innerHTML=m.specials.map(function(s){return'<span class="mh-detail__tag">'+es(s)+'</span>'}).join('')}else{tagsEl.hidden=true;tagsEl.innerHTML=''}}if(posterEl){posterEl.innerHTML='';if(m.posterUrl){var img=document.createElement('img');img.src=m.posterUrl;img.alt='';img.loading='lazy';img.onerror=function(){posterEl.textContent=m.emoji||'🎬'};posterEl.appendChild(img)}else{posterEl.textContent=m.emoji||'🎬'}}if(metaEl){var rows=[];if(m.date)rows.push(metaItem('📅','Date',es(formatDate(new Date(m.date+'T00:00:00')))));if(m.time)rows.push(metaItem('🕒','Time',es(m.time)));if(m.cinema)rows.push(metaItem('🎬','Cinema',es(m.cinema)));if(m.hall)rows.push(metaItem('🎟','Hall',es(m.hall)));if(m.platform||m.streamingPlatform)rows.push(metaItem('📺','Platform',es(m.platform||m.streamingPlatform)));if(m.watchingMethod)rows.push(metaItem('🎞','Method',es(m.watchingMethod)));if(m.director)rows.push(metaItem('🎥','Director',es(m.director)));if(m.genre)rows.push(metaItem('🏷','Genre',es(m.genre)));if(m.watchWith)rows.push(metaItem('👥','With',es(m.watchWith)));if(m.mood)rows.push(metaItem('💭','Mood',es(m.mood)));if(m.location)rows.push(metaItem('📍','Location',es(m.location)));if(m.year)rows.push(metaItem('📆','Year',String(m.year)));if(m.duration)rows.push(metaItem('⏱','Duration',String(m.duration)+' min'));metaEl.innerHTML=rows.join('');metaEl.hidden=rows.length===0}if(synWrap&&synEl){if(m.summary&&m.summary.trim()){synWrap.hidden=false;synEl.textContent=m.summary;setupSynopsisCollapse()}else{synWrap.hidden=true;synEl.textContent=''}}renderQuickStatus(m);renderTrailer(m);var editBtn=document.getElementById('mhPanelEdit'),deleteBtn=document.getElementById('mhPanelDelete'),shareBtn=document.getElementById('mhPanelShare'),exportBtn=document.getElementById('mhPanelExport'),icsBtn=document.getElementById('mhPanelIcs');if(editBtn)editBtn.onclick=function(){oS(m)};if(deleteBtn)deleteBtn.onclick=function(){if(!confirm('Delete "'+m.title+'"?'))return;S.movies=S.movies.filter(function(x){return x.id!==m.id});saveMovies().then(function(){aF();uC();refreshExtras();hideSelectedPanel();if(S._pendingDate){selectCalendarDay(S._pendingDate,{force:true})}else{showIdleList()}})['catch'](function(err){alert('Save failed: '+err.message);aF();uC();showIdleList()})};if(shareBtn)shareBtn.onclick=function(){shareMovieCard(m)};if(icsBtn)icsBtn.onclick=function(){exportMovieICS(m)};if(exportBtn)exportBtn.onclick=function(){exportOneMovie(m)};var actions=document.getElementById('mhPanelActions'),existingTicket=document.getElementById('mhPanelTicket');if(existingTicket)existingTicket.remove();if(actions&&m.ticket_url){var ticketBtn=document.createElement('button');ticketBtn.type='button';ticketBtn.className='mh-detail__action mh-detail__action--primary';ticketBtn.id='mhPanelTicket';ticketBtn.setAttribute('aria-label','Buy ticket');ticketBtn.textContent='🎫 Ticket';ticketBtn.onclick=function(){window.open(m.ticket_url,'_blank')};actions.insertBefore(ticketBtn,actions.firstChild)}panel.hidden=false;panel.classList.add('is-open');panel.style.display='';requestAnimationFrame(function(){panel.scrollIntoView({behavior:'smooth',block:'nearest'});if(card){try{card.focus({preventScroll:true})}catch(e){card.focus()}}})}

function filterByDate(ds){S._pendingDate=ds;var searchEl=document.getElementById('mhSearch');if(searchEl)searchEl.value='';S.filterStatus='all';var filterEl=document.getElementById('mhFilter');if(filterEl)filterEl.value='all';S.searchQuery='';aF();rL(function(m){return m.date===ds})}

document.getElementById('mhPrevWeek').addEventListener('click',function(){var ms=new Date(S.currentMonthStart);ms.setMonth(ms.getMonth()-1);S.currentMonthStart=ms;S._pendingDate=null;uMLabel();uC();showIdleList();refreshExtras()});
document.getElementById('mhNextWeek').addEventListener('click',function(){var ms=new Date(S.currentMonthStart);ms.setMonth(ms.getMonth()+1);S.currentMonthStart=ms;S._pendingDate=null;uMLabel();uC();showIdleList();refreshExtras()});
var todayBtn=document.getElementById('mhTodayBtn');if(todayBtn)todayBtn.addEventListener('click',function(){var now=new Date();S.currentMonthStart=new Date(now.getFullYear(),now.getMonth(),1);S._pendingDate=null;uMLabel();uC();showIdleList();refreshExtras();autoSelectToday()});

function aF(){var f=S.movies.slice(),q=S.searchQuery.toLowerCase();if(S.filterStatus!=='all')f=f.filter(function(m){return m.status===S.filterStatus});if(q){f=f.filter(function(m){return(m.title||'').toLowerCase().indexOf(q)!==-1||(m.summary||'').toLowerCase().indexOf(q)!==-1||(m.cinema||'').toLowerCase().indexOf(q)!==-1||(m.specials||[]).some(function(s){return s.toLowerCase().indexOf(q)!==-1})})}f.sort(function(a,b){return(b.year||0)-a.year||(b.rating||0)-a.rating});S.filtered=f}

function rL(filterFn){var list=document.getElementById('mhMovieList'),loading=document.getElementById('mhLoading');if(loading)loading.style.display='none';if(!list)return;list.innerHTML='';var movies=filterFn?S.movies.filter(filterFn):S.filtered;if(!movies||movies.length===0){list.innerHTML='<div class="mh-empty"><div class="mh-empty__icon">🎬</div><p class="mh-empty__text">No movies found</p><p class="mh-empty__sub">Click a date on the calendar or add your first movie.</p></div>';return}for(var i=0;i<movies.length;i++){var m=movies[i];var card=document.createElement('div');card.className='mh-movie-card mh-movie-card--compact';card.dataset.date=m.date||'';card.dataset.movieId=m.id;card.setAttribute('role','button');card.setAttribute('tabindex','0');card.setAttribute('aria-label','Select movie '+(m.title||'Untitled'));card.innerHTML=rC(m);function onPick(el){var mid=el.dataset.movieId;var mv=S.movies.find(function(x){return x.id===mid});if(!mv)return;if(mv.date)selectCalendarDay(mv.date,{force:true,movieId:mid});else{clearMovieList();showSelectedMovie(mv)}}card.addEventListener('click',function(e){if(e.target.closest('[data-edit],[data-delete]'))return;onPick(this)});card.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();onPick(this)}});list.appendChild(card)}}

/* Compact picker only — full detail lives solely in #mhSelectedPanel */
function rC(m){var st=getStatus(m.status);var meta='';if(m.time)meta+='<span>'+es(m.time)+'</span>';if(m.cinema)meta+='<span>'+es(m.cinema)+'</span>';if(m.hall)meta+='<span>'+es(m.hall)+'</span>';return'<div class="mh-movie-card__top"><div class="mh-movie-card__poster" aria-hidden="true">🎬</div><div class="mh-movie-card__info"><h3 class="mh-movie-card__title">'+es(m.title||'Untitled')+'</h3>'+(meta?'<div class="mh-movie-card__meta">'+meta+'</div>':'')+'</div></div><div class="mh-movie-card__bottom"><span class="mh-movie-card__status mh-movie-card__status--'+st.key+'">'+st.emoji+' '+st.label+'</span><div class="mh-movie-card__actions"><button type="button" class="mh-movie-card__action" data-edit="'+m.id+'" aria-label="Edit '+es(m.title||'')+'">✏ Edit</button><button type="button" class="mh-movie-card__action mh-movie-card__action--danger" data-delete="'+m.id+'" aria-label="Delete '+es(m.title||'')+'">🗑 Delete</button></div></div>'}

document.getElementById('mhMovieList').addEventListener('click',function(e){var t=e.target;if(t.dataset.edit){var m=S.movies.find(function(x){return x.id===t.dataset.edit});if(m)oS(m)}else if(t.dataset.delete){if(!confirm('Delete "'+(S.movies.find(function(x){return x.id===t.dataset.delete})||{}).title+'"?'))return;S.movies=S.movies.filter(function(x){return x.id!==t.dataset.delete});saveMovies().then(function(){aF();uC();S._pendingDate=null;showIdleList()})['catch'](function(err){alert('Save failed: '+err.message);aF();uC();showIdleList()})}});

function oS(m){var ov=document.getElementById('mhOverlay'),title=document.getElementById('mhModalTitle'),id=document.getElementById('mhEditId'),fTitle=document.getElementById('mhFormTitle'),fDate=document.getElementById('mhFormDate'),fYear=document.getElementById('mhFormYear'),fTime=document.getElementById('mhFormTime'),fCinema=document.getElementById('mhFormCinema'),fHall=document.getElementById('mhFormHall'),fTicket=document.getElementById('mhFormTicketUrl'),fSummary=document.getElementById('mhFormSummary'),saveBtn=document.getElementById('mhFormSave');S.editingId=m?m.id:null;if(m){title.textContent='Edit Movie';id.value=m.id;fTitle.value=m.title;fDate.value=m.date||'';fYear.value=m.year||'';fTime.value=m.time||'';fCinema.value=m.cinema||'';fHall.value=m.hall||'';fTicket.value=m.ticket_url||'';fSummary.value=m.summary||'';setStars(m.rating||0);setStatus(m.status||'coming-soon');setSpecials(m.specials||[])}else{title.textContent='Add Movie';id.value='';fTitle.value='';fDate.value=S._pendingDate||getISODate(new Date());fYear.value='';fTime.value='';fCinema.value='';fHall.value='';fTicket.value='';fSummary.value='';setStars(0);setStatus('coming-soon');setSpecials([])}saveBtn.textContent=m?'💾 Update':'💾 Save';if(ov)ov.style.display=''}

document.getElementById('mhModalClose').addEventListener('click',function(){var ov=document.getElementById('mhOverlay');if(ov)ov.style.display='none'});
document.getElementById('mhFormCancel').addEventListener('click',function(){var ov=document.getElementById('mhOverlay');if(ov)ov.style.display='none'});
document.getElementById('mhOverlay').addEventListener('click',function(e){if(e.target===this)this.style.display='none'});

document.getElementById('mhForm').addEventListener('submit',function(e){e.preventDefault();var title=document.getElementById('mhFormTitle').value.trim();if(!title){alert('Movie title is required.');return}var date=document.getElementById('mhFormDate').value;var year=parseInt(document.getElementById('mhFormYear').value,10)||null;var time=document.getElementById('mhFormTime').value;var cinema=document.getElementById('mhFormCinema').value.trim();var hall=document.getElementById('mhFormHall').value.trim();var ticket_url=document.getElementById('mhFormTicketUrl').value.trim();var summary=document.getElementById('mhFormSummary').value.trim();var rating=S._selectedRating||0;var status=S._selectedStatus||'coming-soon';var specials=S._selectedSpecials||[];var editId=S.editingId;var movieDate=date||(editId?(S.movies.find(function(x){return x.id===editId})||{}).date:null)||getISODate(new Date());if(movieDate&&countMoviesOnDate(movieDate,editId||null)>=MAX_MOVIES_PER_DAY){alert('Tối đa '+MAX_MOVIES_PER_DAY+' phim / ngày. Ngày '+movieDate+' đã đủ '+MAX_MOVIES_PER_DAY+' phim. Chọn ngày khác hoặc xóa bớt.');return;}if(editId){var idx=S.movies.findIndex(function(x){return x.id===editId});if(idx!==-1){S.movies[idx]={id:editId,title:title,date:date||S.movies[idx].date,year:year,time:time,cinema:cinema,hall:hall,ticket_url:ticket_url,rating:rating,status:status,summary:summary,specials:specials,created:S.movies[idx].created,updated:Date.now()}}}else{S.movies.push({id:gId(),title:title,date:movieDate,year:year,time:time,cinema:cinema,hall:hall,ticket_url:ticket_url,rating:rating,status:status,summary:summary,specials:specials,created:Date.now(),updated:Date.now()})}S._pendingDate=null;var ov=document.getElementById('mhOverlay');if(ov)ov.style.display='none';saveMovies().then(function(){aF();uC();refreshExtras();if(S._pendingDate){selectCalendarDay(S._pendingDate,{force:true})}else{showIdleList()}hideSelectedPanel()})['catch'](function(err){alert('Save failed: '+err.message+'\nPlease try again.')})});

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
function formatDate(d){var days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];return days[d.getDay()===0?6:d.getDay()-1]+' '+d.getDate()+'/'+(d.getMonth()+1)+'/'+d.getFullYear()}
function es(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
// Sau khi lưu: không scroll, không bung UI — chỉ toast progress bar (fixed)
function hSC(){}
function lV(){var UI='import-fix-1';var BASE=(document.body&&document.body.getAttribute('data-site-base'))||'';fetch(BASE.replace(/\/$/,'')+'/build-info.json').then(function(r){if(!r.ok)return null;return r.json()})['catch'](function(){return null}).then(function(info){var el=document.getElementById('mhVersionBadge');if(!el)return;if(!info){el.textContent='Phiên bản dịch vụ: dev ('+UI+')';return}el.textContent='Phiên bản dịch vụ: '+info.generated_at_display.replace(' ','-'+info.short_sha+'_')+' · '+UI})}

function exportMovies(){var json=JSON.stringify(S.movies,null,2);var blob=new Blob([json],{type:'application/json'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='movie-calendar-'+getISODate(new Date())+'.json';a.click();URL.revokeObjectURL(url)}

var exportBtn=document.getElementById('mhExportBtn');if(exportBtn)exportBtn.addEventListener('click',exportMovies);
var addBtn=document.getElementById('mhAddBtn');if(addBtn)addBtn.addEventListener('click',function(){oS()});
var searchEl=document.getElementById('mhSearch');if(searchEl)searchEl.addEventListener('input',function(){S.searchQuery=this.value||'';aF();if((S.searchQuery||'').trim()){hideSelectedPanel();rL()}else if(S._pendingDate){selectCalendarDay(S._pendingDate,{force:true})}else{showIdleList()}});
var filterEl=document.getElementById('mhFilter');if(filterEl)filterEl.addEventListener('change',function(){S.filterStatus=this.value||'all';aF();if(S.filterStatus!=='all'){hideSelectedPanel();rL()}else if(S._pendingDate){selectCalendarDay(S._pendingDate,{force:true})}else if((S.searchQuery||'').trim()){rL()}else{showIdleList()}});

/* ─── Excel Import / Export ───────────────────────────────── */
var MH_XLSX_HEADERS = [
  'Movie Title *', 'Original Title', 'Watch Date *', 'Watch Time', 'Country', 'Language',
  'Genre', 'Director', 'Main Cast', 'Streaming Platform', 'Cinema', 'Watching Method',
  'Duration (minutes)', 'Personal Rating (0-10)', 'IMDb Rating', 'Rotten Tomatoes',
  'Letterboxd Rating', 'Favorite (Yes/No)', 'Rewatch (Yes/No)', 'Watch With', 'Mood',
  'Review', 'Tags', 'Poster URL (optional)', 'Trailer URL', 'Official Website', 'Notes'
];
var MH_XLSX_SAMPLE = [
  'THE ODYSSEY', 'The Odyssey', '2026-07-17', '09:20', 'USA', 'English',
  'Action, Adventure', 'Christopher Nolan', 'Matt Damon, Tom Holland', '', 'CGV Hùng Vương Plaza', 'Cinema',
  150, 9, 8.2, '92%', 4.1, 'Yes', 'No', 'Friends', 'Excited',
  'Epic Nolan adaptation — sample row for template only', 'cinema, imax', '', '', 'https://www.cgv.vn/', 'Template sample'
];
var pendingMhImport = null;

function mhEnsureXLSX() {
  if (typeof XLSX === 'undefined') {
    alert('Thư viện Excel chưa sẵn sàng. Thử lại sau giây lát.');
    return false;
  }
  return true;
}

function mhSetIoStatus(kind, msg) {
  var el = document.getElementById('mhIoStatus');
  if (!el) return;
  el.hidden = false;
  el.className = 'mh-io__status mh-io__status--' + (kind === 'ok' ? 'ok' : kind === 'warn' ? 'warn' : 'err');
  el.textContent = msg;
}

function mhSetProgress(show, pct, text) {
  var wrap = document.getElementById('mhIoProgress');
  var fill = document.getElementById('mhIoProgressFill');
  var lab = document.getElementById('mhIoProgressText');
  if (!wrap) return;
  if (show) { wrap.hidden = false; } else { wrap.hidden = true; }
  if (fill) fill.style.width = (pct || 0) + '%';
  if (lab) lab.textContent = text || '';
}

function mhColLetter(n) {
  var s = '';
  n += 1;
  while (n > 0) {
    var m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function mhHeaderStyle() {
  return {
    font: { bold: true, color: { rgb: 'FFFFFFFF' }, name: 'Calibri', sz: 11 },
    fill: { fgColor: { rgb: '00A7A0' } },
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: {
      top: { style: 'thin', color: { rgb: '007F7A' } },
      bottom: { style: 'thin', color: { rgb: '007F7A' } },
      left: { style: 'thin', color: { rgb: '007F7A' } },
      right: { style: 'thin', color: { rgb: '007F7A' } }
    }
  };
}

function mhInstructionStyle() {
  return {
    font: { italic: true, color: { rgb: '555555' }, name: 'Calibri', sz: 10 },
    fill: { fgColor: { rgb: 'EEF8F7' } },
    alignment: { wrapText: true, vertical: 'center' }
  };
}

function mhBuildSheet(dataRows) {
  var instr = [
    'INSTRUCTIONS: Row 1 = headers (do not rename). Row 2 = example (replace or delete). Required: Movie Title *, Watch Date * (yyyy-mm-dd). Personal Rating 0–10. Favorite/Rewatch = Yes or No. Tags comma-separated. UTF-8 Vietnamese OK. Sheet name: Movie History.'
  ];
  while (instr.length < MH_XLSX_HEADERS.length) instr.push('');
  var aoa = [MH_XLSX_HEADERS.slice(), instr, (dataRows && dataRows[0]) ? dataRows[0] : MH_XLSX_SAMPLE.slice()];
  if (dataRows && dataRows.length > 1) {
    for (var i = 1; i < dataRows.length; i++) aoa.push(dataRows[i]);
  } else if (dataRows && dataRows.length === 1 && dataRows[0] !== MH_XLSX_SAMPLE) {
    // already added as row 3
  }
  // For export: if dataRows provided, use headers + data only (no instruction row for clean round-trip)
  if (dataRows && dataRows._exportMode) {
    aoa = [MH_XLSX_HEADERS.slice()].concat(dataRows);
  }
  var ws = XLSX.utils.aoa_to_sheet(aoa);
  ws['!cols'] = MH_XLSX_HEADERS.map(function (h, i) {
    var max = h.length + 2;
    for (var r = 0; r < Math.min(aoa.length, 50); r++) {
      var cell = aoa[r][i];
      var len = cell == null ? 0 : String(cell).length + 2;
      if (len > max) max = len;
    }
    return { wch: Math.min(Math.max(max, 12), 36) };
  });
  ws['!freeze'] = { xSplit: 0, ySplit: 1, topLeftCell: 'A2', activePane: 'bottomLeft', state: 'frozen' };
  ws['!views'] = [{ state: 'frozen', ySplit: 1, topLeftCell: 'A2', activePane: 'bottomLeft' }];
  ws['!rows'] = [{ hpt: 26 }];
  for (var c = 0; c < MH_XLSX_HEADERS.length; c++) {
    var addr = mhColLetter(c) + '1';
    if (ws[addr]) ws[addr].s = mhHeaderStyle();
  }
  // instruction row styling when present
  if (!dataRows || !dataRows._exportMode) {
    for (var c2 = 0; c2 < MH_XLSX_HEADERS.length; c2++) {
      var a2 = mhColLetter(c2) + '2';
      if (ws[a2]) ws[a2].s = mhInstructionStyle();
    }
    if (ws['!merges'] === undefined) ws['!merges'] = [];
    // optional: leave as separate cells for column-aligned hints
  }
  // Data validation lists for Favorite / Rewatch columns (R=17, S=18 zero-based)
  if (!ws['!dataValidation']) ws['!dataValidation'] = [];
  try {
    ws['!dataValidation'].push({
      sqref: 'R3:R10000', type: 'list', formula1: '"Yes,No"', allowBlank: true
    });
    ws['!dataValidation'].push({
      sqref: 'S3:S10000', type: 'list', formula1: '"Yes,No"', allowBlank: true
    });
  } catch (e) {}
  return ws;
}

function downloadMovieExcelTemplate() {
  if (!mhEnsureXLSX()) return;
  try {
    var wb = XLSX.utils.book_new();
    var ws = mhBuildSheet([MH_XLSX_SAMPLE.slice()]);
    XLSX.utils.book_append_sheet(wb, ws, 'Movie History');
    XLSX.writeFile(wb, 'Movie_History_Template.xlsx');
    mhSetIoStatus('ok', '✓ Đã tải Movie_History_Template.xlsx (sheet “Movie History”, 1 dòng mẫu).');
  } catch (e) {
    mhSetIoStatus('err', '✗ Không tạo được template: ' + (e.message || e));
  }
}

function movieToExcelRow(m) {
  var fav = (m.specials || []).indexOf('favorite') !== -1 || m.favorite === true || m.favorite === 'Yes';
  var rew = (m.specials || []).indexOf('rewatch') !== -1 || m.rewatch === true || m.rewatch === 'Yes';
  var personal = m.personalRating != null ? m.personalRating : (m.rating != null ? Number(m.rating) * 2 : '');
  var tags = Array.isArray(m.tags) ? m.tags.join(', ') : (m.tags || (m.specials || []).join(', '));
  return [
    m.title || '',
    m.originalTitle || '',
    m.date || '',
    m.time || '',
    m.country || '',
    m.language || '',
    m.genre || '',
    m.director || '',
    m.mainCast || '',
    m.platform || m.streamingPlatform || '',
    m.cinema || '',
    m.watchingMethod || '',
    m.duration != null ? m.duration : '',
    personal,
    m.imdbRating != null ? m.imdbRating : '',
    m.rottenTomatoes != null ? m.rottenTomatoes : '',
    m.letterboxdRating != null ? m.letterboxdRating : '',
    fav ? 'Yes' : 'No',
    rew ? 'Yes' : 'No',
    m.watchWith || '',
    m.mood || '',
    m.review || m.summary || '',
    tags,
    m.posterUrl || '',
    m.trailerUrl || '',
    m.officialWebsite || m.ticket_url || '',
    m.notes || ''
  ];
}

function exportMoviesExcel() {
  if (!mhEnsureXLSX()) return;
  if (!S.movies || !S.movies.length) {
    mhSetIoStatus('warn', '⚠ Chưa có dữ liệu để export.');
    return;
  }
  try {
    var rows = S.movies.map(movieToExcelRow);
    rows._exportMode = true;
    var wb = XLSX.utils.book_new();
    var ws = mhBuildSheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Movie History');
    XLSX.writeFile(wb, 'Movie_History_Export.xlsx');
    mhSetIoStatus('ok', '✓ Exported ' + S.movies.length + ' movies (cùng cấu trúc template — round-trip OK).');
  } catch (e) {
    mhSetIoStatus('err', '✗ Export failed: ' + (e.message || e));
  }
}

function mhNormHeader(h) {
  return String(h == null ? '' : h).replace(/^\uFEFF/, '').trim().toLowerCase().replace(/[%*()]/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
}

function mhBuildHeaderMap(headerRow) {
  var aliases = {
    'movie title': 'Movie Title *', 'title': 'Movie Title *',
    'original title': 'Original Title',
    'watch date': 'Watch Date *', 'date': 'Watch Date *',
    'watch time': 'Watch Time', 'time': 'Watch Time',
    'country': 'Country', 'language': 'Language', 'genre': 'Genre', 'director': 'Director',
    'main cast': 'Main Cast', 'cast': 'Main Cast',
    'streaming platform': 'Streaming Platform', 'platform': 'Streaming Platform',
    'cinema': 'Cinema', 'watching method': 'Watching Method', 'method': 'Watching Method',
    'duration minutes': 'Duration (minutes)', 'duration': 'Duration (minutes)',
    'personal rating 0 10': 'Personal Rating (0-10)', 'personal rating': 'Personal Rating (0-10)', 'rating': 'Personal Rating (0-10)',
    'imdb rating': 'IMDb Rating', 'imdb': 'IMDb Rating',
    'rotten tomatoes': 'Rotten Tomatoes',
    'letterboxd rating': 'Letterboxd Rating', 'letterboxd': 'Letterboxd Rating',
    'favorite yes no': 'Favorite (Yes/No)', 'favorite': 'Favorite (Yes/No)',
    'rewatch yes no': 'Rewatch (Yes/No)', 'rewatch': 'Rewatch (Yes/No)',
    'watch with': 'Watch With', 'mood': 'Mood', 'review': 'Review', 'tags': 'Tags',
    'poster url optional': 'Poster URL (optional)', 'poster url': 'Poster URL (optional)', 'poster': 'Poster URL (optional)',
    'trailer url': 'Trailer URL', 'trailer': 'Trailer URL',
    'official website': 'Official Website', 'website': 'Official Website',
    'notes': 'Notes'
  };
  var map = {};
  for (var i = 0; i < headerRow.length; i++) {
    var n = mhNormHeader(headerRow[i]);
    if (!n) continue;
    if (n.indexOf('instruction') === 0) continue;
    var key = aliases[n];
    if (!key) {
      for (var j = 0; j < MH_XLSX_HEADERS.length; j++) {
        if (mhNormHeader(MH_XLSX_HEADERS[j]) === n) { key = MH_XLSX_HEADERS[j]; break; }
      }
    }
    if (key) map[key] = i;
  }
  return map;
}

function mhYesNo(v) {
  if (v === true || v === 1) return true;
  var s = String(v == null ? '' : v).trim().toLowerCase();
  return s === 'yes' || s === 'y' || s === 'true' || s === '1' || s === 'x';
}

function mhParseDate(v) {
  if (v == null || v === '') return '';
  if (v instanceof Date && !isNaN(v.getTime())) {
    return v.getFullYear() + '-' + String(v.getMonth() + 1).padStart(2, '0') + '-' + String(v.getDate()).padStart(2, '0');
  }
  if (typeof v === 'number' && isFinite(v)) {
    var epoch = Date.UTC(1899, 11, 30);
    var dt = new Date(epoch + Math.round(v * 86400000));
    return dt.getUTCFullYear() + '-' + String(dt.getUTCMonth() + 1).padStart(2, '0') + '-' + String(dt.getUTCDate()).padStart(2, '0');
  }
  var s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  var m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
  if (m) return m[3] + '-' + String(m[2]).padStart(2, '0') + '-' + String(m[1]).padStart(2, '0');
  return s;
}

function mhIsValidDate(s) {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  var p = s.split('-').map(Number);
  var d = new Date(p[0], p[1] - 1, p[2]);
  return d.getFullYear() === p[0] && d.getMonth() === p[1] - 1 && d.getDate() === p[2];
}

function mhIsValidUrl(s) {
  if (!s) return true;
  try {
    var u = new URL(String(s).trim());
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch (e) { return false; }
}

function mhRowEmpty(row) {
  if (!row || !row.length) return true;
  for (var i = 0; i < row.length; i++) {
    if (row[i] !== undefined && row[i] !== null && String(row[i]).trim() !== '') return false;
  }
  return true;
}

function mhDupKey(title, date) {
  return String(title || '').trim().toLowerCase() + '||' + String(date || '').trim();
}

function mhValidateMovie(m) {
  var errors = [];
  if (!m.title) errors.push('Thiếu Movie Title');
  if (!m.date) errors.push('Thiếu Watch Date');
  else if (!mhIsValidDate(m.date)) errors.push('Watch Date sai định dạng');
  if (m.personalRating != null && m.personalRating !== '') {
    var pr = Number(m.personalRating);
    if (isNaN(pr) || pr < 0 || pr > 10) errors.push('Personal Rating phải 0–10');
  }
  if (m.duration != null && m.duration !== '') {
    var d = Number(m.duration);
    if (isNaN(d) || d <= 0) errors.push('Duration phải > 0');
  }
  if (m.posterUrl && !mhIsValidUrl(m.posterUrl)) errors.push('Poster URL không hợp lệ');
  if (m.trailerUrl && !mhIsValidUrl(m.trailerUrl)) errors.push('Trailer URL không hợp lệ');
  if (m.officialWebsite && !mhIsValidUrl(m.officialWebsite)) errors.push('Official Website không hợp lệ');
  return errors;
}

function mhParseWorkbook(wb) {
  var sheetName = wb.SheetNames.indexOf('Movie History') !== -1 ? 'Movie History' : wb.SheetNames[0];
  var ws = wb.Sheets[sheetName];
  if (!ws) throw new Error('Không tìm thấy sheet.');
  var rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true });
  if (!rows.length) throw new Error('File trống.');

  // Find header row (skip instruction rows)
  var headerIdx = 0;
  for (var hi = 0; hi < Math.min(rows.length, 5); hi++) {
    var mapTry = mhBuildHeaderMap(rows[hi] || []);
    if (mapTry['Movie Title *'] !== undefined && mapTry['Watch Date *'] !== undefined) {
      headerIdx = hi;
      break;
    }
  }
  var colMap = mhBuildHeaderMap(rows[headerIdx] || []);
  if (colMap['Movie Title *'] === undefined || colMap['Watch Date *'] === undefined) {
    throw new Error('Thiếu cột bắt buộc: Movie Title * và/hoặc Watch Date *');
  }

  var valid = [];
  var invalid = [];
  var max = Math.min(rows.length - 1, 20000);
  var seen = {};

  for (var r = headerIdx + 1; r <= max; r++) {
    var row = rows[r];
    if (mhRowEmpty(row)) continue;
    // skip pure instruction echo
    var first = String(row[0] || '');
    if (/^INSTRUCTIONS:/i.test(first)) continue;

    function cell(name) {
      var idx = colMap[name];
      return idx === undefined ? '' : row[idx];
    }

    var title = String(cell('Movie Title *') || '').trim();
    var date = mhParseDate(cell('Watch Date *'));
    var personalRaw = cell('Personal Rating (0-10)');
    var personal = personalRaw === '' || personalRaw == null ? null : parseFloat(String(personalRaw).replace(',', '.'));
    var durationRaw = cell('Duration (minutes)');
    var duration = durationRaw === '' || durationRaw == null ? null : parseFloat(String(durationRaw).replace(',', '.'));
    var fav = mhYesNo(cell('Favorite (Yes/No)'));
    var rew = mhYesNo(cell('Rewatch (Yes/No)'));
    var specials = [];
    if (fav) specials.push('favorite');
    if (rew) specials.push('rewatch');
    var tagsStr = String(cell('Tags') || '').trim();
    var tags = tagsStr ? tagsStr.split(/[,;]/).map(function (t) { return t.trim(); }).filter(Boolean) : [];
    tags.forEach(function (t) {
      var low = t.toLowerCase();
      if ((low === 'cinema' || low === 'series' || low === 'anime' || low === 'documentary') && specials.indexOf(low) === -1) specials.push(low);
    });

    var ratingStars = personal != null && !isNaN(personal) ? Math.max(0, Math.min(5, Math.round(personal / 2))) : 0;
    var yearFromDate = date && mhIsValidDate(date) ? parseInt(date.slice(0, 4), 10) : null;

    var movie = {
      id: gId(),
      title: title,
      originalTitle: String(cell('Original Title') || '').trim(),
      date: date,
      year: yearFromDate,
      time: String(cell('Watch Time') || '').trim(),
      country: String(cell('Country') || '').trim(),
      language: String(cell('Language') || '').trim(),
      genre: String(cell('Genre') || '').trim(),
      director: String(cell('Director') || '').trim(),
      mainCast: String(cell('Main Cast') || '').trim(),
      platform: String(cell('Streaming Platform') || '').trim(),
      cinema: String(cell('Cinema') || '').trim(),
      watchingMethod: String(cell('Watching Method') || '').trim(),
      duration: duration,
      personalRating: personal,
      rating: ratingStars,
      imdbRating: cell('IMDb Rating') === '' ? null : cell('IMDb Rating'),
      rottenTomatoes: String(cell('Rotten Tomatoes') || '').trim(),
      letterboxdRating: cell('Letterboxd Rating') === '' ? null : cell('Letterboxd Rating'),
      watchWith: String(cell('Watch With') || '').trim(),
      mood: String(cell('Mood') || '').trim(),
      summary: String(cell('Review') || '').trim(),
      review: String(cell('Review') || '').trim(),
      tags: tags,
      specials: specials,
      posterUrl: String(cell('Poster URL (optional)') || '').trim(),
      trailerUrl: String(cell('Trailer URL') || '').trim(),
      officialWebsite: String(cell('Official Website') || '').trim(),
      ticket_url: String(cell('Official Website') || '').trim(),
      notes: String(cell('Notes') || '').trim(),
      hall: '',
      status: 'watching',
      created: Date.now(),
      updated: Date.now(),
      _rowNum: r + 1,
      _action: 'create'
    };

    var errors = mhValidateMovie(movie);
    var key = mhDupKey(movie.title, movie.date);
    if (key !== '||' && seen[key]) errors.push('Trùng Title+Date trong file');
    if (key !== '||') {
      var existing = S.movies.find(function (x) { return mhDupKey(x.title, x.date) === key; });
      if (existing) {
        movie._action = 'update';
        movie.id = existing.id;
        movie.created = existing.created || movie.created;
        movie.status = existing.status || movie.status;
        movie.hall = existing.hall || '';
      }
    }

    if (errors.length) {
      invalid.push({ row: r + 1, errors: errors, movie: movie });
    } else {
      if (key !== '||') seen[key] = 1;
      valid.push(movie);
    }
  }

  return { sheetName: sheetName, totalDataRows: valid.length + invalid.length, valid: valid, invalid: invalid };
}

function mhOpenImportModal(result) {
  pendingMhImport = result;
  var modal = document.getElementById('mhImportModal');
  if (!modal) return;
  modal.hidden = false;
  modal.style.display = 'flex';
  var sum = document.getElementById('mhImportSummary');
  if (sum) {
    var updates = result.valid.filter(function (m) { return m._action === 'update'; }).length;
    sum.innerHTML =
      'Sheet: <strong>' + es(result.sheetName) + '</strong> · ' +
      'Tổng: <strong>' + result.totalDataRows + '</strong> · ' +
      'Hợp lệ: <strong style="color:#2e7d32">' + result.valid.length + '</strong> ' +
      '(new ' + (result.valid.length - updates) + ' / update ' + updates + ') · ' +
      'Bỏ qua: <strong style="color:#c62828">' + result.invalid.length + '</strong>';
  }
  var head = document.getElementById('mhImportPreviewHead');
  var body = document.getElementById('mhImportPreviewBody');
  if (head) head.innerHTML = '<tr><th>#</th><th>Act</th><th>Title</th><th>Date</th><th>Cinema</th><th>Rating</th><th>Lỗi</th></tr>';
  if (body) {
    body.innerHTML = '';
    var preview = result.invalid.map(function (i) {
      return { ok: false, row: i.row, m: i.movie, errors: i.errors };
    }).concat(result.valid.slice(0, 50).map(function (m) {
      return { ok: true, row: m._rowNum, m: m, errors: [] };
    }));
    preview.sort(function (a, b) { return a.row - b.row; });
    preview.slice(0, 80).forEach(function (item) {
      var tr = document.createElement('tr');
      tr.className = item.ok ? 'is-valid' : 'is-invalid';
      tr.innerHTML =
        '<td>' + item.row + '</td>' +
        '<td>' + (item.ok ? (item.m._action === 'update' ? 'UPD' : 'NEW') : '✗') + '</td>' +
        '<td>' + es(item.m.title) + '</td>' +
        '<td>' + es(item.m.date) + '</td>' +
        '<td>' + es(item.m.cinema) + '</td>' +
        '<td>' + es(item.m.personalRating != null ? String(item.m.personalRating) : '') + '</td>' +
        '<td>' + es(item.errors.join('; ')) + '</td>';
      body.appendChild(tr);
    });
  }
  var report = document.getElementById('mhImportReport');
  if (report) {
    report.textContent = result.invalid.length
      ? result.invalid.slice(0, 40).map(function (i) { return 'Dòng ' + i.row + ': ' + i.errors.join('; '); }).join('\n')
      : 'Tất cả dòng hợp lệ.';
  }
  var btn = document.getElementById('mhImportConfirm');
  if (btn) btn.disabled = result.valid.length === 0;
}

function mhCloseImportModal() {
  pendingMhImport = null;
  var modal = document.getElementById('mhImportModal');
  if (modal) { modal.hidden = true; modal.style.display = 'none'; }
  var f = document.getElementById('mhImportFile');
  if (f) f.value = '';
}

function mhRefreshAfterImport() {
  aF();
  rM();
  uC();
  showIdleList();
  refreshExtras();
}

function mhConfirmImport() {
  if (!pendingMhImport || !pendingMhImport.valid.length) {
    mhSetIoStatus('err', '✗ Không có dòng hợp lệ.');
    mhCloseImportModal();
    return;
  }
  var modeEl = document.querySelector('input[name="mhImportMode"]:checked');
  var mode = modeEl ? modeEl.value : 'append';
  var nValid = pendingMhImport.valid.length;
  var nInvalid = pendingMhImport.invalid.length;
  var nUpdate = 0, nCreate = 0, nDayDropped = 0;

  var cleaned = pendingMhImport.valid.map(function (m) {
    var c = JSON.parse(JSON.stringify(m));
    delete c._rowNum;
    delete c._action;
    return { raw: m, clean: c };
  });

  if (mode === 'replace') {
    S.movies = cleaned.map(function (x) { nCreate++; return x.clean; });
  } else {
    var byKey = {};
    S.movies.forEach(function (m) { byKey[mhDupKey(m.title, m.date)] = m; });
    cleaned.forEach(function (x) {
      var key = mhDupKey(x.clean.title, x.clean.date);
      if (byKey[key]) {
        var keepId = byKey[key].id;
        var keepCreated = byKey[key].created;
        var keepStatus = byKey[key].status;
        Object.keys(x.clean).forEach(function (k) { byKey[key][k] = x.clean[k]; });
        byKey[key].id = keepId;
        byKey[key].created = keepCreated;
        if (keepStatus) byKey[key].status = keepStatus;
        byKey[key].updated = Date.now();
        nUpdate++;
      } else {
        byKey[key] = x.clean;
        nCreate++;
      }
    });
    S.movies = Object.keys(byKey).map(function (k) { return byKey[k]; });
  }

  try {
    var dayCap = enforceMaxMoviesPerDay(S.movies, MAX_MOVIES_PER_DAY);
    nDayDropped = (dayCap && dayCap.dropped) ? dayCap.dropped.length : 0;
    if (nDayDropped) {
      S.movies = dayCap.movies;
      nCreate = Math.max(0, nCreate - nDayDropped);
    }
  } catch (capErr) {
    console.error('dayCap', capErr);
    nDayDropped = 0;
  }

  // Always close modal + refresh UI even if GitHub save fails
  mhCloseImportModal();
  mhSetProgress(true, 70, 'Đang lưu & làm mới lịch…');
  try { mhRefreshAfterImport(); } catch (rfErr) { console.error('refresh', rfErr); }

  var afterSave = function () {
    mhSetProgress(true, 100, 'Hoàn tất');
    setTimeout(function () { mhSetProgress(false); }, 1200);
    if (nInvalid) {
      mhSetIoStatus('warn', '⚠ Imported with warnings: +' + nCreate + ' new · ' + nUpdate + ' updated · ' + nInvalid + ' skipped' + (nDayDropped ? (' · ' + nDayDropped + ' bị chặn (>'+MAX_MOVIES_PER_DAY+'/ngày)') : '') + '. Calendar refreshed.');
    } else {
      mhSetIoStatus(nDayDropped ? 'warn' : 'ok', (nDayDropped ? '⚠ ' : '✓ ') + 'Imported: +' + nCreate + ' new · ' + nUpdate + ' updated' + (nDayDropped ? (' · ' + nDayDropped + ' bị chặn (max '+MAX_MOVIES_PER_DAY+' phim/ngày)') : '') + '. UI refreshed.');
    }
  };

  // Token missing → still keep import in session, prompt token
  var token = (typeof getToken === 'function') ? getToken() : '';
  if (!token) {
    afterSave();
    mhSetIoStatus('warn', '⚠ Đã import vào phiên này nhưng chưa có GitHub token — bấm 🔑 rồi lưu lại (Add/Edit/import).');
    try { if (typeof sT === 'function') sT(); } catch (e) {}
    return;
  }

  saveMovies().then(afterSave)['catch'](function (err) {
    afterSave();
    mhSetIoStatus('warn', '⚠ Data imported in session; GitHub save: ' + (err.message || err) + '. Kiểm tra 🔑 token.');
  });
}

function mhHandleImportFile(file) {
  if (!file) return;
  if (!mhEnsureXLSX()) return;
  if (!/\.xlsx$/i.test(file.name || '')) {
    mhSetIoStatus('err', '✗ Chỉ hỗ trợ .xlsx');
    return;
  }
  mhSetIoStatus('ok', 'Đang đọc “' + file.name + '”…');
  mhSetProgress(true, 20, 'Đang parse Excel…');
  var reader = new FileReader();
  reader.onload = function (ev) {
    // yield to UI for large files
    setTimeout(function () {
      try {
        mhSetProgress(true, 45, 'Đang validate…');
        var wb = XLSX.read(new Uint8Array(ev.target.result), { type: 'array', cellDates: true });
        var result = mhParseWorkbook(wb);
        mhSetProgress(true, 90, 'Chuẩn bị preview…');
        if (!result.totalDataRows) {
          mhSetProgress(false);
          mhSetIoStatus('err', '✗ File không có dòng dữ liệu.');
          return;
        }
        mhOpenImportModal(result);
        mhSetProgress(false);
        if (!result.valid.length) mhSetIoStatus('err', '✗ Mọi dòng đều lỗi — xem preview.');
        else if (result.invalid.length) mhSetIoStatus('warn', '⚠ Có dòng lỗi — kiểm tra preview trước khi xác nhận.');
        else mhSetIoStatus('ok', '✓ Parse OK ' + result.valid.length + ' dòng — xác nhận để import.');
      } catch (e) {
        mhSetProgress(false);
        mhSetIoStatus('err', '✗ Import failed: ' + (e.message || e));
      }
    }, 30);
  };
  reader.onerror = function () {
    mhSetProgress(false);
    mhSetIoStatus('err', '✗ Không đọc được file.');
  };
  reader.readAsArrayBuffer(file);
}


function daysUntilMovie(m){if(!m||!m.date||!/^\d{4}-\d{2}-\d{2}$/.test(m.date))return null;var t=new Date();t.setHours(0,0,0,0);var d=new Date(m.date+'T00:00:00');return Math.round((d-t)/86400000)}
function getISODateLocal(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function upcomingMovies(){var today=getISODateLocal(new Date());return S.movies.filter(function(m){if(!m.date)return false;if(m.status==='cancelled')return false;return m.date>=today}).sort(function(a,b){var c=String(a.date).localeCompare(String(b.date));if(c)return c;return String(a.time||'').localeCompare(String(b.time||''))})}
function refreshExtras(){renderNextUp();renderFavoritesWall();renderYearReview();if(S._view==='list')renderCinemaView()}
function renderNextUp(){var box=document.getElementById('mhNextUp');if(!box)return;var up=upcomingMovies();var today=getISODateLocal(new Date());var todayCount=S.movies.filter(function(m){return m.date===today&&m.status!=='cancelled'}).length;var needTicket=S.movies.filter(function(m){return m.status==='need-ticket'&&m.date>=today}).length;var stats=document.getElementById('mhNextUpStats');if(stats){stats.innerHTML='<span class="mh-nextup__pill">Hôm nay: '+todayCount+'</span><span class="mh-nextup__pill">Sắp tới: '+up.length+'</span>'+(needTicket?'<span class="mh-nextup__pill">🎫 Need ticket: '+needTicket+'</span>':'')}if(!up.length){box.hidden=true;S._nextUpId=null;return}var m=up[0];S._nextUpId=m.id;box.hidden=false;var dLeft=daysUntilMovie(m);var label=document.getElementById('mhNextUpLabel');var title=document.getElementById('mhNextUpTitle');var meta=document.getElementById('mhNextUpMeta');if(label)label.textContent=dLeft===0?'Today on your calendar':'Next up'+(dLeft!=null&&dLeft>0?(' · D-'+dLeft):'');if(title)title.textContent=m.title||'Untitled';var bits=[];if(m.date)bits.push(formatDate(new Date(m.date+'T00:00:00')));if(m.time)bits.push(m.time);if(m.cinema)bits.push(m.cinema);var st=getStatus(m.status);bits.push(st.emoji+' '+st.label);if(meta)meta.textContent=bits.join(' · ')}
function renderQuickStatus(m){var host=document.getElementById('mhPanelQuickStatus');if(!host||!m)return;var keys=['watching','coming-soon','need-ticket','waiting','sold-out','cancelled'];host.innerHTML='';keys.forEach(function(k){var st=STATUS_MAP[k];var b=document.createElement('button');b.type='button';b.className='mh-detail__qstatus'+(m.status===k?' is-active':'');b.textContent=st.emoji+' '+st.label;b.addEventListener('click',function(e){e.stopPropagation();if(m.status===k)return;m.status=k;m.updated=Date.now();saveMovies().then(function(){aF();uC();refreshExtras();showSelectedMovie(m)})['catch'](function(err){alert('Save failed: '+err.message)})});host.appendChild(b)})}
function youtubeId(url){if(!url)return null;var m=String(url).match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|shorts\/))([A-Za-z0-9_-]{6,})/);return m?m[1]:null}
function renderTrailer(m){var wrap=document.getElementById('mhPanelTrailerWrap');var host=document.getElementById('mhPanelTrailer');if(!wrap||!host)return;var url=m.trailerUrl||'';if(!url){wrap.hidden=true;host.innerHTML='';return}wrap.hidden=false;var yid=youtubeId(url);if(yid){host.innerHTML='<iframe src="https://www.youtube.com/embed/'+yid+'" title="Trailer" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture" allowfullscreen loading="lazy"></iframe>'}else{host.innerHTML='<a class="mh-detail__trailer-link" href="'+es(url)+'" target="_blank" rel="noopener noreferrer">▶ Open trailer</a>'}}
function exportMovieICS(m){if(!m||!m.date){alert('Movie needs a date for calendar export.');return}var start=m.date.replace(/-/g,'');var time=(m.time||'19:00').replace(':','');if(time.length===4)time=time+'00';var dtStart=start+'T'+time;var endH=parseInt((m.time||'19:00').split(':')[0],10);var endM=parseInt((m.time||'19:00').split(':')[1]||'0',10);var dur=parseInt(m.duration,10)||120;var endDate=new Date(m.date+'T00:00:00');endDate.setHours(endH);endDate.setMinutes(endM+dur);var dtEnd=endDate.getFullYear()+String(endDate.getMonth()+1).padStart(2,'0')+String(endDate.getDate()).padStart(2,'0')+'T'+String(endDate.getHours()).padStart(2,'0')+String(endDate.getMinutes()).padStart(2,'0')+'00';var desc=(m.summary||m.review||'').replace(/\n/g,'\\n');var loc=[m.cinema,m.hall].filter(Boolean).join(' · ');var ics=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ReviewChanThat//MovieCalendar//EN','BEGIN:VEVENT','UID:'+ (m.id||gId()) +'@movie-history','DTSTAMP:'+new Date().toISOString().replace(/[-:]/g,'').split('.')[0]+'Z','DTSTART:'+dtStart,'DTEND:'+dtEnd,'SUMMARY:'+String(m.title||'Movie').replace(/,/g,'\\,'),'DESCRIPTION:'+desc.replace(/,/g,'\\,'),'LOCATION:'+String(loc).replace(/,/g,'\\,'),'END:VEVENT','END:VCALENDAR'].join('\r\n');var blob=new Blob([ics],{type:'text/calendar;charset=utf-8'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=(m.title||'movie').replace(/[^\w\-]+/g,'_').slice(0,50)+'.ics';a.click();URL.revokeObjectURL(url)}
function shareMovieCard(m){var canvas=document.getElementById('mhShareCanvas');if(!canvas||!canvas.getContext){shareMovie(m);return}var ctx=canvas.getContext('2d');var W=canvas.width,H=canvas.height;var g=ctx.createLinearGradient(0,0,W,H);g.addColorStop(0,'#0b0b18');g.addColorStop(.5,'#12203a');g.addColorStop(1,'#0f3460');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);ctx.fillStyle='rgba(0,167,160,.25)';ctx.beginPath();ctx.arc(W*.8,H*.15,220,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.font='700 36px system-ui,sans-serif';ctx.fillText('MOVIE CALENDAR',72,110);ctx.font='800 64px system-ui,sans-serif';var title=String(m.title||'Untitled');var lines=[];var words=title.split(' ');var line='';words.forEach(function(w){var t=line?line+' '+w:w;if(ctx.measureText(t).width>W-140){if(line)lines.push(line);line=w}else line=t});if(line)lines.push(line);lines.slice(0,3).forEach(function(ln,i){ctx.fillText(ln,72,220+i*74)});ctx.font='600 34px system-ui,sans-serif';ctx.fillStyle='rgba(255,255,255,.88)';var y=220+Math.min(lines.length,3)*74+40;var bits=[];if(m.date)bits.push(m.date);if(m.time)bits.push(m.time);if(m.cinema)bits.push(m.cinema);ctx.fillText(bits.join('  ·  '),72,y);var st=getStatus(m.status);ctx.fillStyle='#00d4c0';ctx.font='700 30px system-ui,sans-serif';ctx.fillText(st.emoji+' '+st.label,72,y+60);ctx.fillStyle='rgba(255,255,255,.55)';ctx.font='500 24px system-ui,sans-serif';ctx.fillText('Review Chân Thật',72,H-80);canvas.toBlob(function(blob){if(!blob){shareMovie(m);return}var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=(m.title||'movie').replace(/[^\w\-]+/g,'_').slice(0,50)+'-card.png';a.click();URL.revokeObjectURL(url);var text=[m.title||'Movie',bits.join(' · '),st.label].join('\n');if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text)['catch'](function(){})}},'image/png')}
function renderFavoritesWall(){var sec=document.getElementById('mhFavorites');var grid=document.getElementById('mhFavoritesGrid');if(!sec||!grid)return;var favs=S.movies.filter(function(m){return (m.specials||[]).indexOf('favorite')!==-1||m.favorite===true||m.favorite==='Yes'});if(!favs.length){sec.hidden=true;grid.innerHTML='';return}sec.hidden=false;grid.innerHTML='';favs.slice(0,24).forEach(function(m){var b=document.createElement('button');b.type='button';b.className='mh-fav-card';var poster=m.posterUrl?'<img src="'+es(m.posterUrl)+'" alt="" loading="lazy">':'🎬';b.innerHTML='<div class="mh-fav-card__poster">'+poster+'</div><div class="mh-fav-card__title">'+es(m.title||'Untitled')+'</div>';b.addEventListener('click',function(){if(m.date){var parts=m.date.split('-');S.currentMonthStart=new Date(parseInt(parts[0],10),parseInt(parts[1],10)-1,1);uMLabel();uC();selectCalendarDay(m.date,{force:true,movieId:m.id})}else showSelectedMovie(m)});grid.appendChild(b)})}
function renderYearReview(){var grid=document.getElementById('mhYearGrid');var sub=document.getElementById('mhYearSub');if(!grid)return;var year=new Date().getFullYear();if(sub)sub.textContent='Thống kê năm '+year+' · '+S.movies.length+' phim trong lịch';var inYear=S.movies.filter(function(m){return m.date&&m.date.indexOf(String(year))===0});var cinemas={};var platforms={};var withWho={};var genres={};inYear.forEach(function(m){if(m.cinema)cinemas[m.cinema]=(cinemas[m.cinema]||0)+1;var p=m.platform||m.streamingPlatform;if(p)platforms[p]=(platforms[p]||0)+1;if(m.watchWith)withWho[m.watchWith]=(withWho[m.watchWith]||0)+1;(String(m.genre||'').split(/[,/]/)).forEach(function(g){g=g.trim();if(g)genres[g]=(genres[g]||0)+1})});function top(map){var k=Object.keys(map).sort(function(a,b){return map[b]-map[a]});return k[0]||'—'}var need=S.movies.filter(function(m){return m.status==='need-ticket'}).length;var fav=S.movies.filter(function(m){return (m.specials||[]).indexOf('favorite')!==-1}).length;var stats=[{l:'Phim '+year,v:inYear.length},{l:'Tổng lịch',v:S.movies.length},{l:'Favorites',v:fav},{l:'Need ticket',v:need},{l:'Rạp hay đi',v:top(cinemas)},{l:'Platform',v:top(platforms)},{l:'Xem với',v:top(withWho)},{l:'Genre hot',v:top(genres)}];grid.innerHTML=stats.map(function(s){return '<div class="mh-year-stat"><span class="mh-year-stat__label">'+es(s.l)+'</span><span class="mh-year-stat__value">'+es(String(s.v))+'</span></div>'}).join('')}
function renderCinemaView(){var host=document.getElementById('mhCinemaGroups');if(!host)return;var groups={};S.movies.forEach(function(m){var key=m.cinema||m.platform||m.streamingPlatform||'Other / TBD';if(!groups[key])groups[key]=[];groups[key].push(m)});var keys=Object.keys(groups).sort();if(!keys.length){host.innerHTML='<div class="mh-empty"><div class="mh-empty__icon">🎬</div><p class="mh-empty__text">Chưa có phim</p></div>';return}host.innerHTML=keys.map(function(k){var items=groups[k].slice().sort(function(a,b){return String(a.date||'').localeCompare(String(b.date||''))});var list=items.map(function(m){var st=getStatus(m.status);return '<div class="mh-cinema-item" data-id="'+m.id+'"><div><div class="mh-cinema-item__title">'+es(m.title||'Untitled')+'</div><div class="mh-cinema-item__meta">'+(es(m.date||'—')+(m.time?(' · '+es(m.time)):'')+' · '+st.emoji+' '+st.label)+'</div></div></div>'}).join('');return '<div class="mh-cinema-group"><h4 class="mh-cinema-group__title">'+es(k)+' <small>('+items.length+')</small></h4><div class="mh-cinema-group__list">'+list+'</div></div>'}).join('');host.querySelectorAll('.mh-cinema-item').forEach(function(el){el.addEventListener('click',function(){var id=this.getAttribute('data-id');var m=S.movies.find(function(x){return x.id===id});if(!m)return;if(m.date){var parts=m.date.split('-');S.currentMonthStart=new Date(parseInt(parts[0],10),parseInt(parts[1],10)-1,1);uMLabel();uC();S._view='calendar';setViewMode('calendar');selectCalendarDay(m.date,{force:true,movieId:m.id})}else showSelectedMovie(m)})})}
function setViewMode(mode){S._view=mode||'calendar';var cal=document.getElementById('mhCalendar');var nav=document.querySelector('.mh-nav');var cinema=document.getElementById('mhCinemaView');var list=document.getElementById('mhMovieList');var detail=document.getElementById('mhSelectedPanel');var btnC=document.getElementById('mhViewCalendar');var btnL=document.getElementById('mhViewList');if(btnC){btnC.classList.toggle('is-active',mode==='calendar');btnC.setAttribute('aria-selected',mode==='calendar'?'true':'false')}if(btnL){btnL.classList.toggle('is-active',mode==='list');btnL.setAttribute('aria-selected',mode==='list'?'true':'false')}if(mode==='list'){if(cal)cal.style.display='none';if(nav)nav.style.display='none';if(cinema){cinema.hidden=false}if(list)list.style.display='none';if(detail){detail.hidden=true;detail.classList.remove('is-open')}renderCinemaView()}else{if(cal)cal.style.display='';if(nav)nav.style.display='';if(cinema)cinema.hidden=true;if(list)list.style.display='';uC()}}
function initUxExtras(){var ioPanel=document.getElementById('mhIoPanel');var ioToggle=document.getElementById('mhIoToggle');if(ioToggle&&ioPanel){ioToggle.addEventListener('click',function(){var open=!ioPanel.hidden;ioPanel.hidden=open;ioToggle.setAttribute('aria-expanded',open?'false':'true')})}var nextBtn=document.getElementById('mhNextUpOpen');if(nextBtn)nextBtn.addEventListener('click',function(){if(!S._nextUpId)return;var m=S.movies.find(function(x){return x.id===S._nextUpId});if(!m)return;if(m.date){var parts=m.date.split('-');S.currentMonthStart=new Date(parseInt(parts[0],10),parseInt(parts[1],10)-1,1);uMLabel();uC();selectCalendarDay(m.date,{force:true,movieId:m.id})}else showSelectedMovie(m)});var vc=document.getElementById('mhViewCalendar');var vl=document.getElementById('mhViewList');if(vc)vc.addEventListener('click',function(){setViewMode('calendar')});if(vl)vl.addEventListener('click',function(){setViewMode('list')})}

function initMovieExcelIO() {
  var dl = document.getElementById('mhDownloadTemplate');
  if (dl) dl.addEventListener('click', downloadMovieExcelTemplate);
  var ex = document.getElementById('mhExportExcelBtn');
  if (ex) ex.addEventListener('click', exportMoviesExcel);
  var ib = document.getElementById('mhImportExcelBtn');
  if (ib) ib.addEventListener('click', function () {
    var f = document.getElementById('mhImportFile');
    if (f) f.click();
  });
  var file = document.getElementById('mhImportFile');
  if (file) file.addEventListener('change', function () {
    if (this.files && this.files[0]) mhHandleImportFile(this.files[0]);
  });
  var drop = document.getElementById('mhImportDrop');
  if (drop) {
    drop.addEventListener('click', function (e) {
      if (e.target && e.target.id === 'mhImportFile') return;
      var f = document.getElementById('mhImportFile');
      if (f) f.click();
    });
    drop.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        var f = document.getElementById('mhImportFile');
        if (f) f.click();
      }
    });
    ['dragenter', 'dragover'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation();
        drop.classList.add('is-dragover');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) {
        e.preventDefault(); e.stopPropagation();
        drop.classList.remove('is-dragover');
      });
    });
    drop.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files[0]) mhHandleImportFile(files[0]);
    });
  }
  var cancel = document.getElementById('mhImportCancel');
  if (cancel) cancel.addEventListener('click', mhCloseImportModal);
  var close = document.getElementById('mhImportModalClose');
  if (close) close.addEventListener('click', mhCloseImportModal);
  var bd = document.getElementById('mhImportModalBackdrop');
  if (bd) bd.addEventListener('click', mhCloseImportModal);
  var conf = document.getElementById('mhImportConfirm');
  if (conf) conf.addEventListener('click', mhConfirmImport);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var modal = document.getElementById('mhImportModal');
      if (modal && !modal.hidden) mhCloseImportModal();
    }
  });
}

iG();lV();initUxExtras();initMovieExcelIO();
})();