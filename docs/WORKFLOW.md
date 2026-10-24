# Flujo operativo

Los ejemplos siguientes usan una terminal en la raíz del repositorio. En algunos sistemas el ejecutable se llama `python3`. Para otro espacio, coloca `--workspace /ruta/privada` antes del subcomando.

## 1. Perfil y filtros

Ejecuta `python run.py init`. Edita `workspace/candidate.json` y `workspace/preferences.json` con datos confirmados. Cada hecho tiene `id`, `text`, `verified` y `scope`; este último distingue empresa, proyecto independiente y formación. Registra lo que falta en `unknowns`.

Pregunta por ubicación, modalidad, autorización de trabajo, idiomas, salario y puestos cuando falten. Comprueba también si el usuario busca empleo, freelance o ambos. Mantén las autorizaciones de envío separadas de sus preferencias.

## 2. Búsqueda y análisis

Consulta las fuentes permitidas y verifica las fichas. Usa las últimas 24 horas cuando haya suficientes resultados y prioriza la última hora cuando el portal lo permita. Conserva la fecha realmente observada, la fecha de revisión, el enlace público y el ID del ATS si existe.

Prepara un JSON siguiendo `examples/job.demo.json`, con motivo, fortalezas acreditadas, dudas y siguiente paso:

```sh
python run.py add-job --file workspace/offer.json
```

Si devuelve un duplicado, retoma la oferta existente. No cambies el ID para esquivar el control.

## 3. CV adaptado

Selecciona y ordena hechos reales. Para el generador incluido, prepara un JSON como `examples/cv.demo.json`. Cada afirmación usa `source_refs` con IDs del perfil:

```sh
python -m pip install -r requirements-pdf.txt
python run.py create-cv --job ats-123 --file workspace/cv-draft.json --why "Destacar integraciones y trabajo con usuarios" --language es
```

Las referencias son una ayuda de trazabilidad: un texto puede citar una fuente válida y aun así exagerarla. Revisa que títulos, fechas, nivel y alcance coincidan con la evidencia.

Si ya tienes un PDF de otra herramienta:

```sh
python run.py attach-cv --job ats-123 --file /ruta/cv.pdf --why "Adaptación revisada para esta oferta" --language es
```

Los documentos se copian con nombre nuevo a `workspace/documents/`. Abre **todas** las páginas. La app muestra una vista previa de la primera y permite abrir o descargar el original completo. Cada adaptación conserva su hash y las versiones anteriores.

## 4. Revisión y autorización

Abre `python run.py serve`. El usuario puede revisar la ficha, el PDF y escribir notas. Priorizar una oferta o aprobar el contenido del CV no equivale por sí solo a autorizar un envío.

Solo después de una instrucción real del usuario:

```sh
python run.py approve --job ats-123 --note "Instrucción concreta del usuario que autoriza este envío"
python run.py check-ready --job ats-123
```

La autorización registrada queda vinculada al PDF y caduca a las 24 horas. Cambiar de versión exige registrar de nuevo una autorización vigente. El agente debe respetar además las condiciones y límites de la instrucción del usuario: este comando no puede certificar su consentimiento por sí mismo.

## 5. Formulario y resultado

El agente abre el formulario oficial con sus herramientas autorizadas. Verifica el PDF elegido y completa únicamente hechos confirmados. No acepta contratos, gastos o permisos adicionales por inferencia.

Si hay un bloqueo:

```sh
python run.py record-outcome --job ats-123 --status bloqueada --reason "La pregunta obligatoria requiere un dato no confirmado"
```

Si no está claro si se envió:

```sh
python run.py record-outcome --job ats-123 --status incierta --reason "El portal no mostró confirmación; comprobar solicitudes antes de reintentar"
```

Después de ver una confirmación real, guarda una captura y registra los datos exactos:

```sh
python run.py record-application --job ats-123 --cv ats-123_YYYY-MM-DD_v1.pdf --sha256 HASH_REAL_DEL_PDF --receipt workspace/confirmation.png --confirmation "Texto real observado en el portal" --channel "ATS de la empresa" --at FECHA_ISO_CON_ZONA
```

`--answers workspace/answers.json` añade respuestas relevantes del formulario. No guardes contraseñas, códigos de acceso ni URLs temporales. Un segundo registro del mismo envío es idempotente; uno con otro PDF genera un conflicto.

Este comando acredita que se ha registrado una observación, no que el programa haya enviado la solicitud ni que una captura pruebe por sí sola su contenido. Nunca lo uses para simular actividad. Si una confirmación llega tarde, el hecho real se puede registrar y se señala la falta de autorización previa guardada en vez de ocultarlo.

## 6. Informe y continuidad

```sh
python run.py validate
python run.py report
```

Informa sobre revisadas, preparadas, enviadas, descartadas y bloqueadas con sus motivos. La app enlaza el último informe. Los informes de este comando resumen los registros existentes; no prueban que se haya ejecutado una búsqueda ese día.

Antes de otra sesión, vuelve a leer los datos y las notas. Para búsquedas recurrentes usa `DAILY_RUN.md` con un periodo y un límite autorizados.
