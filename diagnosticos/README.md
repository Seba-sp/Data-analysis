# Sistema de Diagnósticos - M30M

Un sistema completo para la gestión, análisis y reporte de evaluaciones diagnósticas educativas. El sistema procesa datos de evaluaciones desde LearnWorlds, genera reportes personalizados en PDF y envía resultados por email.

## 🎯 Descripción

Este proyecto es una plataforma integral que maneja evaluaciones diagnósticas para diferentes materias (CIEN, CL, HYST, M1). El sistema incluye:

- **Descarga automática** de evaluaciones desde LearnWorlds API
- **Procesamiento incremental** de datos para eficiencia
- **Análisis detallado** de resultados por materia y nivel
- **Generación de reportes** personalizados en PDF
- **Envío automático** de resultados por email
- **API webhook** para procesamiento en tiempo real
- **Almacenamiento flexible** (local o Google Cloud Storage)

## 📁 Estructura del Proyecto

```
diagnosticos/
├── data/                          # Datos del sistema
│   ├── analysis/                  # Datos analizados (CSV)
│   ├── processed/                 # Datos procesados (CSV)
│   ├── questions/                 # Archivos de preguntas
│   └── raw/                       # Datos JSON originales
├── templates/                     # Plantillas HTML para reportes
│   ├── M1.html                    # Plantilla para M1
│   ├── CL.html                    # Plantilla para CL
│   ├── CIEN.html                  # Plantilla para CIEN
│   └── HYST.html                  # Plantilla para HYST
├── reports/                       # Reportes PDF generados
├── main.py                        # Script principal con CLI
├── assessment_downloader.py       # Descarga de evaluaciones
├── assessment_analyzer.py         # Análisis de resultados
├── report_generator.py            # Generación de reportes PDF
├── send_emails.py                 # Envío automático de emails
├── webhook_service.py             # Servicio webhook
├── webhook_main.py                # Servidor webhook Flask
├── drive_service.py               # Integración con Google Drive
├── storage.py                     # Gestión de almacenamiento
├── email_sender.py                # Configuración de emails
├── setup_data.py                  # Configuración inicial
├── processed_emails.csv           # Registro de emails enviados
└── Dockerfile                     # Configuración Docker
```

## 🚀 Características Principales

### 📊 Análisis de Evaluaciones
- Procesa evaluaciones de 4 materias: **CIEN**, **CL**, **HYST**, **M1**
- **M1**: Análisis basado en dificultad (niveles 1-3)
- **CL**: Análisis basado en habilidades (Localizar, Interpretar, Evaluar)
- **CIEN**: Análisis por materias (Biología, Química, Física)
- **HYST**: Análisis basado en porcentaje general
- Calcula porcentajes por materia y nivel
- Identifica lecciones aprobadas y reprobadas
- Genera estadísticas detalladas de rendimiento

### 📋 Generación de Reportes
- **Reportes PDF**: Generación automática desde plantillas HTML
- **Plantillas personalizadas** por tipo de evaluación
- **Formato Excel-compatible** con separadores españoles (; y ,)
- **Diseño profesional** con tablas de resultados

### 📧 Sistema de Emails
- Envío automático de reportes por email
- **Seguimiento de emails** enviados para evitar duplicados
- Configuración SMTP flexible
- Plantillas HTML personalizadas

### 🔗 Integración Webhook
- **API REST** para recibir datos de evaluaciones en tiempo real
- **Validación de firma** LearnWorlds
- Procesamiento automático de nuevos resultados
- Respuestas JSON estructuradas
- Manejo de errores robusto

### 🔄 Procesamiento Incremental
- **Descarga incremental** de nuevos datos
- **Procesamiento eficiente** solo de datos nuevos
- **Merging automático** de datos incrementales
- **Limpieza automática** de archivos temporales

## 🛠️ Instalación y Configuración

### Requisitos Previos
- Python 3.9+
- Acceso a LearnWorlds API
- Servidor SMTP para emails
- Almacenamiento para datos y reportes

