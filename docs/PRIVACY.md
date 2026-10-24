# Compartir código, conservar los datos en privado

El repositorio distribuye la app, las instrucciones y una demo ficticia. Cada persona crea su propio espacio. No hay telemetría ni un backend central que reciba candidaturas.

La app local no hace llamadas a un proveedor de IA. El agente elegido sí puede procesar los archivos que se le proporcionan según su propio servicio y configuración. Al presentar una candidatura, el portal recibe los datos y documentos enviados. Con acceso remoto opcional, Telegram recibe el código de acceso y la URL del sitio.

No subas a Git `workspace/`, CV reales, capturas, notas, informes, `.env`, sesiones, claves ni copias de seguridad. `.gitignore` ayuda, pero no protege archivos ya rastreados ni archivos copiados a otra carpeta. Una captura de pantalla también puede contener datos personales.

## Exportación

`public-files.txt` enumera exactamente los archivos distribuibles. Para revisar y crear un ZIP:

```sh
python scripts/audit_export.py
python scripts/audit_export.py --zip dist/job-search-workspace.zip
```

El auditor rechaza rutas privadas o inesperadas, enlaces simbólicos, algunos patrones de credenciales y archivos rastreados fuera de la lista. El ZIP incluye solo esa lista; falla si el ZIP de destino ya existe. Estos controles no certifican por sí solos que cualquier texto o imagen sea anónimo: revisa las modificaciones antes de publicar, especialmente ejemplos, PDF y capturas.

## Datos locales

El servidor escucha en `127.0.0.1`. El uso local presupone un equipo y una cuenta de sistema confiables. No publiques ese puerto directamente ni copies una instancia personal como demo pública.

Los datos del espacio no están cifrados por esta app. Usa los permisos y cifrado del sistema para protegerlos. Para una copia de seguridad coherente, detén el servidor y cualquier agente que escriba, y copia el espacio privado completo a un destino privado. Si ya se publicó un secreto, retirarlo del último commit no lo revoca: rótalo y revisa el historial.
