# Instrucción para una búsqueda recurrente

Este texto se entrega al programador del agente que elija el usuario. No activa ninguna automatización al instalar el repositorio.

```text
Trabaja en este repositorio y lee AGENTS.md y docs/WORKFLOW.md.
Comprueba la fecha, el periodo autorizado y si ya existe un registro de hoy.
Lee el perfil, preferencias, estado, notas e informes antes de actuar.

Busca ofertas recientes en las fuentes autorizadas. Verifica fecha real,
ubicación, modalidad, condiciones de contratación y salario. Deduplica antes
de preparar documentos. No fuerces una cuota si no hay encaje.

Prepara CV específicos basados en hechos confirmados, revisa todas sus páginas
y conserva cada versión con su hash. Presenta candidaturas únicamente si la
instrucción vigente del usuario autoriza envíos dentro de este periodo y límite.
Registra esa autorización por oferta y comprueba check-ready antes de actuar.
Si el usuario solo autorizó preparación, deja los documentos para revisión.

Ante una sesión cerrada, un dato desconocido o una intervención obligatoria,
registra el bloqueo y continúa con otras ofertas. Ante un envío incierto,
comprueba si ya existe antes de reintentar. Nunca inventes una confirmación.

Genera el informe con enlaces a oferta, motivo, PDF realmente usado y resultado.
Registra qué fuentes se consultaron y sus limitaciones en workspace/runs.json,
usando escrituras atómicas y conservando los registros previos. Distingue una
búsqueda sin coincidencias de una ejecución que no llegó a realizarse.
Termina al acabar el periodo y no renueves por tu cuenta.
```

La app puede estar alojada en un servidor mientras el agente corre en otro equipo. Son procesos distintos. Para que el trabajo continúe con el ordenador apagado hace falta un entorno del agente que siga funcionando, con las herramientas y sesiones necesarias. No basta con alojar la tabla.