### Variables de Entorno Requeridas

```bash
# LearnWorlds API
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret

# Assessment IDs
M1_ASSESSMENT_ID=assessment_id_1
CL_ASSESSMENT_ID=assessment_id_2
CIEN_ASSESSMENT_ID=assessment_id_3
HYST_ASSESSMENT_ID=assessment_id_4

# Email Configuration
EMAIL_FROM=your-email@gmail.com
EMAIL_PASS=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Storage (optional - defaults to local)
STORAGE_BACKEND=local  # or 'gcp'
GCP_BUCKET_NAME=your-bucket-name  # if using GCP

# Date Filter (optional)
MIN_DOWNLOAD_DATE=2024-01-01  # YYYY-MM-DD format
```

### Instalación Local

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd diagnosticos
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

4. **Ejecutar setup inicial**
   ```bash
   python setup_data.py
   ```

### Instalación con Docker

```bash
# Construir imagen
docker build -t diagnosticos .

# Ejecutar contenedor
docker run -p 8080:8080 \
  -e CLIENT_ID=your_client_id \
  -e SCHOOL_DOMAIN=your_school_domain \
  -e ACCESS_TOKEN=your_access_token \
  -e LEARNWORLDS_WEBHOOK_SECRET=your_secret \
  -e EMAIL_FROM=your-email@gmail.com \
  -e EMAIL_PASS=your-app-password \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  diagnosticos
```

## 📖 Uso

### Comandos Principales

#### Descarga de Datos
```bash
# Descarga completa de todas las evaluaciones
python main.py --download

# Descarga incremental (solo nuevos datos)
python main.py --download --incremental

# Descarga de evaluación específica
python main.py --download --assessment M1
```

#### Procesamiento de Datos
```bash
# Procesar todas las evaluaciones (JSON a CSV)
python main.py --process

# Procesamiento incremental
python main.py --process --incremental

# Procesar evaluación específica
python main.py --process --assessment CL
```

#### Análisis de Datos
```bash
# Analizar todas las evaluaciones
python main.py --analyze

# Análisis incremental
python main.py --analyze --incremental

# Analizar evaluación específica
python main.py --analyze --assessment CIEN
```

#### Generación de Reportes
```bash
# Generar todos los reportes
python main.py --reports

# Generar reportes (saltar existentes)
python main.py --reports --skip-existing

# Forzar generación de todos los reportes
python main.py --reports --force-reports

# Generar reportes para evaluación específica
python main.py --reports --assessment HYST
```

#### Verificar Reportes Existentes
```bash
# Verificar todos los reportes
python main.py --check-reports

# Verificar reportes de evaluación específica
python main.py --check-reports --assessment M1
```

#### Limpieza de Archivos Temporales
```bash
# Limpiar archivos temporales
python main.py --cleanup

# Limpiar archivos de evaluación específica
python main.py --cleanup --assessment CL
```

#### Flujo Completo
```bash
# Ejecutar todo el flujo (descarga, procesamiento, análisis, reportes)
python main.py --download --process --analyze --reports

# Flujo incremental completo
python main.py --download --process --analyze --reports --incremental
```

### API Webhook

#### Endpoint
```
POST /webhook
```

#### Headers Requeridos
```
Content-Type: application/json
Learnworlds-Webhook-Signature: v1=signature
```

#### Ejemplo de Payload
```json
{
  "user_id": "user123",
  "email": "student@example.com",
  "assessment_name": "CIEN",
  "grade": 85,
  "passed": true,
  "created": 1756226598.329633
}
```

### Envío de Emails

```bash
# Enviar todos los reportes por email
python send_emails.py

# Enviar reportes de evaluación específica
python send_emails.py --assessment M1

# Verificar emails procesados
python send_emails.py --check-processed
```

## 📊 Estructura de Datos

