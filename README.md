# Job Search Workspace

**Dale este repositorio a tu agente y pídele que monte tu búsqueda de empleo.** Tendrás una app con ofertas, motivos, CV específicos, decisiones y resultados en una tabla sencilla.

## Úsalo con una frase

Pega el enlace de este repositorio en Codex, Claude Code u otro agente con acceso a archivos y terminal, y dile:

> Descarga este repositorio y úsalo como base para mi búsqueda de empleo. Monta la app, pregúntame por mi perfil y mis filtros, y empieza preparando ofertas y CV para que los revise.

El agente se encarga del arranque y la configuración siguiendo [AGENTS.md](AGENTS.md). Tú aportas tu experiencia, decides los filtros y revisas los resultados. No necesitas conocer los comandos del proyecto.

La app guarda el estado y los documentos. Tu agente busca y analiza las ofertas utilizando las herramientas y cuentas a las que tú le des acceso. El repositorio no incluye un proveedor de IA obligatorio ni credenciales de portales.

![Demo con datos ficticios](docs/demo.png)

## Ver la demo

También puedes decirle: **«Arranca primero la demo de este repo para que la vea»**.

Para quien prefiera hacerlo manualmente:

Necesitas **Python 3.11 o posterior**. La app y la demo no requieren instalar paquetes.

```sh
python run.py demo
```

Abre [localhost:8765](http://127.0.0.1:8765). Hay tres ofertas ficticias, sus motivos y un CV de ejemplo. Ninguna candidatura de la demo se ha enviado. Pulsa una fila para ver la ficha y **PDF** para abrir el currículum.

La vista previa como imagen requiere Poppler (`pdftoppm`). Si falta, puedes abrir o descargar el PDF original. `python run.py doctor` muestra las capacidades disponibles.

## Configuración manual opcional

```sh
python run.py init
python run.py serve
```

Completa `workspace/candidate.json` y `workspace/preferences.json`, o dale a tu agente el prompt de [START_HERE.md](START_HERE.md). El perfil distingue hechos confirmados, ámbitos de experiencia y datos pendientes; los requisitos de una oferta no se convierten automáticamente en experiencia.

Cada instalación tiene su propio `workspace/`, excluido de Git. La demo usa `workspace-demo/`. Los ejemplos públicos son ficticios.

## Dárselo a un agente

Abre esta carpeta con Codex, Claude Code u otro agente que pueda leer archivos y ejecutar Python, y pega:

> Lee AGENTS.md y START_HERE.md. Configura este repositorio como mi espacio de búsqueda de empleo. Comprueba tus herramientas, recoge mi experiencia y mis filtros sin inventar datos, prepara una primera selección y un CV por oferta. Deja las candidaturas listas para revisar; no las envíes hasta tener mi autorización.

El mismo estado se puede continuar con otro agente. [Compatibilidad y límites](docs/AGENTS_AND_TOOLS.md) explica qué necesita cada entorno. El acceso al navegador, la sesión de los portales y la programación diaria se configuran en el agente elegido.

## Qué incluye la primera versión

- Tabla con búsqueda, filtros, fecha, estado, oferta enlazada y PDF; fichas con motivos, dudas, adaptación y notas.
- CLI para registrar ofertas, CV, decisiones, autorizaciones, envíos observados e informes.
- Detección de duplicados por ID, URL canónica, identificadores externos y empresa/puesto/ubicación.
- PDF versionados con SHA-256. Una versión nueva no cambia el documento de una candidatura anterior.
- Generador opcional de CV con referencias a hechos confirmados del perfil.
- Estados separados para preparado, reservado, bloqueado, envío incierto y envío confirmado.
- Acceso privado por Telegram si se aloja detrás de HTTPS; uso local sin cuentas adicionales.
- Pruebas del flujo, integridad de documentos, acceso y exportación pública.

## Flujo de trabajo

1. El usuario confirma perfil, filtros y alcance.
2. El agente consulta fuentes actuales y lee cada oferta completa.
3. `add-job` registra el análisis y rechaza duplicados.
4. `create-cv` o `attach-cv` prepara una versión específica; se revisan todas sus páginas.
5. Se registra una autorización real con `approve`; `check-ready` comprueba el registro antes del formulario.
6. El agente usa el formulario oficial. `record-application` guarda después la confirmación, el PDF exacto y el justificante.
7. `report` produce un informe de los registros actuales.

Los comandos no envían formularios por sí solos. Una referencia válida a un hecho no demuestra que su paráfrasis sea fiel: el agente y el usuario siguen revisando el contenido. Consulta el [procedimiento completo](docs/WORKFLOW.md).

## Crear PDF

```sh
python -m pip install -r requirements-pdf.txt
python run.py --workspace workspace-example init --profile examples/candidate.demo.json --preferences examples/preferences.template.json
python run.py --workspace workspace-example add-job --file examples/job.demo.json
python run.py --workspace workspace-example create-cv --job demo-product-engineer --file examples/cv.demo.json --why "Destacar aplicaciones e integraciones" --language es
```

Esta secuencia crea un espacio de ejemplo separado. No copies el perfil de muestra como experiencia real.

También puedes registrar un PDF generado por otra herramienta mediante `attach-cv`. El generador es opcional; el formato de datos y el registro son compartidos.

## Documentación

- [Empezar con un agente](START_HERE.md)
- [Flujo y comandos](docs/WORKFLOW.md)
- [Formato de datos](docs/DATA_MODEL.md)
- [Codex, Claude y otros entornos](docs/AGENTS_AND_TOOLS.md)
- [Portales, salario y freelance](docs/JOB_SOURCES.md)
- [Privacidad y publicación del repositorio](docs/PRIVACY.md)
- [Alojamiento privado y acceso por Telegram](docs/DEPLOYMENT.md)
- [Decisiones de producto y siguientes pasos](docs/PRODUCT.md)

## Desarrollo

```sh
python -m unittest discover -s tests -v
python scripts/audit_export.py
```

Backend Python con biblioteca estándar, frontend HTML/CSS/JavaScript, datos JSON y sesiones SQLite. Sin compilación del frontend. Interfaz inicial en español. Iconos oficiales de [Phosphor](https://github.com/phosphor-icons/core), incluidos localmente con su licencia.

Esta versión es para una persona por instalación. No incluye un SaaS multiusuario, un navegador remoto, un servicio central de búsqueda ni un planificador autónomo. Puede funcionar con distintos agentes cuando dispongan de las capacidades necesarias; no se ha probado una sesión completa en todos ellos.

Licencia [MIT](LICENSE). Las licencias de terceros se conservan junto a sus archivos.
