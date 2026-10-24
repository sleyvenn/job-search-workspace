#!/usr/bin/env python3
"""Portable entry point. Python 3.11+; no dependencies for the web app."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from lib.workspace import Workspace, WorkspaceError, read

BASE=Path(__file__).resolve().parent


def env_file():
    path=BASE/'.env'
    allowed={'WORKSPACE_PUBLIC_URL','WORKSPACE_BRAND','WORKSPACE_DIR','TELEGRAM_BOT_NAME',
             'TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID','PDFTOPPM'}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'): continue
            key, separator, value=line.partition('=')
            if separator and key.strip() in allowed:
                value=value.strip()
                if len(value)>1 and value[0]==value[-1] and value[0] in "\"'": value=value[1:-1]
                os.environ.setdefault(key.strip(),value)


def serve(workspace, port, demo=False):
    if not (workspace.root/'state.json').exists():
        raise WorkspaceError('Inicializa el espacio primero: python run.py init')
    os.environ['WORKSPACE_DIR']=str(workspace.root)
    if demo:
        # A demo never consumes the owner's production login settings.
        os.environ.pop('WORKSPACE_PUBLIC_URL',None)
    sys.path.insert(0,str(BASE/'app'))
    from server import RadarServer
    server=RadarServer(('127.0.0.1',port),workspace.root/'reviews')
    print(f'Job Search Workspace: http://127.0.0.1:{server.server_port}',flush=True)
    print('Datos: '+str(workspace.root),flush=True)
    try: server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt: pass
    finally: server.server_close()


def demo(workspace, port):
    if not (workspace.root/'state.json').exists():
        candidate=read(BASE/'examples/candidate.demo.json')
        preferences=read(BASE/'examples/preferences.template.json')
        preferences['salary']['minimum_eur_gross_annual']=35000
        workspace.initialize(candidate,preferences,demo=True)
        first=read(BASE/'examples/job.demo.json')
        workspace.add_job(first)
        workspace.register_cv(first['id'],BASE/'examples/cv.demo.pdf',
                              'CV ficticio: prioriza aplicaciones, integraciones y necesidades de usuarios.',
                              content=read(BASE/'examples/cv.demo.json'))
        second={**first,'id':'demo-automation','external_ids':['demo:automation'],
                'company':'Norte Ejemplo','title':'Automation Engineer','url':'https://example.com/jobs/automation',
                'salary':{'label':'No publicado','minimum':None,'maximum':None},
                'why':'Ejemplo de encaje con integraciones; queda pendiente confirmar salario e inglés hablado.'}
        workspace.add_job(second)
        workspace.record_outcome(second['id'],'reservada','Confirmar salario y nivel de inglés conversacional.')
        third={**first,'id':'demo-support','external_ids':['demo:support'],'company':'Sur Ejemplo',
               'title':'Técnico de soporte','url':'https://example.com/jobs/support',
               'salary':{'label':'24.000–28.000 €/año · ejemplo','minimum':24000,'maximum':28000},
               'why':'Ejemplo descartado porque el máximo publicado queda por debajo del mínimo configurado.'}
        workspace.add_job(third)
        workspace.record_outcome(third['id'],'descartada','El máximo de 28.000 € está por debajo del mínimo de la demo.')
        workspace.report()
    elif not workspace.state().get('demo'):
        raise WorkspaceError('La carpeta contiene datos reales. No se abre como demo.')
    serve(workspace,port,demo=True)


def main():
    if sys.version_info < (3,11): raise WorkspaceError('Se requiere Python 3.11 o posterior.')
    env_file()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,help='Carpeta privada; por defecto ./workspace')
    commands=parser.add_subparsers(dest='command',required=True)
    initialize=commands.add_parser('init',help='Crear un espacio privado vacío')
    initialize.add_argument('--profile',type=Path)
    initialize.add_argument('--preferences',type=Path)
    bootstrap=commands.add_parser('bootstrap',help='Preparar y arrancar la app para el agente, sin sobrescribir datos')
    bootstrap.add_argument('--port',type=int,default=8765)
    for command in ['serve','demo']:
        p=commands.add_parser(command,help='Abrir la app local' if command=='serve' else 'Probar con datos ficticios')
        p.add_argument('--port',type=int,default=8765)
    commands.add_parser('doctor',help='Comprobar datos y dependencias')
    commands.add_parser('validate',help='Verificar integridad de PDF y justificantes')
    commands.add_parser('report',help='Generar informe de los registros actuales')
    add=commands.add_parser('add-job',help='Añadir una oferta analizada sin duplicados')
    add.add_argument('--file',type=Path,required=True)
    for command in ['attach-cv','create-cv']:
        p=commands.add_parser(command)
        p.add_argument('--job',required=True)
        p.add_argument('--file',type=Path,required=True,help='PDF externo' if command=='attach-cv' else 'JSON de contenido con source_refs')
        p.add_argument('--why',required=True,help='Qué se ha adaptado y por qué')
        p.add_argument('--language',default='es')
    approval=commands.add_parser('approve',help='Registrar una autorización real del usuario para el PDF actual')
    approval.add_argument('--job',required=True)
    approval.add_argument('--note',required=True)
    ready=commands.add_parser('check-ready',help='Comprobar antes de completar un formulario externo')
    ready.add_argument('--job',required=True)
    outcome=commands.add_parser('record-outcome')
    outcome.add_argument('--job',required=True)
    outcome.add_argument('--status',required=True,choices=['reservada','descartada','bloqueada','incierta','pendiente'])
    outcome.add_argument('--reason',required=True)
    application=commands.add_parser('record-application',help='Registrar una confirmación real; no envía solicitudes')
    application.add_argument('--job',required=True)
    application.add_argument('--cv',required=True,help='Nombre exacto del PDF que se subió')
    application.add_argument('--sha256',required=True,help='SHA-256 del PDF subido')
    application.add_argument('--receipt',type=Path,required=True)
    application.add_argument('--confirmation',required=True)
    application.add_argument('--channel',required=True)
    application.add_argument('--at',required=True,help='Fecha ISO 8601 con zona horaria')
    application.add_argument('--answers',type=Path)
    options=parser.parse_args()
    default='workspace-demo' if options.command=='demo' else 'workspace'
    workspace=Workspace(options.workspace or os.environ.get('WORKSPACE_DIR') or BASE/default)
    command=options.command
    if command=='init':
        result=workspace.initialize(read(options.profile or BASE/'examples/candidate.template.json'),
                                    read(options.preferences or BASE/'examples/preferences.template.json'))
        result['next']='Completa candidate.json y preferences.json; después ejecuta python run.py serve.'
    elif command=='bootstrap':
        from lib.bootstrap import start
        result=start(workspace,BASE,options.port)
    elif command=='serve': return serve(workspace,options.port)
    elif command=='demo': return demo(workspace,options.port)
    elif command=='add-job': result=workspace.add_job(read(options.file))
    elif command=='attach-cv': result=workspace.register_cv(options.job,options.file,options.why,options.language)
    elif command=='create-cv':
        from lib.cv import create
        result=create(workspace,options.job,read(options.file),options.why,options.language)
        result['next']='Abre o renderiza todas las páginas del PDF antes de aprobarlo.'
    elif command=='approve': result=workspace.approve(options.job,options.note)
    elif command=='check-ready': result=workspace.ready(options.job)
    elif command=='record-outcome': result=workspace.record_outcome(options.job,options.status,options.reason)
    elif command=='record-application':
        result=workspace.record_application(options.job,options.confirmation,options.receipt,options.channel,
                                             options.at,options.cv,options.sha256,read(options.answers) if options.answers else None)
    elif command=='report': result=workspace.report()
    elif command=='validate': result=workspace.validate()
    elif command=='doctor':
        try:
            import reportlab
            pdf_generator=True
        except ImportError: pdf_generator=False
        result={'python':sys.version.split()[0], 'workspace':str(workspace.root),
                'initialized':(workspace.root/'state.json').exists(),'pdf_generator':pdf_generator,
                'pdf_preview':bool(shutil.which(os.environ.get('PDFTOPPM','pdftoppm'))),
                'browser':'El agente debe comprobar su propio acceso al navegador y a los portales.',
                'auth':'Telegram OTP' if os.environ.get('WORKSPACE_PUBLIC_URL') else 'Solo localhost'}
        if result['initialized']: result['integrity']=workspace.validate()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if isinstance(result,dict) and result.get('valid') is False: return 1
    return 0


if __name__=='__main__':
    try: sys.exit(main() or 0)
    except (WorkspaceError,FileNotFoundError,KeyError,json.JSONDecodeError) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
