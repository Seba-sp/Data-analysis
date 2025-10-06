# 🧠 Generador de Guías Escolares - M30M

Sistema automatizado para la creación de guías escolares filtradas por tema, habilidad, dificultad, etc., a partir de un conjunto de preguntas clasificadas en Word y Excel.

## 📋 Características

- **Procesamiento de documentos Word**: Divide archivos Word con múltiples preguntas en archivos individuales
- **Generación de IDs únicos**: Crea identificadores únicos para cada pregunta basados en metadatos
- **Procesamiento de Excel**: Actualiza archivos Excel con rutas y metadatos de preguntas
- **Consolidación**: Combina múltiples archivos Excel en archivos maestros por asignatura
- **Aplicación web**: Interfaz Streamlit para generar guías personalizadas con filtros avanzados
- **Seguimiento de uso**: Sistema de tracking para monitorear qué preguntas se han usado en cada guía
- **Gestión de nombres**: Base de datos de nombres de guías permitidos por asignatura
- **Asignaturas combinadas**: Soporte para "Ciencias" que combina Física, Química y Biología
- **Filtros avanzados**: Filtrado por preguntas libres/usadas, orden personalizable, vista previa de contenido
- **Exportación múltiple**: Generación de guías en formato Word con numeración automática

## 🏗️ Arquitectura del Proyecto

```
generador-guias/
├── storage.py                    # Abstracción de almacenamiento (local/GCS)
├── config.py                     # Configuración del sistema
├── id_generator.py              # Generación de PreguntaID únicos
├── question_processor.py        # Procesamiento de documentos Word
├── excel_processor.py           # Procesamiento de archivos Excel
├── master_consolidator.py       # Consolidación de archivos maestros
├── usage_tracker.py             # Seguimiento de uso de preguntas
├── main.py                      # Punto de entrada CLI
├── requirements.txt             # Dependencias
├── streamlit_app/
│   └── app.py                   # Aplicación principal Streamlit
├── input/                       # Archivos de entrada (Word + Excel)
├── output/
│   ├── preguntas_divididas/     # Archivos de preguntas individuales
│   │   ├── M30M/               # Matemática
│   │   ├── L30M/               # Lenguaje
│   │   ├── H30M/               # Historia
│   │   ├── B30M/               # Biología
│   │   ├── Q30M/               # Química
│   │   └── F30M/               # Física
│   ├── excels_actualizados/     # Archivos Excel actualizados
│   ├── excels_maestros/         # Archivos Excel maestros consolidados
│   └── nombres_guias.xlsx       # Base de datos de nombres permitidos
└── planning.md                  # Documentación de planificación
```

## 🚀 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd generador-guias
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicializar directorios**:
   ```bash
   python main.py init
   ```

## 📖 Uso

### Procesamiento de un conjunto de archivos

```bash
# Procesar archivos con el mismo nombre base
python main.py process-set N1-GA10-Estandarizada --subject F30M

# Procesar archivos con nombres diferentes
python main.py process-files input/documento.docx input/etiquetas.xlsx --subject M30M
```

### Consolidación de archivos Excel

```bash
# Consolidar una asignatura específica
python main.py consolidate --subject F30M

# Consolidar todas las asignaturas
python main.py consolidate --all-subjects

# Consolidar solo Ciencias (F30M + Q30M + B30M)
python main.py consolidate --subject Ciencias
```

### Aplicación web Streamlit

```bash
streamlit run streamlit_app/app.py
```

### Inicialización del sistema

```bash
# Crear directorios necesarios
python main.py init

# Verificar configuración
python config.py
```

## 📊 Formato de datos

### Archivo Word de entrada
- Documento con ~25 preguntas numeradas
- Formato PSU con alternativas A, B, C, D
- 1 pregunta por página

### Archivo Excel de entrada
Columnas requeridas:
- `Eje temático`: Ej: Física, Matemática, Lenguaje
- `Área temática`: Ej: Ondas, Geometría, Lectura literal
- `Conocimiento/Subtema`: Subtema específico
- `Habilidad`: Habilidad cognitiva evaluada
- `Dificultad`: 1,2,3 (Baja, Media o Alta)
- `Clave`: Letra de la respuesta correcta (A–E)
- `Fecha creación`: Fecha de creación

### PreguntaID generado
Formato: `{EJE}-{AREA}-{SUBTEMA}-{HABILIDAD}-{DIFICULTAD}-{CLAVE}-{RANDOM}`

Ejemplo: `FIS-OND-LONG-ANA-MED-C-A1B2`

## 🔧 Configuración

### Variables de entorno (opcional)
- `STORAGE_BACKEND`: Backend de almacenamiento (`local` o `gcp`)
- `GCP_BUCKET_NAME`: Nombre del bucket de Google Cloud Storage

### Personalización
Edita `config.py` para:
- **Rutas de directorios**: Modificar ubicaciones de input/output
- **Mapeos de asignaturas**: Cambiar códigos de asignaturas (M30M, F30M, etc.)
- **Configuración de IDs**: Ajustar formato y longitud de PreguntaID
- **Columnas de Excel**: Personalizar nombres de columnas requeridas
- **Seguimiento de uso**: Configurar columnas de tracking de uso
- **Nombres de guías**: Ruta al archivo de nombres permitidos
- **Colores de gráficos**: Paleta de colores para visualizaciones

### Configuración de seguimiento de uso
El sistema incluye tracking automático de uso de preguntas:
- **Número de usos**: Contador de veces que se ha usado cada pregunta
- **Nombres de guías**: Registro de en qué guías se ha usado
- **Fechas de descarga**: Timestamp de cada uso
- **Filtros de uso**: Opción de filtrar por preguntas libres/usadas

