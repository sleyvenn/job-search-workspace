# Empieza aquí

Pásale el enlace a tu agente y dile:

> Descarga este repositorio y úsalo como base para mi búsqueda de empleo. Monta la app y ayúdame a completar mi perfil y mis filtros.

El agente seguirá `docs/AGENT_SETUP.md`: descarga, arranca y abre la app. Tú solo aportas los datos y decisiones que falten.

Si necesitas detallar el alcance, puedes ampliar el mensaje:

```text
Lee AGENTS.md y docs/WORKFLOW.md. Quiero usar esta app para buscar trabajo.
Comprueba primero que puedes leer y escribir archivos, ejecutar Python,
consultar ofertas actuales y, si llega el momento, usar los formularios oficiales.

Inicializa mi espacio privado sin sobrescribir archivos existentes.
Ayúdame a completar el perfil con hechos confirmados y los filtros de ubicación,
modalidad, salario, idiomas, tipo de contrato y puestos que me interesan.
Pregúntame solo lo que falte; no deduzcas experiencia de las ofertas.

Busca una primera selección reciente, explica por qué encaja o por qué la descartas,
registra las ofertas sin duplicados y prepara un PDF específico para cada selección.
Abre la tabla y enséñame los PDF antes de presentar candidaturas.
No envíes nada sin una instrucción mía que autorice ese paso.
Si no tienes una capacidad, registra el bloqueo y completa el resto del trabajo.
```

Para continuar con otro agente:

```text
Lee AGENTS.md, workspace/candidate.json, workspace/preferences.json,
workspace/state.json, workspace/reviews/decisions.json y workspace/runs.json.
Retoma el trabajo desde esos registros. No repitas envíos ni supongas autorizaciones.
Comprueba los envíos inciertos antes de reintentar. Conserva todos los PDF existentes.
```

Para una búsqueda recurrente, define primero con el agente el periodo, horario,
límite diario y si está autorizado a enviar o solo preparar. Usa el servicio de
programación de ese entorno y el contenido de `docs/DAILY_RUN.md`. Esta app no
mantiene un agente ejecutándose ni evita que un ordenador apagado interrumpa su trabajo.