### Evaluaciones (JSON)
```json
{
  "id": "assessment_id",
  "user_id": "user_id",
  "email": "student@example.com",
  "grade": 85,
  "passed": true,
  "created": 1756226598.329633,
  "answers": [
    {
      "blockId": "question_id",
      "blockType": "mc",
      "description": "Pregunta 1",
      "answer": "C",
      "points": 1,
      "blockMaxScore": 1
    }
  ]
}
```

### Análisis (CSV)
- `email`: Email del estudiante
- `assessment_name`: Nombre de la evaluación
- `level`: Nivel del estudiante
- `overall_percentage`: Porcentaje general
- `total_questions`: Total de preguntas
- `correct_questions`: Preguntas correctas
- `passed_lectures`: Lecciones aprobadas
- `failed_lectures`: Lecciones reprobadas
- Estadísticas específicas por tipo de evaluación

### Tipos de Evaluación

#### M1 (Matemáticas)
- **Tipo**: Basado en dificultad
- **Niveles**: 1-4 (reportados: 1-3)
- **Criterios**: Porcentaje en preguntas de dificultad 1 y 2

#### CL (Comprensión Lectora)
- **Tipo**: Basado en habilidades
- **Habilidades**: Localizar, Interpretar, Evaluar
- **Niveles**: 1-4 (reportados: 1-3)
- **Criterios**: Porcentaje en Interpretar y Evaluar

#### CIEN (Ciencias)
- **Tipo**: Basado en materias
- **Materias**: Biología, Química, Física
- **Niveles**: 1-2
- **Criterios**: Porcentaje por materia y lecciones reprobadas

#### HYST (Historia)
- **Tipo**: Basado en porcentaje general
- **Niveles**: General, Avanzado
- **Criterios**: Porcentaje general de aciertos

## 🔧 Configuración Avanzada

### Almacenamiento
```python
# Local (por defecto)
STORAGE_BACKEND=local

# Google Cloud Storage
STORAGE_BACKEND=gcp
GCP_BUCKET_NAME=your-bucket-name
```

### Filtros de Fecha
```bash
# Solo descargar datos desde una fecha específica
MIN_DOWNLOAD_DATE=2024-01-01
```

### Logging
El sistema genera logs detallados para:
- Descarga de evaluaciones
- Procesamiento de datos
- Análisis de resultados
- Generación de reportes
- Envío de emails
- Errores y excepciones

## 🚀 Despliegue

### Producción con Docker
```bash
# Construir y ejecutar
docker build -t diagnosticos .
docker run -d -p 8080:8080 --name diagnosticos-app diagnosticos

# Con docker-compose
docker-compose up -d
```

### Monitoreo
```bash
# Health check
curl http://localhost:8080/healthz

# Logs
docker logs diagnosticos-app

# Estado del servicio
curl http://localhost:8080/
```

### Escalabilidad
- **Procesamiento incremental** para eficiencia
- **Almacenamiento en la nube** para escalabilidad
- **API webhook** para procesamiento en tiempo real
- **Docker** para despliegue consistente

## 📝 Logs y Monitoreo

El sistema genera logs detallados para:
- Descarga de evaluaciones
- Procesamiento de datos
- Generación de reportes
- Envío de emails
- Errores y excepciones

### Niveles de Log
- **INFO**: Operaciones normales
- **WARNING**: Situaciones que requieren atención
- **ERROR**: Errores que impiden la operación
- **DEBUG**: Información detallada para desarrollo

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte técnico o preguntas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo
- Revisar la documentación técnica

## 🔄 Actualizaciones

### v2.0.0 (Actual)
- Sistema completo de análisis de evaluaciones
- Procesamiento incremental para eficiencia
- Generación de reportes PDF automática
- Sistema de emails con seguimiento
- API webhook para tiempo real
- Soporte para almacenamiento en la nube
- CLI completo con múltiples opciones

### Próximas características
- Dashboard web para visualización
- Análisis predictivo
- Reportes comparativos
- Integración con más LMS
- API REST completa
