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
from lib.records import normalize_application_status

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
        raise WorkspaceError('Initialize the workspace first: python run.py init')
    os.environ['WORKSPACE_DIR']=str(workspace.root)
    if demo:
        # A demo never consumes the owner's production login settings.
        os.environ.pop('WORKSPACE_PUBLIC_URL',None)
    sys.path.insert(0,str(BASE/'app'))
    from server import RadarServer
    server=RadarServer(('127.0.0.1',port),workspace.root/'reviews')
    print(f'Job Search Workspace: http://127.0.0.1:{server.server_port}',flush=True)
    print('Data: '+str(workspace.root),flush=True)
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
                              'Fictional CV: highlights applications, integrations and user needs.',
                              content=read(BASE/'examples/cv.demo.json'))
        second={**first,'id':'demo-automation','external_ids':['demo:automation'],
                'company':'North Example','title':'Automation Engineer','url':'https://example.com/jobs/automation',
                'salary':{'label':'Not disclosed','minimum':None,'maximum':None},
                'why':'Example match for integrations; salary and spoken English requirements need confirmation.'}
        workspace.add_job(second)
        workspace.record_outcome(second['id'],'reserved','Confirm salary and conversational English requirements.')
        third={**first,'id':'demo-support','external_ids':['demo:support'],'company':'South Example',
               'title':'IT Support Technician','url':'https://example.com/jobs/support',
               'salary':{'label':'€24,000-28,000/year · example','minimum':24000,'maximum':28000},
               'why':'Example discarded because the published maximum is below the configured minimum.'}
        workspace.add_job(third)
        workspace.record_outcome(third['id'],'discarded','The €28,000 maximum is below the demo minimum.')
        workspace.report()
    elif not workspace.state().get('demo'):
        raise WorkspaceError('This folder contains real records and cannot be opened as a demo.')
    serve(workspace,port,demo=True)


def main():
    if sys.version_info < (3,11): raise WorkspaceError('Python 3.11 or later is required.')
    env_file()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,help='Private folder; defaults to ./workspace')
    commands=parser.add_subparsers(dest='command',required=True)
    initialize=commands.add_parser('init',help='Create an empty private workspace')
    initialize.add_argument('--profile',type=Path)
    initialize.add_argument('--preferences',type=Path)
    bootstrap=commands.add_parser('bootstrap',help='Set up and start the app for the agent without overwriting data')
    bootstrap.add_argument('--port',type=int,default=8765)
    for command in ['serve','demo']:
        p=commands.add_parser(command,help='Start the local app' if command=='serve' else 'Try the app with fictional data')
        p.add_argument('--port',type=int,default=8765)
    commands.add_parser('doctor',help='Check data and dependencies')
    commands.add_parser('validate',help='Check PDF and receipt integrity')
    commands.add_parser('report',help='Report on the current records')
    add=commands.add_parser('add-job',help='Add an assessed job without duplicates')
    add.add_argument('--file',type=Path,required=True)
    for command in ['attach-cv','create-cv']:
        p=commands.add_parser(command)
        p.add_argument('--job',required=True)
        p.add_argument('--file',type=Path,required=True,help='Existing PDF' if command=='attach-cv' else 'Content JSON with source_refs')
        p.add_argument('--why',required=True,help='What was tailored and why')
        p.add_argument('--language',default='en')
    approval=commands.add_parser('approve',help='Record real user authorization for the current PDF')
    approval.add_argument('--job',required=True)
    approval.add_argument('--note',required=True)
    ready=commands.add_parser('check-ready',help='Check readiness before using an external form')
    ready.add_argument('--job',required=True)
    outcome=commands.add_parser('record-outcome')
    outcome.add_argument('--job',required=True)
    outcome.add_argument('--status',required=True,type=normalize_application_status,choices=['reserved','discarded','blocked','uncertain','pending'])
    outcome.add_argument('--reason',required=True)
    application=commands.add_parser('record-application',help='Record a real confirmation; does not submit applications')
    application.add_argument('--job',required=True)
    application.add_argument('--cv',required=True,help='Exact filename of the uploaded PDF')
    application.add_argument('--sha256',required=True,help='SHA-256 of the uploaded PDF')
    application.add_argument('--receipt',type=Path,required=True)
    application.add_argument('--confirmation',required=True)
    application.add_argument('--channel',required=True)
    application.add_argument('--at',required=True,help='ISO 8601 timestamp with time zone')
    application.add_argument('--answers',type=Path)
    options=parser.parse_args()
    default='workspace-demo' if options.command=='demo' else 'workspace'
    workspace=Workspace(options.workspace or os.environ.get('WORKSPACE_DIR') or BASE/default)
    command=options.command
    if command=='init':
        result=workspace.initialize(read(options.profile or BASE/'examples/candidate.template.json'),
                                    read(options.preferences or BASE/'examples/preferences.template.json'))
        result['next']='Complete candidate.json and preferences.json, then run python run.py serve.'
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
        result['next']='Open or render every PDF page before approving it.'
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
                'browser':'The agent must verify its own browser and portal access.',
                'auth':'Telegram OTP' if os.environ.get('WORKSPACE_PUBLIC_URL') else 'Localhost only'}
        if result['initialized']: result['integrity']=workspace.validate()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if isinstance(result,dict) and result.get('valid') is False: return 1
    return 0


if __name__=='__main__':
    try: sys.exit(main() or 0)
    except (WorkspaceError,FileNotFoundError,KeyError,json.JSONDecodeError) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
