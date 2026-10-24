"""Local records, immutable documents and explicit submission evidence.

This module never contacts employers or sends job applications.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


class WorkspaceError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(4) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                           if not unicodedata.combining(c)).split())


def canonical_url(value):
    parts = urlsplit(value)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise WorkspaceError('La oferta necesita una URL web válida sin credenciales.')
    if parts.hostname in {'linkedin.com', 'www.linkedin.com'}:
        match = re.search(r'/jobs/view/(\d+)', parts.path)
        if match: return 'https://www.linkedin.com/jobs/view/' + match[1] + '/'
    removed = {'source','ref','referrer','referral','trackingid','trk','gh_src','fbclid','gclid'}
    query = [(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in removed]
    if any(re.search(r'token|password|secret|session|auth', k, re.I) for k,_ in query):
        raise WorkspaceError('Guarda la URL pública de la oferta, sin enlaces de acceso ni tokens.')
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()

    @contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / '.writer.lock').open('a+b') as handle:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX)
            try: yield
            finally:
                if os.name == 'nt':
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else: fcntl.flock(handle, fcntl.LOCK_UN)

    def state(self):
        return read(self.root / 'state.json')

    def write_state(self, state):
        state['updated_at'] = now()
        save(self.root / 'state.json', state)

    def job(self, identifier, state=None):
        match = next((j for j in (state or self.state())['jobs'] if j['id'] == identifier), None)
        if not match: raise WorkspaceError('Oferta desconocida: ' + identifier)
        return match

    def initialize(self, candidate, preferences, demo=False):
        with self.lock():
            if (self.root / 'state.json').exists():
                raise WorkspaceError('Este espacio ya existe. No se sobrescribe.')
            if any(p.name != '.writer.lock' for p in self.root.iterdir()):
                raise WorkspaceError('Elige una carpeta vacía para el espacio privado.')
            facts = candidate.get('facts', [])
            if len({f['id'] for f in facts}) != len(facts):
                raise WorkspaceError('Los identificadores de los hechos del perfil deben ser únicos.')
            for folder in ['documents','receipts','reports','reviews','cv-content']:
                (self.root / folder).mkdir(mode=0o700)
            for name, value in {
                'candidate.json': candidate, 'preferences.json': preferences,
                'state.json': {'schema_version':1,'demo':demo,'updated_at':now(),'master_cv':None,'jobs':[]},
                'analysis.json': {}, 'cv-versions.json': {'schema_version':1,'variants':[]},
                'runs.json': {'schema_version':1,'runs':[]}, 'trial.json': {},
                'reviews/decisions.json': {'schema_version':1,'revision':0,'jobs':{},'profile':{},'history':[]},
            }.items(): save(self.root / name, value)
        return {'initialized':str(self.root),'demo':demo}

    def add_job(self, incoming):
        identifier = incoming.get('id', '')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{1,100}', identifier):
            raise WorkspaceError('Usa un ID estable con letras, números, guiones o guiones bajos.')
        for field in ['company','title','url','location','mode','why','verified_on']:
            if not isinstance(incoming.get(field), str) or not incoming[field].strip():
                raise WorkspaceError('Falta el campo: ' + field)
        datetime.fromisoformat(incoming['verified_on'])
        canonical = canonical_url(incoming['url'])
        external_ids = set(incoming.get('external_ids', []))
        if any(not isinstance(v, str) for v in external_ids):
            raise WorkspaceError('external_ids debe contener identificadores de texto.')
        if incoming.get('application', {}).get('sent'):
            raise WorkspaceError('Usa record-application con el PDF y el justificante para registrar un envío.')
        with self.lock():
            state = self.state()
            triplet = tuple(normalized(incoming[k]) for k in ['company','title','location'])
            for previous in state['jobs']:
                if (previous['id'] == identifier or previous.get('canonical_url', canonical_url(previous['url'])) == canonical
                    or tuple(normalized(previous[k]) for k in ['company','title','location']) == triplet
                    or external_ids.intersection(previous.get('external_ids', []))):
                    raise WorkspaceError('Oferta ya registrada: ' + previous['id'])
            job = {**incoming, 'canonical_url':canonical, 'url':canonical,
                   'published_label':incoming.get('published_label','Fecha de publicación pendiente de confirmar'),
                   'salary':incoming.get('salary',{'label':'No publicado','minimum':None,'maximum':None}),
                   'strengths':incoming.get('strengths',[]), 'gaps':incoming.get('gaps',[]),
                   'decision':'revisar', 'next_step':incoming.get('next_step','Revisar encaje y preparar CV.'),
                   'cv_prepared':None, 'cv_history':[], 'application':{'sent':False,'status':'pendiente','label':'Pendiente de revisión'}}
            state['jobs'].append(job)
            analysis = read(self.root / 'analysis.json')
            analysis[identifier] = incoming.get('analysis', {})
            save(self.root / 'analysis.json', analysis)
            self.write_state(state)
        return job

    def record_outcome(self, identifier, status, reason):
        if status not in {'reservada','descartada','bloqueada','incierta','pendiente'}:
            raise WorkspaceError('Estado no admitido.')
        if not reason.strip(): raise WorkspaceError('Describe el motivo observado.')
        with self.lock():
            state = self.state(); job = self.job(identifier, state)
            if job.get('application', {}).get('sent'):
                raise WorkspaceError('Un envío confirmado se conserva; registra su seguimiento aparte.')
            job['application'] = {'sent':False,'status':status,'label':reason,'updated_at':now()}
            job['next_step'] = reason
            self.write_state(state)
        return job['application']

    def register_cv(self, identifier, source, tailoring, language='es', content=None):
        source = Path(source)
        if not source.read_bytes().startswith(b'%PDF-'):
            raise WorkspaceError('El archivo no es un PDF.')
        if not tailoring.strip(): raise WorkspaceError('Explica qué se ha adaptado y por qué.')
        with self.lock():
            state = self.state(); job = self.job(identifier, state)
            version = 1
            stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            while (self.root/'documents'/f'{identifier}_{stamp}_v{version}.pdf').exists(): version += 1
            filename = f'{identifier}_{stamp}_v{version}.pdf'
            target = self.root / 'documents' / filename
            with target.open('xb') as handle: handle.write(source.read_bytes())
            cv = {'filename':filename,'sha256':digest(target),'version':f'v{version}',
                  'language':language,'created_on':now(),'tailoring':tailoring}
            if job.get('cv_prepared'): job['cv_history'].append(job['cv_prepared'])
            job['cv_prepared'] = cv
            job.pop('authorization', None)
            versions = read(self.root / 'cv-versions.json')
            versions['variants'].append({'job_id':identifier,**cv})
            if content is not None: save(self.root / 'cv-content' / (filename+'.json'), content)
            save(self.root / 'cv-versions.json', versions)
            self.write_state(state)
        return cv

    def approve(self, identifier, note):
        if len(note.strip()) < 10:
            raise WorkspaceError('Registra la instrucción real del usuario que autoriza este envío.')
        with self.lock():
            state=self.state(); job=self.job(identifier,state)
            if job.get('application',{}).get('sent'): raise WorkspaceError('La candidatura ya consta enviada.')
            cv=job.get('cv_prepared')
            if not cv: raise WorkspaceError('Prepara y revisa el PDF antes de registrar la autorización.')
            if digest(self.root/'documents'/cv['filename']) != cv['sha256']:
                raise WorkspaceError('El PDF ha cambiado desde su registro.')
            job['authorization']={'note':note,'recorded_at':now(),'cv_sha256':cv['sha256'],
                                  'expires_at':(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()}
            self.write_state(state)
        return job['authorization']

    def ready(self, identifier):
        job=self.job(identifier)
        if job.get('application',{}).get('sent'): raise WorkspaceError('Ya enviada. No repitas el formulario.')
        if job.get('application',{}).get('status')=='incierta':
            raise WorkspaceError('El envío es incierto. Comprueba el portal antes de cualquier reintento.')
        cv=job.get('cv_prepared'); approval=job.get('authorization',{})
        if not cv or approval.get('cv_sha256') != cv['sha256']:
            raise WorkspaceError('Falta autorización del usuario para esta versión del PDF.')
        if datetime.fromisoformat(approval['expires_at']) <= datetime.now(timezone.utc):
            raise WorkspaceError('La autorización ha caducado; comprueba la vigencia y la instrucción del usuario.')
        if digest(self.root/'documents'/cv['filename']) != cv['sha256']:
            raise WorkspaceError('El PDF registrado ha cambiado.')
        preferences=read(self.root/'preferences.json')
        minimum=preferences.get('salary',{}).get('minimum_eur_gross_annual')
        maximum=job.get('salary',{}).get('maximum')
        if minimum is not None and maximum is not None and maximum < minimum:
            raise WorkspaceError('El máximo publicado está por debajo del mínimo salarial configurado.')
        return {'ready':True,'job_id':identifier,'cv':cv,
                'reminder':'Verifica vigencia, modalidad, condiciones y sesión del portal antes del envío.'}

    def record_application(self, identifier, confirmation, receipt, channel, observed_at, cv_filename, cv_sha256, answers=None):
        if len(confirmation.strip()) < 10 or not channel.strip():
            raise WorkspaceError('Registra la confirmación visible y el canal.')
        observed=datetime.fromisoformat(observed_at)
        if observed.tzinfo is None: raise WorkspaceError('La fecha de envío debe incluir zona horaria.')
        if observed > datetime.now(timezone.utc)+timedelta(minutes=5):
            raise WorkspaceError('La fecha observada no puede estar en el futuro.')
        receipt=Path(receipt)
        raw=receipt.read_bytes()
        suffix='.png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if raw.startswith(b'\xff\xd8\xff') else None
        if not suffix: raise WorkspaceError('Guarda una captura PNG o JPEG real como justificante.')
        with self.lock():
            state=self.state(); job=self.job(identifier,state)
            if job.get('application',{}).get('sent'):
                if job['application'].get('cv_sha256')!=cv_sha256 or job['application'].get('cv_sent')!=cv_filename:
                    raise WorkspaceError('Ya existe un envío con otro PDF; no se sobrescribe.')
                return {'already_recorded':True,'application':job['application']}
            cv=next((cv for cv in [job.get('cv_prepared')]+job.get('cv_history',[]) if cv and cv['filename']==cv_filename and cv['sha256']==cv_sha256),None)
            if not cv or digest(self.root/'documents'/cv['filename']) != cv_sha256:
                raise WorkspaceError('Falta el PDF exacto de la solicitud o se ha modificado.')
            # Recording observed reality must remain possible after a late confirmation.
            # Authorization is checked before submission by check-ready, not fabricated here.
            proof=f'{identifier}_{secrets.token_hex(4)}{suffix}'
            with (self.root/'receipts'/proof).open('xb') as handle: handle.write(raw)
            application={'sent':True,'sent_at':observed.isoformat(),'status':'enviada','label':'Envío confirmado',
                         'cv_sent':cv['filename'],'cv_sha256':cv['sha256'],'channel':channel,
                         'evidence':confirmation,'evidence_file':proof,'evidence_sha256':hashlib.sha256(raw).hexdigest(),
                         'answers':answers or {},'updated_at':now()}
            if job.get('authorization',{}).get('cv_sha256') != cv['sha256']:
                application['audit_note']='No hay autorización registrada para este PDF. Revisar el proceso; no ocultar el envío observado.'
            job['application']=application
            job['next_step']='Revisar respuestas reales del portal o del correo; no reenviar la candidatura.'
            self.write_state(state)
        return application

    def validate(self):
        state=self.state(); problems=[]; ids=set(); sent=0
        for name in ['candidate','preferences','analysis','cv-versions','runs','trial']:
            read(self.root/(name+'.json'))
        for job in state['jobs']:
            if job['id'] in ids: problems.append('ID duplicado: '+job['id'])
            ids.add(job['id'])
            for cv in [job.get('cv_prepared')]+job.get('cv_history',[]):
                if not cv: continue
                path=self.root/'documents'/cv['filename']
                if Path(cv['filename']).name != cv['filename'] or not path.exists() or digest(path)!=cv['sha256']:
                    problems.append('PDF ausente o modificado: '+cv['filename'])
            app=job.get('application',{})
            if app.get('sent'):
                sent+=1
                for folder,key,hashkey in [('documents','cv_sent','cv_sha256'),('receipts','evidence_file','evidence_sha256')]:
                    name=app.get(key,''); path=self.root/folder/name
                    if Path(name).name!=name or not path.is_file() or digest(path)!=app.get(hashkey):
                        problems.append('Envío sin documento verificable: '+job['id']+' / '+key)
        return {'valid':not problems,'jobs':len(ids),'sent':sent,'problems':problems}

    def report(self):
        state=self.state(); today=datetime.now(timezone.utc).date().isoformat()
        lines=['JOB SEARCH WORKSPACE', 'Generado: '+now(),
               'Informe de registros observados; no implica que se haya ejecutado una búsqueda automática.', '']
        for job in state['jobs']:
            app=job.get('application',{}); cv=job.get('cv_prepared')
            lines += [job['company']+' · '+job['title'],job['url'],
                      'Estado: '+('Enviada' if app.get('sent') else app.get('status','pendiente')),
                      'Motivo: '+job['why'],'Por confirmar: '+'; '.join(job['gaps']),
                      'CV: '+(app.get('cv_sent') or (cv or {}).get('filename','Sin preparar')),
                      'Confirmación: '+app.get('evidence','Sin envío confirmado'),
                      'Siguiente paso: '+job['next_step'],'']
        filename='Informe_'+today+'_'+datetime.now(timezone.utc).strftime('%H%M%S_%f')+'_'+secrets.token_hex(3)+'.txt'
        with self.lock():
            with (self.root/'reports'/filename).open('x',encoding='utf-8') as handle:
                handle.write('\n'.join(lines))
            runs=read(self.root/'runs.json')
            runs['runs'].append({'id':'report-'+secrets.token_hex(5),'scheduled_date':today,'status':'report',
                                 'summary':'Informe generado a partir de los registros actuales.', 'report_filename':filename})
            save(self.root/'runs.json',runs)
        return {'report':str(self.root/'reports'/filename),'jobs':len(state['jobs'])}
