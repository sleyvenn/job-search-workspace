"""Start or reuse the local app on an available loopback port."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

from .workspace import WorkspaceError, read, save


def health(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/health',timeout=0.7) as response:
            return json.load(response)
    except (OSError,ValueError): return {}


def start(workspace, base, preferred_port=8765):
    base=Path(base).resolve()
    if os.environ.get('WORKSPACE_PUBLIC_URL'):
        raise WorkspaceError('bootstrap arranca una app local. Para el alojamiento HTTPS configurado, usa serve y docs/DEPLOYMENT.md.')
    if not 1024 <= preferred_port <= 65516:
        raise WorkspaceError('El puerto de arranque debe estar entre 1024 y 65516.')
    initialized=False
    if not (workspace.root/'state.json').exists():
        workspace.initialize(read(base/'examples/candidate.template.json'),read(base/'examples/preferences.template.json'))
        initialized=True
    for port in range(preferred_port,preferred_port+20):
        existing=health(port)
        if existing.get('app')=='job-search-workspace-v1' and existing.get('workspace')==str(workspace.root):
            return {'url':f'http://127.0.0.1:{port}','reused':True,'workspace':str(workspace.root)}
        with socket.socket() as probe:
            try: probe.bind(('127.0.0.1',port))
            except OSError: continue
        logs=workspace.root/'runtime'
        logs.mkdir(exist_ok=True)
        with (logs/'server.out.log').open('ab') as out, (logs/'server.err.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,str(base/'run.py'),'--workspace',str(workspace.root),'serve','--port',str(port)],
                cwd=base,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=os.name!='nt')
        for _ in range(40):
            current=health(port)
            if current.get('app')=='job-search-workspace-v1' and current.get('workspace')==str(workspace.root):
                result={'url':f'http://127.0.0.1:{port}','pid':process.pid,'workspace':str(workspace.root),
                        'initialized':initialized,'reused':False,
                        'next':'El agente completa el perfil y los filtros con el usuario; la app ya está abierta para trabajar.'}
                save(logs/'server.json',result)
                return result
            if process.poll() is not None:
                raise WorkspaceError('El servidor no ha arrancado. Revisa runtime/server.err.log dentro del espacio privado.')
            time.sleep(0.15)
        process.terminate()
        process.wait(timeout=5)
        raise WorkspaceError('El servidor no respondió a tiempo. Revisa los registros privados.')
    raise WorkspaceError('No hay un puerto disponible en el rango de arranque.')
