# Guía de Instalación y Configuración — Sistema de Reportes M30M

> **Para quién es esta guía:** Empleados corporativos sin conocimientos técnicos que necesitan instalar y poner en marcha el sistema de reportes automáticos en Google Cloud. Asume que ya tienes el repositorio descargado en tu computador.

---

## Tabla de Contenidos

- [Conceptos de Google Cloud (Glosario)](#conceptos-de-google-cloud-glosario)
- [Requisitos Previos](#requisitos-previos)
- [Paso 1: Instalar Python](#paso-1-instalar-python)
- [Paso 2: Instalar Google Cloud CLI (gcloud)](#paso-2-instalar-google-cloud-cli-gcloud)
- [Paso 3: Autenticarse en Google Cloud](#paso-3-autenticarse-en-google-cloud)
- [Paso 4: Crear el Proyecto GCP](#paso-4-crear-el-proyecto-gcp)
- [Paso 5: Habilitar las APIs necesarias](#paso-5-habilitar-las-apis-necesarias)
- [Paso 6: Instalar las dependencias de Python](#paso-6-instalar-las-dependencias-de-python)
- [Paso 7: Crear la base de datos Firestore](#paso-7-crear-la-base-de-datos-firestore)
- [Paso 8: Crear el bucket de Cloud Storage](#paso-8-crear-el-bucket-de-cloud-storage)
- [Paso 9: Subir el archivo ids.xlsx al bucket](#paso-9-subir-el-archivo-idsxlsx-al-bucket)
- [Paso 10: Crear la cola de Cloud Tasks](#paso-10-crear-la-cola-de-cloud-tasks)
- [Paso 11: Configurar las variables de entorno](#paso-11-configurar-las-variables-de-entorno)
- [Paso 12: Primer despliegue en Cloud Run](#paso-12-primer-despliegue-en-cloud-run)
- [Paso 13: Configurar variables de entorno en Cloud Run](#paso-13-configurar-variables-de-entorno-en-cloud-run)
- [Paso 14: Verificar el despliegue](#paso-14-verificar-el-despliegue)
- [Paso 15: Conectar el webhook de LearnWorlds](#paso-15-conectar-el-webhook-de-learnworlds)
- [Solución de Problemas](#solución-de-problemas)

---

## Conceptos de Google Cloud (Glosario)

Antes de comenzar, aquí tienes una explicación breve de los servicios de Google Cloud que usa este sistema:

| Término | Qué hace en este sistema |
|---------|--------------------------|
| **Cloud Run** | El servidor donde vive el programa. Recibe los avisos de LearnWorlds y procesa los informes automáticamente. No necesitas tener un computador encendido permanentemente: Cloud Run se activa solo cuando llega un aviso. |
| **Cloud Storage (GCS)** | Un disco duro en la nube donde se guardan los archivos del sistema (como el mapeo de evaluaciones `ids.xlsx` y los datos de preguntas). |
| **Firestore** | Una base de datos en la nube que el sistema usa para llevar registro de qué informes están pendientes y cuáles ya se procesaron. |
| **Cloud Tasks** | El sistema de cola de tareas. Cuando llega un aviso de LearnWorlds, Cloud Tasks programa el momento exacto en que el sistema procesará los informes. |
| **IAM (Gestión de Identidades y Accesos)** | El sistema de permisos de Google Cloud. Controla quién puede hacer qué dentro del proyecto. |
| **Proyecto GCP** | Un contenedor que agrupa todos los recursos (servidor, base de datos, archivos) de esta aplicación. Tiene un ID único (por ejemplo: `mi-empresa-reportes-2024`). |

---

## Requisitos Previos

- Cuenta Google Workspace corporativa activa (Gmail corporativo)
- Acceso al panel de administrador de LearnWorlds
- Windows 10 o superior
- El repositorio del proyecto ya descargado en tu computador (si no lo tienes, sigue el tutorial de actualización del repositorio primero)
- Conexión a internet

---

## Paso 1: Instalar Python

> Python es el lenguaje de programación en el que está escrito el sistema; necesitas instalarlo en tu computador para que el programa pueda ejecutarse localmente.

1. Abre tu navegador y ve a https://www.python.org/downloads/
2. Haz clic en el botón amarillo **"Download Python 3.11.x"** (la versión más reciente de Python 3.11)
3. Ejecuta el instalador descargado (.exe)
4. En la primera pantalla del instalador, **marca la casilla "Add Python to PATH"** antes de hacer clic en "Install Now"
5. Haz clic en **"Install Now"** y espera a que termine la instalación
6. Abre el **Símbolo del sistema** (busca "cmd" en el menú de inicio) y escribe:
   ```cmd
   python --version
   ```

> [!WARNING]
> Si no marcas "Add Python to PATH", el comando `python` no funcionará en el Símbolo del sistema. Si ya instalaste Python sin marcar esta opción, desinstálalo y vuelve a instalarlo marcando la casilla.

✅ **Deberías ver:** algo como `Python 3.11.x`

---

## Paso 2: Instalar Google Cloud CLI (gcloud)

> Google Cloud CLI es la herramienta de línea de comandos que te permite gestionar todos los servicios de Google Cloud desde el Símbolo del sistema de Windows.

1. Abre tu navegador y ve a https://cloud.google.com/sdk/docs/install#windows
2. Descarga el instalador de **Google Cloud SDK para Windows** (.exe)
3. Ejecuta el instalador y acepta las opciones predeterminadas
4. Al finalizar, el instalador abrirá una ventana nueva del Símbolo del sistema automáticamente
5. **Cierra todas las ventanas del Símbolo del sistema** y abre una nueva (esto es necesario para que gcloud quede disponible)
6. En la nueva ventana, escribe:
   ```cmd
   gcloud --version
   ```

> [!WARNING]
> Si ves el error `'gcloud' no se reconoce como un comando interno o externo`, cierra el Símbolo del sistema y ábrelo de nuevo. El instalador actualiza el PATH solo para sesiones nuevas del terminal.

✅ **Deberías ver:** una lista de versiones como `Google Cloud SDK X.X.X` y componentes instalados.

---

## Paso 3: Autenticarse en Google Cloud

> Antes de crear recursos en GCP, debes iniciar sesión con tu cuenta Google Workspace corporativa para que gcloud tenga los permisos necesarios.

1. En el Símbolo del sistema, escribe:
   ```cmd
   gcloud auth login
   ```
2. Se abrirá una ventana del navegador. Inicia sesión con tu **cuenta Google Workspace corporativa** (tu Gmail corporativo)
3. Acepta los permisos solicitados
4. Vuelve al Símbolo del sistema y escribe:
   ```cmd
   gcloud auth application-default login
   ```
5. Repite el proceso de inicio de sesión en el navegador

✅ **Deberías ver:** el mensaje `You are now logged in as [tu-correo@empresa.com]` y luego `Credentials saved to file [ruta]`.

---

## Paso 4: Crear el Proyecto GCP

> Todos los recursos de este sistema (servidor, base de datos, archivos) vivirán dentro de un "Proyecto GCP" — un espacio aislado con un identificador único.

1. Ve a https://console.cloud.google.com/ en tu navegador
2. Haz clic en el selector de proyectos en la barra superior (donde dice "Select a project")
3. Haz clic en **"Nuevo proyecto"**
4. Escribe un nombre descriptivo, por ejemplo: `reportes-m30m`
5. Anota el **ID del proyecto** que aparece debajo del nombre (por ejemplo: `reportes-m30m-123456`) — lo necesitarás en todos los pasos siguientes
6. Haz clic en **"Crear"**
7. En el Símbolo del sistema, configura gcloud para usar este proyecto:
   ```cmd
   gcloud config set project TU_PROJECT_ID
   ```
   Reemplaza `TU_PROJECT_ID` con el ID que anotaste en el paso 5.
8. Verifica que el proyecto correcto está activo:
   ```cmd
   gcloud config get project
   ```

> [!NOTE]
> El **ID del proyecto** (por ejemplo `reportes-m30m-123456`) es diferente al **nombre del proyecto** (`reportes-m30m`). Usa siempre el ID en los comandos.

✅ **Deberías ver:** el ID de tu proyecto como respuesta al último comando.

---

## Paso 5: Habilitar las APIs necesarias

> Antes de usar cualquier servicio de Google Cloud, debes "activarlo" en tu proyecto — esto es obligatorio aunque el servicio exista en GCP.

1. En el Símbolo del sistema, ejecuta este bloque de comandos (puedes copiar y pegar todo a la vez):
   ```cmd
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable cloudtasks.googleapis.com
   ```
2. Espera a que cada comando confirme la activación (puede tardar 1-2 minutos por API)

✅ **Deberías ver:** el mensaje `Operation "operations/..." finished successfully.` para cada API.

---

## Paso 6: Instalar las dependencias de Python

> El sistema usa varias bibliotecas de Python que debes instalar en tu computador antes de poder ejecutarlo localmente.

1. Abre el Símbolo del sistema
2. Navega a la carpeta del repositorio. Por ejemplo, si el repositorio está en `C:\Proyectos\reportes`, escribe:
   ```cmd
   cd C:\Proyectos\reportes
   ```
   (ajusta la ruta según donde tengas guardado el repositorio)
3. Instala las dependencias:
   ```cmd
   pip install -r requirements.txt
   ```
4. Espera a que termine la instalación

✅ **Deberías ver:** una lista de paquetes instalados y el mensaje `Successfully installed ...` al final.

---

## Paso 7: Crear la base de datos Firestore

> Firestore es la base de datos que el sistema usa para registrar qué informes están en cola y cuáles ya se procesaron; debes crearla en modo "nativo" para que funcione correctamente.

1. En el Símbolo del sistema, ejecuta:
   ```cmd
   gcloud firestore databases create --location=us-central1
   ```

> [!WARNING]
> Cuando GCP te pregunte por el modo de base de datos, selecciona **Modo nativo (Native mode)**. Si eliges "Modo Datastore", el sistema no funcionará y no se puede cambiar después.

✅ **Deberías ver:** el mensaje `Success! Selected Google Cloud Firestore Native database ...`

---

## Paso 8: Crear el bucket de Cloud Storage

> El bucket es el "disco duro en la nube" donde se guardarán el archivo de mapeo de evaluaciones y los archivos de datos de preguntas.

1. En el Símbolo del sistema, crea el bucket (reemplaza `TU_PROJECT_ID` con tu ID de proyecto):
   ```cmd
   gcloud storage buckets create gs://TU_PROJECT_ID-mapping --location=us-central1
   ```
   Por ejemplo, si tu proyecto es `reportes-m30m-123456`, el comando sería:
   ```cmd
   gcloud storage buckets create gs://reportes-m30m-123456-mapping --location=us-central1
   ```
2. Anota el nombre del bucket que acabas de crear (por ejemplo: `reportes-m30m-123456-mapping`) — lo usarás en los pasos siguientes.

✅ **Deberías ver:** el mensaje `Creating gs://TU_PROJECT_ID-mapping/...`

---

## Paso 9: Subir el archivo ids.xlsx al bucket

> El archivo `ids.xlsx` contiene el mapeo entre los IDs de evaluaciones de LearnWorlds y los tipos de informe — el sistema lo necesita en la nube para funcionar correctamente.

1. Verifica que tienes el archivo `ids.xlsx` dentro de la carpeta `inputs\` del repositorio
2. En el Símbolo del sistema (dentro de la carpeta del repositorio), sube el archivo:
   ```cmd
   gcloud storage cp inputs\ids.xlsx gs://TU_PROJECT_ID-mapping/ids.xlsx
   ```
3. Verifica que el archivo se subió correctamente:
   ```cmd
   gcloud storage ls gs://TU_PROJECT_ID-mapping/
   ```

✅ **Deberías ver:** `gs://TU_PROJECT_ID-mapping/ids.xlsx` en la lista.

---

## Paso 10: Crear la cola de Cloud Tasks

> Cloud Tasks es el sistema que programa cuándo el servidor debe procesar los informes acumulados; la cola se llama `batch-processing-queue`.

1. En el Símbolo del sistema, ejecuta:
   ```cmd
   gcloud tasks queues create batch-processing-queue --location=us-central1
   ```

✅ **Deberías ver:** el mensaje `Created queue [batch-processing-queue].`

---

## Paso 11: Configurar las variables de entorno

> Las variables de entorno son los datos de configuración que el sistema necesita para conectarse a LearnWorlds, Google Cloud y el correo electrónico — se definen en un archivo `.env` en la carpeta del repositorio.

1. En la carpeta del repositorio, busca el archivo `.env.example`
2. Copia el archivo y renómbralo a `.env`:
   - Haz clic derecho en `.env.example` en el Explorador de Windows → Copiar
   - Pega en la misma carpeta → Renombra la copia como `.env`
3. Abre `.env` con el Bloc de notas o cualquier editor de texto
4. Rellena cada variable según la tabla de referencia:

| Variable | Valor | Dónde encontrarlo |
|----------|-------|-------------------|
| `GCP_PROJECT_ID` | Tu ID de proyecto GCP | El ID que anotaste en el Paso 4 |
| `GCP_BUCKET_NAME` | Nombre de tu bucket | El bucket que creaste en el Paso 8 (ej: `reportes-m30m-123456-mapping`) |
| `IDS_XLSX_GCS_PATH` | Ruta GCS al ids.xlsx | `gs://TU_PROJECT_ID-mapping/ids.xlsx` |
| `ASSESSMENT_MAPPING_SOURCE` | `gcs` | Usar siempre `gcs` para Cloud Run |
| `BANKS_GCS_PREFIX` | `inputs/` | Dejar como `inputs/` (valor predeterminado) |
| `LEARNWORLDS_WEBHOOK_SECRET` | El secreto del webhook | LearnWorlds → Configuración → Webhooks → secreto |
x| `CLIENT_ID` | ID de cliente LearnWorlds | LearnWorlds → Configuración → API |
x| `SCHOOL_DOMAIN` | Dominio de tu escuela | Por ejemplo: `miescuela.learnworlds.com` |
x| `ACCESS_TOKEN` | Token de acceso LearnWorlds | LearnWorlds → Configuración → API |
x| `EMAIL_FROM` | Correo Gmail que envía informes | Tu dirección Gmail corporativa |
x| `EMAIL_PASS` | Contraseña de aplicación Gmail | Ver instrucciones abajo |
| `TASK_QUEUE_ID` | `batch-processing-queue` | El nombre de la cola del Paso 10 |
| `TASK_LOCATION` | `us-central1` | Dejar como está |
| `PROCESS_BATCH_URL` | URL del servicio Cloud Run + `/process-batch` | **Dejar en blanco por ahora** — se obtiene en el Paso 12 |
| `STORAGE_BACKEND` | `gcs` | Para uso en Cloud Run |

**Cómo generar una Contraseña de aplicación Gmail (EMAIL_PASS):**
1. Ve a https://myaccount.google.com/security
2. Haz clic en **"Verificación en dos pasos"** (debe estar activada)
3. Al final de esa página, haz clic en **"Contraseñas de aplicación"**
4. En el menú desplegable, selecciona **"Correo"** y **"Computadora con Windows"**
5. Haz clic en **"Generar"** — copia la contraseña de 16 caracteres que aparece
6. Usa esa contraseña como valor de `EMAIL_PASS`

> [!NOTE]
> Si no ves la opción "Contraseñas de aplicación" en tu cuenta Google Workspace, contacta al administrador de tu cuenta. En algunas configuraciones corporativas esta función puede estar desactivada.

> [!WARNING]
> El archivo `.env` contiene credenciales privadas. No lo compartas con nadie ni lo subas a ningún servidor.

✅ **Deberías ver:** el archivo `.env` con todas las variables rellenadas (excepto `PROCESS_BATCH_URL` que se completa después).

---

## Paso 12: Primer despliegue en Cloud Run

> El despliegue sube el código del repositorio a Google Cloud y crea el servidor que recibirá los webhooks de LearnWorlds — el primer despliegue puede tardar entre 5 y 10 minutos.

> [!NOTE]
> Este es el **primer despliegue** — se hace sin la variable `PROCESS_BATCH_URL` porque esa URL no existe aún. Después del despliegue obtendrás la URL y la configurarás en el Paso 13.

1. En el Símbolo del sistema (dentro de la carpeta del repositorio), ejecuta:
   ```cmd
   gcloud run deploy unified-webhook ^
     --source . ^
     --region us-central1 ^
     --allow-unauthenticated ^
     --project TU_PROJECT_ID
   ```
   Reemplaza `TU_PROJECT_ID` con tu ID de proyecto.
2. Espera a que termine el despliegue (puede tardar de 5 a 10 minutos)
3. Cuando termine, **copia la URL del servicio** que aparece al final del proceso (tiene el formato `https://unified-webhook-xxxxxxxx-uc.a.run.app`)
4. Anota esa URL — la necesitarás en el siguiente paso

✅ **Deberías ver:** `Service [unified-webhook] revision [unified-webhook-xxxxx] has been deployed and is serving 100 percent of traffic. Service URL: https://unified-webhook-XXXXXXXX.us-central1.run.app`

---

## Paso 13: Configurar variables de entorno en Cloud Run

> Las variables de entorno que configuraste en tu `.env` local también deben configurarse directamente en el servidor de Cloud Run para que el sistema funcione en producción.

1. Obtén la URL completa del servicio (si no la anotaste en el paso anterior):
   ```cmd
   gcloud run services describe unified-webhook --region us-central1 ^
     --format="value(status.url)"
   ```
2. Construye la URL de proceso (añade `/process-batch` al final de la URL del servicio):
   Por ejemplo, si la URL es `https://unified-webhook-abc123.us-central1.run.app`, la URL de proceso es `https://unified-webhook-abc123.us-central1.run.app/process-batch`
3. Configura todas las variables de entorno en Cloud Run:
   ```cmd
   gcloud run services update unified-webhook ^
     --region us-central1 ^
     --update-env-vars GCP_PROJECT_ID=TU_PROJECT_ID,^
   GCP_BUCKET_NAME=TU_PROJECT_ID-mapping,^
   IDS_XLSX_GCS_PATH=gs://TU_PROJECT_ID-mapping/ids.xlsx,^
   ASSESSMENT_MAPPING_SOURCE=gcs,^
   BANKS_GCS_PREFIX=inputs/,^
   STORAGE_BACKEND=gcs,^
   LEARNWORLDS_WEBHOOK_SECRET=TU_SECRETO,^
   CLIENT_ID=TU_CLIENT_ID,^
   SCHOOL_DOMAIN=TU_ESCUELA.learnworlds.com,^
   ACCESS_TOKEN=TU_TOKEN,^
   EMAIL_FROM=tu@correo.com,^
   EMAIL_PASS=TU_CONTRASENA_APP,^
   TASK_QUEUE_ID=batch-processing-queue,^
   TASK_LOCATION=us-central1,^
   PROCESS_BATCH_URL=https://unified-webhook-XXXXXXXX.us-central1.run.app/process-batch
   ```
   Reemplaza cada valor en MAYÚSCULAS con tu información real.

✅ **Deberías ver:** `OK` — el servicio Cloud Run se actualiza con las nuevas variables.

---

## Paso 14: Verificar el despliegue

> Antes de conectar LearnWorlds, verifica que el servidor está funcionando correctamente abriendo la URL de estado del servicio.

1. En tu navegador, abre la siguiente URL (reemplaza con tu URL de servicio):
   `https://unified-webhook-XXXXXXXX.us-central1.run.app/status`
2. Si el servidor está funcionando correctamente, verás una respuesta en formato JSON
3. Para verificar también la importación del código Python, en el Símbolo del sistema ejecuta (dentro de la carpeta del repositorio):
   ```cmd
   python -c "from core.assessment_mapper import AssessmentMapper; print('Importacion OK')"
   ```

> [!NOTE]
> La prueba local (paso 3) solo verifica que el código Python está bien instalado en tu computador. El sistema completo solo funciona en producción (Cloud Run) porque necesita acceso a GCP.

✅ **Deberías ver:** la respuesta JSON del endpoint `/status` en el navegador y el texto `Importacion OK` en el Símbolo del sistema.

---

## Paso 15: Conectar el webhook de LearnWorlds

> El último paso es registrar la URL de tu servidor en LearnWorlds para que la plataforma envíe automáticamente un aviso cada vez que un alumno completa una evaluación.

1. Inicia sesión en el panel de administrador de LearnWorlds
2. Ve a **Configuración → Webhooks** (o busca "Webhooks" en el menú)
3. Haz clic en **"Agregar webhook"** o **"Crear nuevo webhook"**
4. En el campo **URL**, pega la URL de tu servicio Cloud Run:
   `https://unified-webhook-XXXXXXXX.us-central1.run.app`
5. En el campo **Secreto** (o "Secret"), pega el mismo valor que usaste para `LEARNWORLDS_WEBHOOK_SECRET`
6. Selecciona el evento **"Assessment Completed"** (u otro nombre equivalente según la versión de LearnWorlds)
7. Guarda el webhook

✅ **Deberías ver:** el webhook registrado y activo en la lista de webhooks de LearnWorlds.

---

## Solución de Problemas

Si algo no funciona como se describe en esta guía, busca tu error en la tabla siguiente:

---

### ❌ 'gcloud' no se reconoce como un comando

**Qué ves:** `'gcloud' no se reconoce como un comando interno o externo, programa o archivo por lotes ejecutable.`

**Por qué ocurre:** El instalador de gcloud actualiza el PATH, pero el Símbolo del sistema que tenías abierto usa el PATH antiguo.

**Cómo resolverlo:**
1. Cierra el Símbolo del sistema actual.
2. Abre una nueva ventana del Símbolo del sistema.
3. Escribe `gcloud --version` para confirmar.

---

### ❌ 'python' no se reconoce como un comando

**Qué ves:** `'python' no se reconoce como un comando interno o externo`

**Por qué ocurre:** Python se instaló sin marcar la opción "Add Python to PATH".

**Cómo resolverlo:**
1. Ve al Panel de control → Programas → Desinstalar un programa.
2. Desinstala Python.
3. Vuelve a instalarlo desde https://www.python.org/downloads/ **marcando la casilla "Add Python to PATH"** en la primera pantalla del instalador.
4. Abre una nueva ventana del Símbolo del sistema y prueba `python --version`.

---

### ❌ Los recursos se crean en el proyecto equivocado

**Qué ves:** Permiso denegado aunque hayas seguido los pasos, o los recursos no aparecen donde esperabas.

**Por qué ocurre:** Es fácil olvidar ejecutar `gcloud config set project` después de autenticarse.

**Cómo resolverlo:**
1. Verifica qué proyecto está activo: `gcloud config get project`.
2. Si no es el correcto: `gcloud config set project TU_PROJECT_ID`.
3. Repite el paso que falló.

---

### ❌ El servidor arranca pero devuelve error 500 (Firestore incompatible)

**Qué ves:** En los registros de Cloud Run: `google.api_core.exceptions.FailedPrecondition: 400`

**Por qué ocurre:** La base de datos Firestore se creó en "Modo Datastore" en lugar de "Modo nativo". Una vez creada, no se puede cambiar.

**Cómo resolverlo:**
1. Crea un nuevo proyecto GCP (el modo Firestore no se puede cambiar en un proyecto existente).
2. Repite todos los pasos de configuración desde el Paso 4 en el nuevo proyecto, asegurándote de seleccionar **Modo nativo** en el Paso 7.

---

### ❌ El webhook responde con error 500 / SERVICES_AVAILABLE: false

**Qué ves:** Al abrir `/status` ves `SERVICES_AVAILABLE: false` o cada webhook devuelve un error.

**Por qué ocurre:** Una o más variables de entorno obligatorias no están configuradas en Cloud Run.

**Cómo resolverlo:**
1. Revisa los registros del servicio en Google Cloud Console → Cloud Run → `unified-webhook` → Registros.
2. Busca el mensaje `Services not properly initialized. Check environment variables.`
3. Identifica qué variable falta y agrégala con:
   ```cmd
   gcloud run services update unified-webhook --region us-central1 ^
     --update-env-vars NOMBRE_VARIABLE=VALOR
   ```

---

### ❌ Error de autenticación SMTP al enviar correos

**Qué ves:** En los registros: `smtplib.SMTPAuthenticationError: 535 Authentication failed`

**Por qué ocurre:** `EMAIL_PASS` tiene la contraseña normal de Gmail en lugar de una "Contraseña de aplicación".

**Cómo resolverlo:**
1. Sigue las instrucciones del Paso 11 para generar una Contraseña de aplicación Gmail.
2. Actualiza la variable:
   ```cmd
   gcloud run services update unified-webhook --region us-central1 ^
     --update-env-vars EMAIL_PASS=NUEVA_CONTRASENA
   ```
3. Verifica en los registros que el siguiente envío funciona.

---

### ❌ Webhook acepta eventos pero todos los IDs de evaluación son desconocidos

**Qué ves:** En los registros: `Unknown assessment ID` o `IDS_XLSX_GCS_PATH load failure`

**Por qué ocurre:** El archivo `ids.xlsx` no se subió al bucket de GCS, o se subió a la ruta incorrecta.

**Cómo resolverlo:**
1. Verifica que el archivo existe en el bucket:
   ```cmd
   gcloud storage ls gs://TU_PROJECT_ID-mapping/
   ```
2. Si no aparece `ids.xlsx`, súbelo:
   ```cmd
   gcloud storage cp inputs\ids.xlsx gs://TU_PROJECT_ID-mapping/ids.xlsx
   ```
3. Verifica que `IDS_XLSX_GCS_PATH` en Cloud Run apunta a `gs://TU_PROJECT_ID-mapping/ids.xlsx`.

---

### ❌ Los informes se reciben pero nunca se procesan

**Qué ves:** Los eventos de webhook llegan (aparecen en Firestore) pero no se generan PDF ni se envían correos.

**Por qué ocurre:** `PROCESS_BATCH_URL` apunta a una URL incorrecta o vacía, por lo que Cloud Tasks no puede llamar al endpoint de procesamiento.

**Cómo resolverlo:**
1. Obtén la URL correcta:
   ```cmd
   gcloud run services describe unified-webhook --region us-central1 ^
     --format="value(status.url)"
   ```
2. La `PROCESS_BATCH_URL` debe ser esa URL + `/process-batch`.
3. Actualiza:
   ```cmd
   gcloud run services update unified-webhook --region us-central1 ^
     --update-env-vars PROCESS_BATCH_URL=https://TU_URL/process-batch
   ```

---

*Guía generada para el Sistema de Reportes M30M — Si tienes problemas no cubiertos en esta guía, contacta al equipo de desarrollo.*
