'use strict';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const icon = window.radarIcon;
const statusLabels = {sent:'Enviada',prepared:'En preparación',reserved:'Reservada',blocked:'Bloqueada',uncertain:'Envío incierto',apartada:'Apartada',discarded:'Descartada',closed:'Retirada'};
const decisionLabels = {pendiente:'Por decidir',priorizar:'Priorizar',revisar:'Revisar',reservar:'Reservar',descartar:'Descartar'};
const collator = new Intl.Collator('es',{sensitivity:'base',numeric:true});
let data, query='', filter='sent', sortKey='date', sortDirection='desc', selected=null, saving=false, loading=false, toastTimer;
const noteDrafts = new Map();

function safeUrl(value){try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u.href:'#';}catch{return '#';}}
function fileUrl(filename){return '/files/'+encodeURIComponent(filename);}
function toDate(value){const d=new Date(value?.length===10?value+'T12:00:00Z':value);return Number.isNaN(d.getTime())?null:d;}
function date(value,time=false){const d=toDate(value);if(!d)return '—';const options={day:'2-digit',month:'short',year:'numeric',...(time?{hour:'2-digit',minute:'2-digit'}:{})};try{return new Intl.DateTimeFormat('es-ES',{...options,timeZone:data?.preferences?.timezone||'UTC'}).format(d);}catch{return new Intl.DateTimeFormat('es-ES',options).format(d);}}
function getJob(id){return data?.catalog.jobs.find(j=>j.id===id);}
function jobStatus(job){
  const a=job.application||{};
  if(a.sent)return 'sent';
  if(a.status==='incierta')return 'uncertain';
  if(a.status==='apartada')return 'apartada';
  if(a.status==='cerrada')return 'closed';
  if(a.status==='descartada'||job.review_outcome==='discarded')return 'discarded';
  if(a.status==='bloqueada'||job.review_outcome==='blocked')return 'blocked';
  if(a.status==='reservada'||job.review_outcome==='reserved')return 'reserved';
  return 'prepared';
}
function badge(job){const key=jobStatus(job);return `<span class="status status-${key}">${statusLabels[key]}</span>`;}
function jobDate(job){return job.application?.sent_at||job.verified_on||job.cv_prepared?.created_on;}
function documentFor(job,initial=false){
  const a=job.application||{};
  const filename=initial?a.cv_sent:a.current_cv?.filename||a.cv_sent||job.cv_prepared?.filename;
  if(!filename)return null;
  const match=[job.cv_prepared,...(job.cv_history||[])].find(c=>c?.filename===filename)||{};
  const current=!initial&&a.current_cv?.filename===filename;
  return {...match,...(current?a.current_cv:{}),filename,kind:current?'CV actualizado en el portal':a.sent?'CV enviado':'CV preparado'};
}
function sortedRows(){
  return data.catalog.jobs.filter(job=>(filter==='all'||jobStatus(job)===filter)&&(!query||normalize([job.company,job.title,job.location,job.mode].join(' ')).includes(normalize(query))))
    .sort((a,b)=>{
      const diff=sortKey==='date'?(toDate(jobDate(a))?.getTime()||0)-(toDate(jobDate(b))?.getTime()||0):collator.compare(sortKey==='status'?statusLabels[jobStatus(a)]:a[sortKey],sortKey==='status'?statusLabels[jobStatus(b)]:b[sortKey]);
      return diff?(sortDirection==='asc'?diff:-diff):collator.compare(a.company,b.company);
    });
}
function renderTable(){
  if(!data)return;
  $('#profile-name').textContent=data.profile?.name||'Mi búsqueda de empleo';
  $('#demo-notice').hidden=!data.catalog.demo;
  const rows=sortedRows();
  $('#rows').innerHTML=rows.length?rows.map(job=>{
    const cv=documentFor(job);
    return `<tr data-job="${esc(job.id)}">
      <td title="${esc(job.title)}"><button class="row-title" data-open="${esc(job.id)}" aria-label="Abrir ${esc(job.title)} en ${esc(job.company)}">${icon('document')}<span>${esc(job.title)}</span></button></td>
      <td class="company-cell" title="${esc(job.company)}">${esc(job.company)}</td>
      <td>${badge(job)}</td>
      <td class="date-cell" title="${job.application?.sent?'Enviada':'Revisada'}: ${esc(date(jobDate(job),!!job.application?.sent_at))}"><time datetime="${esc(jobDate(job))}">${esc(date(jobDate(job)))}</time></td>
      <td><a class="table-link" href="${esc(safeUrl(job.url))}" target="_blank" rel="noopener noreferrer" aria-label="Abrir oferta de ${esc(job.company)}">Abrir ↗</a></td>
      <td>${cv?`<button class="pdf-cell-button" data-pdf="${esc(job.id)}" aria-label="Ver PDF de ${esc(job.company)}" title="${esc(cv.kind)}${cv.version?' · '+esc(cv.version):''}">PDF</button>`:'<span class="no-value" aria-label="Sin PDF">—</span>'}</td>
    </tr>`;
  }).join(''):`<tr><td colspan="6" class="empty-cell">${query?'No hay coincidencias con esta búsqueda.':'No hay candidaturas con este estado.'}</td></tr>`;
  document.querySelectorAll('[data-column]').forEach(th=>{
    const active=th.dataset.column===sortKey;
    th.setAttribute('aria-sort',active?(sortDirection==='asc'?'ascending':'descending'):'none');
    th.querySelector('.sort-arrow').textContent=active?(sortDirection==='asc'?'↑':'↓'):'';
  });
  $('#row-count').textContent=`${rows.length} ${rows.length===1?'registro':'registros'}${filter!=='all'||query?' de '+data.catalog.jobs.length:''}`;
  $('#updated-at').textContent='Actualizado '+date(data.catalog.updated_at||data.catalog.run?.date,true);
  const last=[...(data.daily_runs||[])].filter(r=>r.report_filename).sort((a,b)=>String(b.scheduled_date).localeCompare(String(a.scheduled_date)))[0];
  $('#daily-report').href=last?'/reports/'+encodeURIComponent(last.report_filename):'/api/report';
  $('#daily-report').title=last?'Informe del '+date(last.scheduled_date):'Informe de candidaturas';
  $('#logout').hidden=!data.remote;
}
function noteDraft(id){
  if(!noteDrafts.has(id)){
    const entry=data.reviews.jobs[id]||{};
    const fields={notes:entry.notes||'',decision:entry.decision||'pendiente'};
    noteDrafts.set(id,{...fields,original:JSON.stringify(fields)});
  }
  return noteDrafts.get(id);
}
function draftChanged(entry){return JSON.stringify({notes:entry.notes,decision:entry.decision})!==entry.original;}
function dirtyNotes(){return [...noteDrafts.values()].some(draftChanged);}
function updateNoteControls(){
  if(!selected||!$('#save-note'))return;
  const dirty=draftChanged(noteDraft(selected));
  $('#save-note').disabled=saving||!dirty;
  $('#job-notes').disabled=saving;$('#job-decision').disabled=saving;
  $('#save-status').textContent=saving?'Guardando…':dirty?'Sin guardar':'Guardado';
}
function detailSection(title,content){return content?`<section class="detail-section"><h3>${esc(title)}</h3>${content}</section>`:'';}
function bullets(items){return items?.length?`<ul>${items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:'';}
function openJob(id){
  const job=getJob(id);if(!job)return;
  selected=id;
  const a=job.application||{},analysis=job.analysis||{},cv=documentFor(job),entry=noteDraft(id),stored=data.reviews.jobs[id]||{};
  const initial=a.current_cv&&a.cv_sent&&a.current_cv.filename!==a.cv_sent;
  const receipt=a.evidence_file?'/receipts/'+encodeURIComponent(a.evidence_file.split(/[\\/]/).pop()):null;
  $('#job-content').innerHTML=`<p class="company-eyebrow">${esc(job.company)}</p><h2 id="job-title">${esc(job.title)}</h2>
    <dl class="properties"><dt>Estado</dt><dd>${badge(job)}</dd><dt>${a.sent?'Enviada el':'Revisada el'}</dt><dd class="date-value">${esc(date(jobDate(job),!!a.sent_at))}</dd><dt>Modalidad</dt><dd>${esc(job.mode)} · ${esc(job.location)}</dd><dt>Salario</dt><dd>${esc(job.salary?.label||'No publicado')}</dd>${cv?`<dt>Currículum</dt><dd>${esc(cv.kind)}${cv.version?' · '+esc(cv.version):''}</dd>`:''}</dl>
    <div class="modal-links"><a class="small-button" href="${esc(safeUrl(job.url))}" target="_blank" rel="noopener noreferrer">Ver oferta ${icon('arrow')}</a>${cv?`<button class="small-button" data-pdf="${esc(id)}">${icon('document')} Ver PDF</button>`:''}${receipt?`<a class="quiet-link" href="${receipt}" target="_blank" rel="noopener">Justificante ↗</a>`:''}</div>
    ${detailSection('Por qué esta oferta',`<p>${esc(job.why||analysis.summary||'Pendiente de análisis.')}</p>`)}
    ${detailSection('Lo que encaja',bullets(job.strengths))}
    ${detailSection('Lo que falta confirmar',bullets(job.gaps))}
    ${detailSection('El CV para esta oferta',`<p>${esc(job.cv_prepared?.tailoring||analysis.cv_plan||'Todavía no hay un CV específico.')}</p>${initial?`<p class="source-note">El CV actual del portal se actualizó después del envío. <button class="cv-history-link" data-pdf="${esc(id)}" data-initial="true">Ver CV de la inscripción inicial</button>.</p>`:''}`)}
    ${detailSection('Siguiente paso',`<p>${esc(job.next_step||'Pendiente de concretar.')}</p>`)}
    <section class="detail-section"><label for="job-notes" class="note-label">Mis notas</label><textarea id="job-notes" maxlength="16000" placeholder="Algo que quieras recordar…">${esc(entry.notes)}</textarea><div class="notes-actions"><label class="decision-label" for="job-decision">Mi decisión<select id="job-decision">${Object.entries(decisionLabels).map(([key,label])=>`<option value="${key}"${key===entry.decision?' selected':''}>${label}</option>`).join('')}</select></label><div class="save-group"><span id="save-status" class="save-status" role="status"></span><button id="save-note" class="small-button primary">Guardar</button></div></div><p id="note-error" class="note-error" role="alert" hidden></p></section>
    ${stored.cv_notes?detailSection('Mis notas sobre el CV',`<p>${esc(stored.cv_notes)}</p>`):''}
    ${stored.evidence_notes?detailSection('Contexto que aporté',`<p>${esc(stored.evidence_notes)}</p>`):''}
    <p class="source-note">Revisión: ${esc(date(job.verified_on))}. ${esc(job.published_label||'')}</p>`;
  updateNoteControls();
  if(!$('#job-dialog').open)$('#job-dialog').showModal();
  $('#job-content').scrollTop=0;
  syncDialogState();
}
function openPdf(id,initial=false){
  const job=getJob(id),cv=job&&documentFor(job,initial);if(!cv)return;
  const url=fileUrl(cv.filename);
  $('#pdf-title').textContent='CV · '+job.company;
  $('#pdf-caption').textContent=cv.kind+(cv.version?' · '+cv.version:'')+(initial?' · inscripción inicial':'')+' · Vista previa de la primera página';
  $('#pdf-external').href=url;$('#pdf-download').href=url+'?download=1';$('#pdf-download').download=cv.filename;
  $('#pdf-content').innerHTML=`<p class="pdf-loading" role="status">Cargando el currículum…</p><img class="pdf-page" src="/preview/${encodeURIComponent(cv.filename)}" alt="Primera página del currículum de ${esc(job.company)}"><p class="pdf-preview-error" role="alert" hidden>No se ha podido cargar la vista previa. Puedes descargar el PDF original desde el botón de arriba.</p>`;
  const preview=$('#pdf-content img'),loading=$('#pdf-content .pdf-loading'),error=$('#pdf-content .pdf-preview-error');
  preview.addEventListener('load',()=>{loading.hidden=true;});
  preview.addEventListener('error',()=>{loading.hidden=true;preview.hidden=true;error.hidden=false;});
  $('#pdf-content').scrollTop=0;
  if(!$('#pdf-dialog').open)$('#pdf-dialog').showModal();
  syncDialogState();
}
function syncDialogState(){document.body.classList.toggle('has-dialog',$('#job-dialog').open||$('#pdf-dialog').open);}
function closeDialog(kind){
  const dialog=$('#'+kind+'-dialog');dialog.close();
  if(kind==='pdf')$('#pdf-content').replaceChildren();
  syncDialogState();
}
function toast(message,error=false){clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').className='toast show'+(error?' error':'');toastTimer=setTimeout(()=>{$('#toast').className='toast';},error?8000:3500);}
async function saveNote(){
  if(saving||!selected)return;
  const id=selected,job=getJob(id),draft=noteDraft(id),stored=data.reviews.jobs[id]||{};
  if(!draftChanged(draft))return;
  saving=true;updateNoteControls();$('#note-error').hidden=true;
  const cv=job.cv_prepared,stale=stored.cv_reference&&stored.cv_reference!==cv?.sha256;
  const fields={notes:draft.notes,decision:draft.decision,cv_review:stale?'pendiente':stored.cv_review||'pendiente',cv_notes:stored.cv_notes||'',evidence_notes:stored.evidence_notes||'',cv_reference:cv?.sha256||null,revision:data.reviews.revision};
  try{
    const response=await fetch('/api/jobs/'+encodeURIComponent(id),{method:'POST',headers:{'Content-Type':'application/json','X-Radar-Token':data.csrf},body:JSON.stringify(fields)});
    if(response.status===401){throw new Error('La sesión ha caducado. Copia las notas pendientes y vuelve a abrir la app para entrar con Telegram.');}
    const result=await response.json();if(!response.ok)throw new Error(result.error||'No se han podido guardar las notas.');
    data.reviews=result.reviews;noteDrafts.delete(id);noteDraft(id);renderTable();
  }catch(error){if(selected===id){$('#note-error').hidden=false;$('#note-error').textContent=error.message;}else toast(error.message,true);}
  finally{saving=false;updateNoteControls();}
}
async function load(){
  if(loading)return;
  if(dirtyNotes()){
    const id=[...noteDrafts].find(([,draft])=>draftChanged(draft))[0];openJob(id);
    $('#note-error').hidden=false;$('#note-error').textContent='Guarda los cambios antes de actualizar la tabla.';return;
  }
  loading=true;$('#refresh').disabled=true;
  try{
    const response=await fetch('/api/data');if(response.status===401){location.replace('/login');return;}if(!response.ok)throw new Error('No se han podido cargar las candidaturas.');
    const next=await response.json();if(!Array.isArray(next.catalog?.jobs))throw new Error('No se ha podido leer la tabla.');
    if(!data&&(next.catalog.demo||!next.catalog.jobs.some(job=>job.application?.sent))){filter='all';$('#status-filter').value='all';}
    data=next;noteDrafts.clear();renderTable();
  }catch(error){if(data)toast(error.message,true);else $('#rows').innerHTML=`<tr><td colspan="6" class="empty-cell">${esc(error.message)} Pulsa Actualizar para volver a intentarlo.</td></tr>`;}
  finally{loading=false;$('#refresh').disabled=false;}
}

$('#search-icon').innerHTML=icon('search');$('#date-icon').innerHTML=icon('calendar');$('#refresh').innerHTML=icon('refresh');
$('#page-icon').innerHTML=icon('briefcase');$('#status-icon').innerHTML=icon('status');$('#logout').innerHTML=icon('logout');
$('#logout').addEventListener('click',async()=>{
  if(dirtyNotes()){toast('Guarda las notas pendientes antes de cerrar sesión.',true);return;}
  try{const r=await fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json','X-Radar-Token':data.csrf},body:'{}'});if(!r.ok)throw new Error();location.replace('/login');}
  catch{toast('No se ha podido cerrar la sesión. Vuelve a intentarlo.',true);}
});
document.querySelectorAll('[data-close]').forEach(button=>{button.innerHTML=icon('close');});
$('#search').addEventListener('input',event=>{query=event.target.value;renderTable();});
$('#status-filter').addEventListener('change',event=>{filter=event.target.value;renderTable();});
$('#refresh').addEventListener('click',load);
document.addEventListener('click',event=>{
  const close=event.target.closest('[data-close]');if(close){closeDialog(close.dataset.close);return;}
  const pdf=event.target.closest('[data-pdf]');if(pdf){openPdf(pdf.dataset.pdf,pdf.dataset.initial==='true');return;}
  const sort=event.target.closest('[data-sort]');if(sort){const key=sort.dataset.sort;sortDirection=sortKey===key?(sortDirection==='asc'?'desc':'asc'):key==='date'?'desc':'asc';sortKey=key;renderTable();return;}
  if(event.target.closest('#save-note')){saveNote();return;}
  if(event.target.closest('a'))return;
  const row=event.target.closest('[data-job]');if(row)openJob(row.dataset.job);
});
document.addEventListener('input',event=>{if(event.target.id==='job-notes'){noteDraft(selected).notes=event.target.value;updateNoteControls();}});
document.addEventListener('change',event=>{if(event.target.id==='job-decision'){noteDraft(selected).decision=event.target.value;updateNoteControls();}});
for(const kind of ['job','pdf']){
  const dialog=$('#'+kind+'-dialog');
  dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog(kind);});
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeDialog(kind);});
}
window.addEventListener('beforeunload',event=>{if(dirtyNotes()){event.preventDefault();event.returnValue='';}});
load();
