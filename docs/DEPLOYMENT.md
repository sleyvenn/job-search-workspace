# Uso local y alojamiento privado

La entrada normal es pedir al agente que ejecute `python run.py bootstrap` y abra la URL devuelta. Arranca en segundo plano, conserva los datos y reutiliza un servidor del mismo espacio cuando lo encuentra. Los registros están en `workspace/runtime/`. El equipo debe estar encendido; este comando no instala un servicio de inicio automático.

Para detenerlo, comprueba que el PID de `runtime/server.json` sigue correspondiendo a `run.py` y a ese espacio antes de terminar el proceso. Para volver a abrirlo, repite `bootstrap`.

## Servidor propio, opcional

Esta versión admite **una persona y un destinatario de Telegram por instalación**. Para alojarla, el operador necesita Python 3.11+, almacenamiento persistente y un proxy HTTPS que reenvíe al puerto local. No expongas el servidor de desarrollo directamente a Internet.

1. Inicializa un espacio privado fuera de una carpeta pública y limita sus permisos.
2. Configura un bot propio de Telegram y su destinatario. Copia `.env.example` a `.env`, o usa variables del servicio. Nunca incluyas el token en Git, capturas o comandos compartidos.
3. Define `WORKSPACE_PUBLIC_URL=https://tu-subdominio.example`, `WORKSPACE_DIR`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. La URL debe ser un origen HTTPS, sin ruta.
4. Ejecuta `python run.py serve --port 8765` mediante el gestor de servicios del sistema. `bootstrap` es solo para el uso local.
5. Configura el proxy para conservar el Host público, limitar peticiones y no registrar cuerpos con códigos. Restringe el acceso directo al puerto local.
6. Comprueba desde una sesión sin autenticar que documentos, notas, informes y API están protegidos. Prueba después un código real con autorización del titular del bot.

Cuando hay URL pública configurada, la app exige credenciales de Telegram; no abre el contenido si faltan. Los códigos duran cinco minutos, son de un solo uso y tienen límites de peticiones e intentos. La cookie de sesión usa Secure, HttpOnly y SameSite=Strict. Las sesiones duran hasta 30 días y se pueden cerrar desde la interfaz.

`reviews/auth.sqlite` y `reviews/auth.key` son privados. Las pruebas automáticas simulan la entrega del código y no envían mensajes. El despliegue real, el proxy, los respaldos y su supervisión corresponden al operador.

Alojar la app no ejecuta por sí solo un agente diariamente. La búsqueda necesita un entorno de ejecución y un planificador autorizados con las herramientas y sesiones necesarias.