## 📱 Aplicación web

La aplicación Streamlit incluye las siguientes funcionalidades:

### 1. **Carga de datos**
- Selección de asignatura (M30M, L30M, H30M, B30M, Q30M, F30M, Ciencias)
- Carga automática del archivo maestro consolidado
- Validación de datos y estructura

### 2. **Filtros avanzados**
- **Área temática**: Filtrado por áreas específicas de la asignatura
- **Dificultad**: Niveles 1, 2, 3 (Baja, Media, Alta)
- **Habilidad**: Tipos de habilidades cognitivas
- **Subtema**: Filtrado por conocimiento específico
- **Estado de uso**: Preguntas libres vs. usadas (con contador)
- **Orden personalizable**: Ordenar por diferentes criterios

### 3. **Vista previa y selección**
- **Vista previa de contenido**: Visualización completa de preguntas con formato HTML
- **Soporte para ecuaciones**: Renderizado de fórmulas matemáticas
- **Selección múltiple**: Checkbox para elegir preguntas específicas
- **Contador dinámico**: Número de preguntas seleccionadas en tiempo real

### 4. **Gestión de nombres**
- **Base de datos de nombres**: Lista desplegable con nombres permitidos por asignatura
- **Validación automática**: Solo permite nombres predefinidos
- **Gestión centralizada**: Archivo Excel con nombres autorizados

### 5. **Generación de guías**
- **Exportación a Word**: Generación de documentos .docx
- **Numeración automática**: Preguntas numeradas secuencialmente
- **Formato preservado**: Mantiene el formato original de las preguntas
- **Seguimiento automático**: Actualiza el contador de uso de preguntas

### 6. **Características adicionales**
- **Interfaz responsiva**: Diseño adaptativo para diferentes pantallas
- **Preservación de scroll**: Mantiene posición al recargar
- **Estadísticas visuales**: Gráficos de distribución de preguntas
- **Manejo de errores**: Mensajes informativos y recuperación automática

## 🛠️ Desarrollo

### Estructura de módulos

- **`storage.py`**: Abstracción para operaciones de archivo (local/GCS)
- **`config.py`**: Configuración centralizada del sistema
- **`id_generator.py`**: Generación de IDs únicos con abreviaciones
- **`question_processor.py`**: División de documentos Word en preguntas individuales
- **`excel_processor.py`**: Operaciones con archivos Excel y actualización de metadatos
- **`master_consolidator.py`**: Consolidación de archivos maestros por asignatura
- **`usage_tracker.py`**: Seguimiento de uso de preguntas en guías generadas
- **`main.py`**: Interfaz de línea de comandos
- **`streamlit_app/app.py`**: Aplicación web con interfaz de usuario

### Agregar nuevas funcionalidades

1. **Nuevos filtros**: Modificar `streamlit_app/app.py` en la sección de filtros
2. **Nuevos formatos**: Extender `question_processor.py` para soportar otros formatos
3. **Nuevas columnas**: Actualizar `config.py` y los procesadores correspondientes
4. **Nuevos backends**: Extender `storage.py` para otros sistemas de almacenamiento
5. **Nuevas asignaturas**: Agregar códigos en `config.py` y crear directorios
6. **Nuevos tipos de seguimiento**: Extender `usage_tracker.py` con más métricas

### Flujo de datos

1. **Entrada**: Archivos Word + Excel en `input/`
2. **Procesamiento**: División de preguntas y generación de IDs
3. **Actualización**: Excel actualizado con rutas y metadatos
4. **Consolidación**: Archivos maestros por asignatura
5. **Uso**: Aplicación web para generar guías personalizadas
6. **Tracking**: Seguimiento automático de uso de preguntas

## 🧪 Pruebas

```bash
# Probar generación de IDs
python id_generator.py

# Probar procesamiento de preguntas
python question_processor.py

# Probar procesamiento de Excel
python excel_processor.py

# Probar consolidación
python master_consolidator.py
```

## 📝 Notas

- El sistema mantiene el formato original de las preguntas
- Los archivos se organizan por asignatura en subdirectorios
- Se eliminan duplicados automáticamente durante la consolidación
- La aplicación web requiere archivos maestros consolidados
- El seguimiento de uso se actualiza automáticamente al generar guías
- Los nombres de guías deben estar predefinidos en la base de datos

## 🆕 Funcionalidades implementadas recientemente

### ✅ Completadas
- **Lista desplegable en subtema**: Filtrado mejorado por subtemas específicos
- **Vista de 3 ciencias simultáneas**: Soporte para asignatura "Ciencias" combinada
- **Orden de preguntas**: Funcionalidad para ordenar preguntas por diferentes criterios
- **Renderizado de ecuaciones**: Soporte para visualizar fórmulas matemáticas en HTML
- **Numeración automática**: Preguntas numeradas automáticamente en documentos Word
- **Ordenamiento directo**: Opción de ordenar preguntas directamente en la interfaz
- **Base de datos de nombres**: Sistema de gestión de nombres de guías permitidos
- **Lista desplegable de nombres**: Selección de nombres desde base de datos centralizada
- **Seguimiento de uso**: Sistema completo de tracking de preguntas usadas
- **Filtros de uso**: Opción de filtrar por preguntas libres o usadas

### 🔄 En desarrollo
- **Manejo de errores**: Sistema para eliminar guías con errores y limpiar base de datos
- **Estandarización de CL**: Revisión y estandarización de texto asociado en base de datos

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es parte del sistema M30M de generación de contenido educativo dinámico.
