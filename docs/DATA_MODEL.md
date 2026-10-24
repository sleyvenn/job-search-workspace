# Datos de cada persona

`workspace/` es privado. `--workspace /otra/ruta` permite elegir otra carpeta. Los ejemplos públicos no son el perfil del usuario.

| Archivo o carpeta | Contenido |
| --- | --- |
| candidate.json | Identidad y contacto, idiomas, hechos confirmados, incógnitas y nombres privados que deben omitirse |
| preferences.json | Ubicación, modalidad, salario, familias de puestos, fuentes y alcance de los envíos |
| state.json | Ofertas, análisis resumido, versiones de CV, autorización y resultado observado |
| analysis.json | Explicación adicional por ID de oferta: recomendación, riesgos y adaptación |
| cv-versions.json | Índice de documentos registrados |
| cv-content/ | Contenido del CV generado y referencias a los hechos del perfil |
| documents/ | PDF con nombre nuevo por versión y SHA-256 |
| receipts/ | Capturas de confirmaciones reales; pueden contener datos personales |
| reviews/decisions.json | Notas y decisiones guardadas desde la app; revisión incremental e historial |
| runs.json, reports/ | Ejecuciones e informes; un informe del CLI no acredita una búsqueda nueva |
| trial.json | Condiciones de una prueba diaria autorizada, cuando exista |
| runtime/ | PID, URL y registros del servidor local |

## Perfil

Cada entrada de `facts` tiene un `id` estable, `text`, `verified` y `scope`. Usa `scope` para indicar la empresa concreta, trabajo independiente o formación. Solo los hechos con `verified: true` pueden ser fuente del generador de CV. Las preferencias por una tecnología y las ganas de aprender no son experiencia profesional.

`source_refs` referencia esos IDs en `examples/cv.demo.json`. Su validación comprueba que existen y están confirmados; la fidelidad de la redacción requiere revisión.

## Ofertas y documentos

Parte de `examples/job.demo.json` y utiliza `add-job`. El ID, URL pública, empresa, puesto, ubicación, modalidad, motivo y fecha de verificación son obligatorios. `external_ids` permite deduplicar una misma vacante entre LinkedIn y el ATS. Una fecha de revisión no sustituye la fecha de publicación.

Un salario no publicado usa `minimum: null` y `maximum: null`. Los rangos se expresan en euros brutos anuales para empleo; si la oferta usa otra moneda o periodicidad, conserva la fuente y verifica la conversión antes de compararla. No reutilices estos campos para tarifas freelance.

`cv_prepared` es la versión propuesta; `cv_history` conserva las anteriores. Una candidatura enviada guarda por separado `cv_sent` y `cv_sha256`, además de la fecha, canal, respuestas y justificante. Preparar un nuevo CV no cambia el enviado.

## Estados

| Estado | Significado |
| --- | --- |
| pendiente | En análisis o preparación; la presencia de un PDF se muestra aparte |
| reservada | Se aplaza por un motivo explícito |
| descartada | Se decide no continuar, con razón |
| bloqueada | Falta un dato, acceso o intervención necesaria |
| incierta | No se pudo confirmar el resultado del formulario; comprobar antes de reintentar |
| enviada | Hay confirmación observada registrada con PDF y captura |

La decisión del usuario y la revisión del CV están separadas del resultado del envío. Guardar «Priorizar» o «CV aprobado» no ejecuta un formulario ni concede por sí solo autorización para enviarlo.

Usa los comandos para modificar ofertas y documentos. Lee las notas antes de actuar; no reconstruyas `decisions.json` desde otra versión. El servidor rechaza escrituras de una pestaña con revisión obsoleta. No ejecutes varios servidores sobre el mismo espacio privado.
