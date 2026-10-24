# Compatibilidad con agentes

El contrato común es el sistema de archivos, los comandos de `run.py` y las instrucciones de `AGENTS.md`. No se llama a una API de modelo desde el backend.

| Entorno | Cómo empezar | Qué debe estar disponible |
| --- | --- | --- |
| Codex con acceso al repositorio | Abrir la carpeta y usar START_HERE.md; AGENTS.md contiene el contexto | Terminal/Python, acceso web y navegador autorizado para enviar |
| Claude Code | Abrir la carpeta; CLAUDE.md remite a AGENTS.md | Las mismas capacidades; el acceso al navegador se configura en ese entorno |
| Otro agente con herramientas | Pedir expresamente que lea AGENTS.md y START_HERE.md | Archivos, ejecución de comandos y las capacidades externas necesarias |
| Chat sin acceso a archivos o herramientas | Puede ayudar a redactar el perfil y evaluar ofertas aportadas | No puede operar este repositorio ni acreditar envíos por sí solo |

Los modelos pueden diferir al seleccionar ofertas o redactar. Los comandos mantienen el formato de los registros, los hashes de los documentos y la detección de duplicados; no garantizan que todos los agentes razonen igual.

## Comprobación inicial

1. Ejecutar `python run.py doctor` y comprobar la carpeta privada.
2. Consultar una oferta actual por una herramienta disponible y verificar la ficha completa.
3. Comprobar si existe una sesión autorizada en el portal de destino antes de intentar un envío.
4. Abrir el PDF o renderizar sus páginas. Si falta Poppler, usar un visor disponible; no dar por revisado un archivo que no se ha visto.
5. Registrar bloqueos concretos y continuar con pasos independientes.

No se redistribuyen sesiones de navegador, plugins comerciales ni las skills de terceros que pudiera usar una instalación. El flujo básico está documentado aquí y el generador de PDF es propio; las skills de análisis o CV instaladas por el usuario pueden complementarlo.

Referencias oficiales: [instrucciones AGENTS.md en Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [memoria e instrucciones de Claude Code](https://code.claude.com/docs/en/memory). La compatibilidad de estructura está documentada; una ejecución completa con cada entorno debe probarse antes de anunciarla como verificada.
