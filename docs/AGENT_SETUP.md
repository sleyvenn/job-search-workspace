# Arranque que realiza el agente

El usuario ha dado el repositorio para que lo montes y lo uses. Resuelve tú la instalación y el arranque; evita pedirle que ejecute comandos que puedes ejecutar con tus herramientas.

1. Lee README.md y AGENTS.md. Si has descargado un ZIP, localiza la carpeta que contiene run.py; si ya hay un checkout, úsalo sin sobrescribirlo.
2. Localiza Python 3.11+ en el entorno de ejecución, incluido el runtime que proporcione tu agente. `python`, `python3` o `py -3` pueden ser el ejecutable. Si no existe, instala desde una fuente oficial cuando tengas autorización y capacidades; si no puedes, explica ese bloqueo concreto.
3. Ejecuta `python run.py bootstrap`. Crea el espacio privado si falta, elige un puerto libre y arranca la app. Si ya existe, conserva sus datos y reutiliza su servidor. Guarda la URL que devuelve.
4. Abre esa URL con el navegador disponible para que el usuario vea la app. No abras una nueva instancia en cada mensaje. `python run.py doctor` informa sobre el estado y las funciones de PDF disponibles.
5. Lee el perfil y las preferencias actuales. Si están vacíos, recoge primero experiencia real, ubicación/modalidad, salario mínimo, idiomas, autorización laboral y puestos de interés. Usa el CV o perfil que el usuario haya autorizado a leer. Agrupa las preguntas y pregunta solo lo que falte.
6. Guarda los hechos confirmados en candidate.json con IDs estables. Distingue el trabajo de cada empresa del trabajo independiente. Guarda las preferencias y deja el modo de envío en revisión salvo que el usuario autorice más.
7. Comprueba tus capacidades para buscar ofertas, manejar las sesiones autorizadas y ver documentos. Instala `requirements-pdf.txt` en un entorno local del proyecto si necesitas el generador; no necesita API keys. Poppler es opcional para la vista previa, y puede sustituirse por un visor para la revisión visual.
8. Sigue docs/WORKFLOW.md: busca, analiza, registra, prepara y muestra. Completa lo que puedas y registra los bloqueos concretos. No envíes candidaturas hasta tener autorización.

La única intervención inicial del usuario debería ser aportar datos que no tienes y tomar las decisiones que le corresponden. Los comandos internos son una herramienta del agente.

Si el usuario pide solo ver el producto, usa `python run.py demo` en vez de introducir datos personales. Para continuar un trabajo existente, lee sus registros y notas antes de actuar.
