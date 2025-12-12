# 🧠 Generador de Guías Escolares - M30M

Sistema automatizado para la creación de guías escolares filtradas por tema, habilidad, dificultad, etc., a partir de un conjunto de preguntas clasificadas en Word y Excel.

## 📋 Características

### 🎯 Procesamiento de Documentos
- **División de documentos Word**: Divide archivos Word con múltiples preguntas (1 por página) en archivos individuales
- **Preservación total de formato**: Mantiene imágenes, tablas, ecuaciones y todo el formato original usando ZIP structure
- **Validación automática**: Verifica coincidencia entre número de preguntas en Word y Excel
- **Generación de IDs únicos**: Crea identificadores únicos con formato `{EJE}-{AREA}-{SUBTEMA}-{HABILIDAD}-{DIFICULTAD}-{CLAVE}-{RANDOM8}` (ej: `NUM-CON-OPE-RES-1-D-LX63VU56`)

### 📊 Gestión de Excel
- **Procesamiento de Excel**: Actualiza archivos Excel con rutas relativas y metadatos de preguntas
- **Validación de estructura**: Detecta columnas faltantes, valores vacíos y valores inválidos
- **Consolidación maestro**: Combina múltiples archivos Excel en archivos maestros por asignatura
- **Consolidación incremental (DEFAULT)**: Solo consolida archivos nuevos (no procesados previamente) - más rápido
- **Consolidación completa**: Opción de resetear el maestro y procesar todos los archivos con flag `--full`
- **Auto-ajuste de columnas**: Formato automático con ancho óptimo de columnas

### 🌐 Aplicación Web Streamlit
- **Interfaz moderna**: Interfaz web completa con diseño responsivo y preservación de scroll
- **Filtros avanzados**: Por área temática, subtema (dinámico), descripción (búsqueda de texto), habilidad, dificultad y asignatura (para Ciencias)
- **Vista previa**: Conversión de documentos Word a imágenes PNG usando LibreOffice para preview completo
- **Selección múltiple**: Sistema de checkboxes con orden personalizable mediante drag-and-drop
- **Reordenamiento**: Mover preguntas a posiciones específicas con preview visual
- **Ordenamiento automático**: Por área temática o asignatura (para Ciencias)
- **Gráficos resumen**: Pie charts con distribución por asignatura, área, habilidad, dificultad y subtema

### 📝 Generación de Guías
- **Exportación a Word**: Fusión perfecta de documentos Word preservando todo el formato
- **Numeración automática**: Preguntas numeradas secuencialmente (1., 2., 3., etc.)
- **Excel resumen**: Archivo Excel con PreguntaID, número de pregunta, clave correcta y enlace a video explicativo
- **Paquete completo**: Descarga ZIP con Word (estudiantes), Excel (profesores) y README
- **Gestión de imágenes**: Sistema de mapeo y copia inteligente de imágenes con nombres únicos
- **Relaciones preservadas**: Actualización automática de relationship IDs para imágenes
- **Configuración A4**: Márgenes de 2.54 cm en todos los lados, tamaño A4 estándar

### 📈 Seguimiento de Uso
- **Tracking completo**: Monitorea qué preguntas se han usado en cada guía con timestamp
- **Columnas dinámicas**: Crea nuevas columnas automáticamente para cada uso (`Nombre guía (uso 1)`, `Fecha descarga (uso 1)`, etc.)
- **Estadísticas de uso**: Obtiene distribución de uso, preguntas no usadas y porcentaje de uso
- **Estadísticas generales**: Gráficos de barras y pie charts para ver distribución por área, habilidad y dificultad de todas las preguntas
- **Gestión de guías**: Lista todas las guías creadas con detalles de preguntas y fechas
- **Eliminación selectiva**: Elimina guías específicas y actualiza contadores de uso

### 🎓 Asignaturas Combinadas
- **Soporte para Ciencias**: Combina Física (F30M), Química (Q30M) y Biología (B30M) en una sola vista
- **Identificación de origen**: Columna `Subject_Source` para identificar la asignatura original
- **Filtrado por asignatura**: En Ciencias, permite filtrar por F30M, Q30M o B30M
- **Consolidación cruzada**: Actualiza tracking en los tres archivos maestros simultáneamente

### 💾 Almacenamiento Flexible
- **Backend configurable**: Soporte para almacenamiento local o Google Cloud Storage (GCS)
- **Abstracción completa**: API unificada para operaciones de lectura/escritura independiente del backend
- **Gestión de directorios**: Creación automática de estructura de carpetas necesaria

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
├── main.py                      # Punto de entrada CLI con modo interactivo
├── requirements.txt             # Dependencias
├── streamlit_app/
│   └── app.py                   # Aplicación principal Streamlit
├── input/                       # Archivos de entrada organizados por asignatura
│   ├── M30M/                   # Matemática (pares Word + Excel)
│   ├── L30M/                   # Lenguaje (pares Word + Excel)
│   ├── H30M/                   # Historia (pares Word + Excel)
│   ├── B30M/                   # Biología (pares Word + Excel)
│   ├── Q30M/                   # Química (pares Word + Excel)
│   └── F30M/                   # Física (pares Word + Excel)
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

### Requisitos previos
- Python 3.8 o superior
- LibreOffice (para preview de documentos en la aplicación web)
  - Windows: Descargar desde [libreoffice.org](https://www.libreoffice.org/download/download/)
  - Linux: `sudo apt-get install libreoffice`
  - macOS: `brew install --cask libreoffice`

### Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd generador-guias
   ```

2. **Instalar dependencias** (versiones exactas probadas):
   ```bash
   pip install -r requirements.txt
   ```
   
   Dependencias principales:
   - `pandas==2.2.2` - Procesamiento de datos
   - `openpyxl==3.1.5` - Lectura/escritura de Excel
   - `python-docx==1.2.0` - Procesamiento de documentos Word
   - `pillow==11.3.0` - Procesamiento de imágenes
   - `matplotlib==3.9.2` - Gráficos
   - `streamlit==1.37.1` - Aplicación web
   - `plotly==5.24.1` - Gráficos interactivos
   - `unidecode==1.3.8` - Normalización de texto
   - `mammoth==1.11.0` - Conversión de documentos
   - `reportlab==4.4.3` - Generación de PDFs
   - `google-cloud-storage==3.2.0` - Almacenamiento en nube (opcional)

3. **Inicializar directorios**:
   ```bash
   python main.py init
   ```

4. **Configurar variables de entorno** (opcional para Google Cloud Storage):
   ```bash
   export STORAGE_BACKEND=local  # o 'gcp' para Google Cloud Storage
   export GCP_BUCKET_NAME=your-bucket-name  # solo si usas GCS
   ```

## 📖 Uso

### 1️⃣ Procesamiento de archivos (CLI)

Coloca tus archivos Word (.docx) y Excel (.xlsx) con el mismo nombre base en carpetas por asignatura dentro de `input/`:

**Estructura de carpetas:**
```
input/
├── F30M/              # Física
│   ├── ensayo1.docx
│   ├── ensayo1.xlsx
│   ├── guia2.docx
│   └── guia2.xlsx
├── M1/              # Matemática
│   ├── test.docx
│   └── test.xlsx
└── ... (otras asignaturas)
```

**Modo interactivo (recomendado):**
```bash
# Ejecutar sin argumentos para usar menús interactivos
python main.py process-set

# El sistema te mostrará un menú como este:
# ============================================================
# SELECT SUBJECT FOLDER
# ============================================================
#   [1] F30M (3 file pairs)
#   [2] M30M (5 file pairs)
#   [3] H30M (2 file pairs)
#   [0] Cancel
# ============================================================
# Enter your choice (number): 1

# Luego te muestra los archivos disponibles:
# ============================================================
# SELECT FILE PAIR IN F30M
# ============================================================
#   [1] ensayo1
#       • ensayo1.docx
#       • ensayo1.xlsx
#   
#   [2] guia-fisica-ondas
#       • guia-fisica-ondas.docx
#       • guia-fisica-ondas.xlsx
#   
#   [0] Go back
# ============================================================
# Enter your choice (number): 2

# El sistema procesa automáticamente el conjunto seleccionado
```

**Modo directo (legacy):**
```bash
# Procesar un conjunto específico directamente
python main.py process-set "N1-GA10-Estandarizada" --subject F30M

# El sistema busca los archivos en input/F30M/ y:
# 1. Lee el archivo Excel y genera PreguntaIDs únicos
# 2. Valida la estructura del Excel (columnas, valores)
# 3. Divide el Word en preguntas individuales (1 por página)
# 4. Verifica que Word y Excel tengan el mismo número de preguntas
# 5. Guarda las preguntas individuales en output/preguntas_divididas/{subject}/
# 6. Actualiza el Excel con rutas relativas y lo guarda en output/excels_actualizados/{subject}/
```

**Validaciones automáticas:**
- ❌ Si el archivo ya fue procesado anteriormente: **DETIENE el procesamiento** (evita duplicados)
- ❌ Si hay valores inválidos en `Clave` (debe ser A, B, C o D) o `Dificultad` (debe ser 1, 2 o 3): **DETIENE el procesamiento**
- ⚠️ Si hay columnas faltantes o valores vacíos: **Muestra advertencias pero CONTINÚA**
- ❌ Si el número de preguntas en Word y Excel no coincide: **DETIENE el procesamiento**

**Protección contra duplicados:**
El sistema detecta automáticamente si un archivo ya fue procesado verificando la existencia del archivo actualizado en `output/excels_actualizados/{subject}/`. Si intenta procesar un archivo que ya existe:
- 🛑 Detiene el procesamiento
- 📋 Muestra la ubicación del archivo ya procesado
- 💡 Proporciona instrucciones para reprocesar si es necesario (debe eliminar el archivo existente primero)

### 2️⃣ Consolidación de archivos Excel

Combina todos los archivos Excel procesados en un archivo maestro por asignatura:

```bash
# Consolidar una asignatura específica (incremental - solo archivos nuevos)
python main.py consolidate --subject F30M

# Consolidar todas las asignaturas a la vez (incremental)
python main.py consolidate --all-subjects

# El sistema (modo incremental - DEFAULT):
# 1. Identifica archivos Excel que NO están en el maestro actual
# 2. Lee solo los archivos nuevos de output/excels_actualizados/{subject}/
# 3. Combina las filas nuevas
# 4. Elimina duplicados basándose en PreguntaID
# 5. AGREGA al archivo maestro existente en output/excels_maestros/excel_maestro_{subject}.xlsx
# 6. Agrega columna "Archivo origen" para rastrear procedencia
```

**Consolidación completa** (resetea el archivo maestro):
```bash
# Consolida TODOS los archivos (resetea el maestro)
python main.py consolidate --subject M30M --full

# Consolidar todas las asignaturas en modo completo
python main.py consolidate --all-subjects --full

# Útil cuando necesitas reconstruir el maestro desde cero
```

### 3️⃣ Aplicación web Streamlit

Interfaz gráfica completa para generar guías personalizadas:

```bash
# Opción 1: Launcher con selección de asignatura en terminal
python streamlit_app/launch_app.py

# Opción 2: Ejecutar directamente
streamlit run streamlit_app/app.py
```

**Flujo de trabajo en la aplicación:**

1. **Cargar datos**: Selecciona una asignatura (M30M, L30M, H30M, B30M, Q30M, F30M, o Ciencias)
2. **Filtrar preguntas**: Usa los filtros de área, subtema, habilidad, dificultad
3. **Seleccionar preguntas**: Marca las preguntas que deseas incluir (con preview)
4. **Reordenar**: Arrastra y suelta para cambiar el orden, o usa ordenamiento automático
5. **Ver resumen**: Revisa los gráficos de distribución de preguntas seleccionadas
6. **Generar guía**: Descarga el documento Word con numeración automática

**Características especiales:**
- 👁️ Vista previa de cada pregunta (conversión a imágenes PNG)
- 📊 Gráficos interactivos de distribución
- 🔄 Reordenamiento visual con selección de posición
- 📈 Estadísticas en tiempo real
- 💾 Guardado automático de posición de scroll

### 4️⃣ Comandos adicionales

```bash
# Inicializar directorios del sistema
python main.py init

# Verificar configuración actual
python config.py

# Probar generación de IDs (modo desarrollo)
python id_generator.py

# Probar procesamiento de Excel (modo desarrollo)
python excel_processor.py

# Probar consolidación (modo desarrollo)
python master_consolidator.py
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
- `Unidad temática`: Subtema específico (también conocido como Conocimiento/Subtema)
- `Habilidad`: Habilidad cognitiva evaluada
- `Dificultad`: 1, 2, 3 (Baja, Media o Alta)
- `Clave`: Letra de la respuesta correcta (A, B, C, D o E)
- `Descripción`: Descripción breve de la pregunta o concepto evaluado
- `Fecha creacion`: Fecha de creación de la pregunta

Columnas opcionales:
- `Enlace video`: URL de video explicativo de la pregunta (se incluye automáticamente en el Excel resumen al descargar guías)

### PreguntaID generado

Formato: `{EJE}-{AREA}-{SUBTEMA}-{HABILIDAD}-{DIFICULTAD}-{CLAVE}-{RANDOM8}`

**Componentes:**
- **EJE**: Abreviación de 3 letras del Eje temático (ej: `NUM` para Números)
- **AREA**: Abreviación de 3 letras del Área temática (ej: `CON` para Conjuntos)
- **SUBTEMA**: Abreviación de 3 letras del Conocimiento/Subtema (ej: `OPE` para Operaciones)
- **HABILIDAD**: Abreviación de 3 letras de la Habilidad (ej: `RES` para Resolver problemas)
- **DIFICULTAD**: Abreviación de 3 letras de la Dificultad (ej: `1`, `2`, `3`)
- **CLAVE**: Letra de respuesta correcta (A, B, C, o D)
- **RANDOM8**: Sufijo aleatorio de 8 caracteres con patrón `LLNNLLNN` (ej: `LX63VU56`)
  - L = Letra mayúscula (A-Z)
  - N = Número (0-9)

**Ejemplos reales:**
- `NUM-CON-OPE-RES-1-D-LX63VU56` (Matemática - Números, Conjuntos, Operaciones, Resolver problemas, Dificultad 1, Clave D)
- `NUM-CON-OPE-RES-1-C-ET72PM50` (Matemática - Números, Conjuntos, Operaciones, Resolver problemas, Dificultad 1, Clave C)
- `FIS-OND-LONG-ANA-2-C-A1B2C3D4` (Física - Ondas, Longitud de onda, Análisis, Dificultad 2, Clave C)

**Ventajas del formato:**
- ✅ Único e irrepetible (sufijo aleatorio de 8 caracteres)
- ✅ Descriptivo (contiene información de la pregunta)
- ✅ Validable (patrón específico LLNNLLNN en el sufijo)
- ✅ Compatible con nombres de archivo en todos los sistemas operativos

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

## 📱 Aplicación web Streamlit

La aplicación web completa incluye las siguientes funcionalidades:

### 1. **Carga de datos**
- Selección de asignatura: M1, M2, H30M, B30M, Q30M, F30M, o Ciencias
- Carga automática del archivo maestro consolidado
- Para "Ciencias": combina automáticamente F30M + Q30M + B30M
- Validación de datos y estructura
- Métricas en tiempo real: total preguntas, áreas, dificultades, habilidades

### 2. **Filtros avanzados y dinámicos**
- **Asignatura** (solo para Ciencias): Filtrar por F30M, Q30M, B30M o todas
- **Área temática**: Filtrado por áreas específicas de la asignatura
- **Subtema**: Filtrado dinámico que se actualiza según área y asignatura seleccionadas
- **Descripción**: Búsqueda por texto en las descripciones de preguntas (búsqueda parcial, no distingue mayúsculas/minúsculas)
- **Habilidad**: Tipos de habilidades cognitivas evaluadas
- **Dificultad**: Niveles 1, 2, 3 (Baja, Media, Alta)
- **Filtro de uso**: Filtra preguntas por número de veces que han sido usadas (sin usar, 1 vez, 2 veces, etc.)
- **Contador de resultados**: Muestra cuántas preguntas cumplen los filtros

### 3. **Vista previa y selección**
- **Vista previa completa**: Conversión Word→PNG usando LibreOffice
- **Preview inline**: Se muestra debajo de cada pregunta seleccionada
- **Botón de cerrar**: Cierra la vista previa sin recargar la página
- **Selección múltiple**: Sistema de checkboxes para elegir preguntas
- **Información detallada**: Muestra PreguntaID, área, dificultad, habilidad y subtema
- **Identificación de origen**: En Ciencias, muestra la asignatura origen [F30M], [Q30M] o [B30M]

### 4. **Reordenamiento de preguntas**
- **Sistema visual**: Selecciona pregunta y elige posición target
- **Preview de posiciones**: Muestra "antes de {pregunta}" para cada posición
- **Botones de ordenamiento**:
  - 📚 Ordenar por asignatura (solo Ciencias): Agrupa por F30M, Q30M, B30M
  - 📊 Ordenar por área: Agrupa por área temática
- **Lista ordenada**: Muestra preguntas en el orden actual con numeración
- **Botón de mover**: Aplica el reordenamiento con un clic

### 5. **Resumen de selección**
- **Métricas**: Total seleccionadas, áreas, dificultades, habilidades
- **Lista completa**: Todas las preguntas seleccionadas con su información
- **Botones por pregunta**:
  - 👁️ Ver preview de la pregunta
  - ❌ Deseleccionar individualmente
- **Gráficos interactivos** (Plotly):
  - Distribución por asignatura (solo Ciencias)
  - Distribución por área temática
  - Distribución por habilidad
  - Distribución por dificultad
  - Distribución por subtema (top 10 + otros)

### 6. **Generación de guías Word**
- **Exportación a Word**: Fusión perfecta de documentos individuales
- **Numeración automática**: Preguntas numeradas secuencialmente (1., 2., 3., etc.)
- **Excel resumen incluido**: Archivo Excel complementario con columnas:
  - `PreguntaID`: Identificador único de cada pregunta
  - `Número`: Posición en la guía (1, 2, 3, etc.)
  - `Clave`: Respuesta correcta (A, B, C, D, E)
  - `Enlace video`: URL del video explicativo (si está disponible)
- **Paquete ZIP**: Descarga completa con Word + Excel + README
- **Preservación total**: Mantiene imágenes, tablas, ecuaciones y todo el formato
- **Timestamp en nombre**: Archivo generado con fecha y hora
- **Descarga inmediata**: Botón de descarga después de generar
- **Resumen final**: Muestra número de preguntas y asignatura

### 7. **Características técnicas**
- **Interfaz responsiva**: Diseño adaptativo con layout wide
- **Preservación de scroll**: JavaScript que mantiene posición al recargar
- **Session state**: Mantiene selecciones y estado entre reruns
- **Caching**: Conversiones PNG cacheadas por 2 horas (TTL=7200s)
- **Manejo de errores**: Mensajes informativos con íconos y colores
- **Performance optimizada**: Timeout de 30s para conversiones LibreOffice
- **Limpieza automática**: Archivos temporales se eliminan después del uso

### 8. **Controles de gestión**
- **Botón "Limpiar Selección"**: Reinicia todas las selecciones
- **Recarga de datos**: Cambia de asignatura y recarga desde cero
- **Info contextual**: Tooltips en todos los botones importantes
- **Feedback visual**: Success/error/warning messages con íconos

## 🛠️ Desarrollo

### Estructura de módulos

#### Core del sistema

- **`main.py`** (~550 líneas)
  - Punto de entrada CLI con argparse
  - Comandos: `process-set` (modo interactivo y directo), `consolidate`, `init`
  - Modo interactivo: menús numerados para seleccionar asignatura y pares de archivos
  - Funciones auxiliares: `select_subject_interactive()`, `select_file_pair_interactive()`
  - Protección contra duplicados: detecta archivos ya procesados y previene reprocesamiento
  - Validaciones críticas: coincidencia Word-Excel, valores inválidos, archivos duplicados
  - Pipeline completo: Excel → Word → Validación → Archivos individuales → Excel actualizado

- **`config.py`** (120 líneas)
  - Configuración centralizada del sistema
  - Mapeo de asignaturas: M30M, L30M, H30M, B30M, Q30M, F30M, Ciencias
  - Configuración de columnas Excel y tracking de uso
  - Función `get_usage_column_names()` para generar nombres de columnas dinámicas
  - Función `ensure_directories()` para crear estructura de carpetas

#### Procesamiento de documentos

- **`question_processor.py`** (518 líneas)
  - División de documentos Word por páginas usando ZIP structure
  - Métodos de detección de límites: numeración o page breaks
  - Preservación total de formato, imágenes y tablas
  - Limpieza de elementos problemáticos (page breaks, section properties)
  - Configuración A4: márgenes 2.54 cm, tamaño estándar

- **`id_generator.py`** (232 líneas)
  - Generación de PreguntaID con formato estructurado
  - Abreviaciones de 3 caracteres con `unidecode` para quitar acentos
  - Sufijo aleatorio de 8 caracteres con patrón LLNNLLNN
  - Funciones de validación y parsing de IDs
  - Sistema de limpieza de texto robusto

#### Gestión de Excel

- **`excel_processor.py`** (271 líneas)
  - Lectura y escritura de archivos Excel con `openpyxl`
  - Generación masiva de PreguntaIDs para DataFrames
  - Validación de estructura: columnas requeridas, valores válidos
  - Actualización de rutas relativas a archivos de preguntas
  - Auto-ajuste de ancho de columnas (10-50 caracteres)

- **`master_consolidator.py`** (533 líneas)
  - Consolidación de múltiples archivos Excel en maestros
  - **Modo incremental (DEFAULT)**: solo archivos nuevos (optimizado, recomendado)
  - Modo completo: procesa todos los archivos (resetea maestro)
  - Eliminación automática de duplicados por PreguntaID
  - Validación de datos consolidados y generación de estadísticas
  - Método `consolidate_all_subjects_incremental()` para procesamiento batch incremental
  - Método `consolidate_all_subjects()` para procesamiento batch completo

#### Tracking y uso

- **`usage_tracker.py`** (609 líneas)
  - Sistema de tracking completo con columnas dinámicas
  - Actualización automática de uso en archivos maestros
  - Soporte para "Ciencias": actualiza F30M, Q30M y B30M simultáneamente
  - Obtención de estadísticas: distribución de uso, preguntas no usadas
  - Gestión de guías: lista, detalles y eliminación selectiva
  - Método `delete_specific_guide_usage()` para eliminar guías precisas
  - Método `_remove_specific_usage_from_question()` con reordenamiento de columnas

#### Almacenamiento

- **`storage.py`** (141 líneas)
  - Abstracción completa para almacenamiento local o GCS
  - API unificada: `read_csv()`, `write_csv()`, `read_json()`, `write_json()`, `read_bytes()`, `write_bytes()`
  - Detección automática de backend por variable de entorno
  - Métodos para listar archivos, crear directorios y eliminar
  - Normalización de rutas (forward slashes para GCS)

#### Aplicación web

- **`streamlit_app/app.py`** (1700 líneas)
  - Aplicación Streamlit completa con interfaz moderna
  - Carga y combinación de datos (incluyendo Ciencias)
  - Filtros dinámicos: subtema se actualiza según área seleccionada
  - Vista previa: conversión Word→PNG usando LibreOffice con cache (2 horas TTL)
  - Sistema de selección con checkboxes y orden personalizable
  - Reordenamiento visual: selector de pregunta + posición target
  - Generación de guías: fusión de documentos Word con ZIP structure
  - Gráficos interactivos: pie charts con Plotly
  - Preservación de scroll: JavaScript para mantener posición

- **`streamlit_app/launch_app.py`** (82 líneas)
  - Launcher con menú de terminal para selección de asignatura
  - Pasa la asignatura como variable de entorno
  - Ejecuta Streamlit con configuración específica

### Tecnologías y patrones

**Procesamiento de Word:**
- ZIP structure manipulation para máxima preservación
- XML parsing con `xml.etree.ElementTree`
- Gestión de relaciones (relationships) para imágenes
- Mapeo de IDs para evitar conflictos

**Procesamiento de Excel:**
- Pandas DataFrames para manipulación de datos
- OpenPyXL para formato y escritura
- Validación por etapas: estructura → valores → relaciones

**Aplicación web:**
- Streamlit con session state para persistencia
- Caching estratégico (@st.cache_data, @st.cache_resource)
- JavaScript inyectado para funcionalidades avanzadas
- Conversión de documentos con subprocess + LibreOffice

**Almacenamiento:**
- Patrón Strategy para backends intercambiables
- Path normalization para compatibilidad multiplataforma
- Gestión de errores granular

### Flujo de datos completo

```
┌─────────────────────────────────────────────────────────────┐
│  1. ENTRADA (input/{subject}/)                              │
│     - archivo.docx (Word con ~25 preguntas, 1 por página)  │
│     - archivo.xlsx (Excel con metadatos)                    │
│     Ejemplo: input/F30M/ensayo1.docx + ensayo1.xlsx         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. PROCESAMIENTO (main.py process-set)                     │
│     Modo interactivo: menú para elegir asignatura y par     │
│     Modo directo: especificar archivo y --subject           │
│     a) Leer Excel y validar estructura                      │
│     b) Generar PreguntaIDs únicos                           │
│     c) Dividir Word en archivos individuales                │
│     d) Validar coincidencia Word-Excel                      │
│     e) Actualizar Excel con rutas                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. SALIDA PROCESADA                                        │
│     - output/preguntas_divididas/{subject}/{PreguntaID}.docx│
│     - output/excels_actualizados/{subject}/archivo_actualizado.xlsx│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. CONSOLIDACIÓN (main.py consolidate)                     │
│     a) Leer todos los excels_actualizados de la asignatura │
│     b) Combinar en un DataFrame                             │
│     c) Eliminar duplicados por PreguntaID                   │
│     d) Agregar columna "Archivo origen"                     │
│     e) Guardar en archivo maestro                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. ARCHIVO MAESTRO                                         │
│     - output/excels_maestros/excel_maestro_{subject}.xlsx   │
│     - Contiene todas las preguntas consolidadas             │
│     - Incluye columnas de tracking de uso                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  6. APLICACIÓN WEB (streamlit_app/app.py)                   │
│     a) Cargar archivo maestro                               │
│     b) Filtrar preguntas (área, subtema, habilidad, etc.)   │
│     c) Vista previa de preguntas (Word→PNG)                 │
│     d) Seleccionar y reordenar preguntas                    │
│     e) Generar guía Word (fusión de documentos)             │
│     f) Actualizar tracking de uso                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  7. GUÍA GENERADA                                           │
│     - guia_{subject}_{timestamp}.docx                       │
│     - Preguntas numeradas secuencialmente                   │
│     - Formato completo preservado                           │
│     - Tracking actualizado en archivo maestro               │
└─────────────────────────────────────────────────────────────┘
```

### Agregar nuevas funcionalidades

**1. Nuevos filtros en la aplicación web:**
```python
# En streamlit_app/app.py, sección de filtros
nuevo_filtro = st.selectbox("Nuevo Filtro", opciones)
filters['nuevo_campo'] = nuevo_filtro

# En función filter_questions()
if filters.get('nuevo_campo'):
    filtered_df = filtered_df[filtered_df['Nuevo Campo'] == filters['nuevo_campo']]
```

**2. Nueva columna en Excel:**
```python
# En config.py
EXCEL_COLUMNS = {
    # ... existentes ...
    "nuevo_campo": "Nuevo Campo"
}

# En excel_processor.py, método generate_pregunta_ids()
# Agregar el nuevo campo al generate_pregunta_id() si es parte del ID

# En question_processor.py, método process_word_document()
# Usar el nuevo campo si es necesario
```

**3. Nueva asignatura:**
```python
# En config.py
SUBJECT_FOLDERS = {
    # ... existentes ...
    "G30M": "G30M"  # Nueva asignatura
}

# Ejecutar
python main.py init  # Crea los directorios automáticamente
```

**4. Nuevo backend de almacenamiento:**
```python
# En storage.py, extender StorageClient
def __init__(self):
    self.backend = os.getenv('STORAGE_BACKEND', 'local')
    
    if self.backend == 's3':  # Nuevo backend
        import boto3
        self.s3_client = boto3.client('s3')
        self.bucket = os.getenv('S3_BUCKET_NAME')
    
# Implementar métodos read_*, write_*, etc. para el nuevo backend
```

### Mejores prácticas

✅ **Usar config.py para valores configurables**: No hardcodear valores numéricos o strings
✅ **Validar entrada temprano**: Detectar errores antes de procesamiento costoso
✅ **Logs descriptivos**: print() con prefijos [ERROR], [WARNING], [INFO]
✅ **Manejo de errores granular**: try-except específicos, no globales
✅ **Funciones puras cuando sea posible**: Facilita testing y debugging
✅ **Docstrings completos**: Args, Returns, Raises en todas las funciones públicas
✅ **Session state en Streamlit**: Mantener estado entre reruns
✅ **Caching estratégico**: @st.cache_data para conversiones costosas

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

## 📝 Notas importantes

### ✅ Características técnicas
- **Preservación de formato**: El sistema usa manipulación ZIP para mantener 100% del formato original
- **Organización automática**: Los archivos se organizan por asignatura en subdirectorios
- **Eliminación de duplicados**: Durante la consolidación se eliminan automáticamente por PreguntaID
- **Archivos maestros requeridos**: La aplicación web requiere archivos maestros consolidados previamente
- **Tracking automático**: El seguimiento de uso se actualiza automáticamente al generar guías
- **Validación estricta**: Detiene el procesamiento si detecta errores críticos (valores inválidos, desajuste Word-Excel)

### 🎯 Limitaciones conocidas
- **LibreOffice requerido**: La vista previa en la app web necesita LibreOffice instalado
- **Formato Word**: Solo soporta .docx (no .doc antiguo)
- **1 pregunta por página**: El Word de entrada debe tener exactamente 1 pregunta por página
- **Nombres de archivo**: Los PreguntaIDs generados deben ser compatibles con el sistema de archivos
- **Timeout de conversión**: La conversión Word→PNG tiene timeout de 30 segundos

### 🔐 Seguridad y privacidad
- **Almacenamiento local por defecto**: Los datos se guardan localmente a menos que configures GCS
- **Sin telemetría**: El sistema no envía datos a servicios externos
- **Archivos temporales**: Se limpian automáticamente después del procesamiento

## 🆕 Estado actual del proyecto

### ✅ Funcionalidades completadas

#### Core del sistema
- ✅ **Procesamiento completo de documentos Word**: División por páginas con preservación total
- ✅ **Generación de IDs únicos**: Sistema robusto con patrón LLNNLLNN
- ✅ **Validación de datos**: Validación de Excel en 3 niveles (estructura, vacíos, inválidos)
- ✅ **Consolidación de archivos**: Modos completo e incremental
- ✅ **Almacenamiento flexible**: Soporte para local y Google Cloud Storage

#### Aplicación web
- ✅ **Interfaz completa**: Diseño moderno con Streamlit
- ✅ **Filtros dinámicos**: Subtema se actualiza según área seleccionada
- ✅ **Vista previa avanzada**: Conversión Word→PNG con LibreOffice
- ✅ **Reordenamiento visual**: Sistema drag-and-drop con preview de posiciones
- ✅ **Gráficos interactivos**: Pie charts con Plotly para todas las dimensiones
- ✅ **Generación de guías**: Fusión perfecta de documentos Word
- ✅ **Numeración automática**: Preguntas numeradas secuencialmente
- ✅ **Preservación de scroll**: JavaScript para mantener posición en la página

#### Ciencias combinadas
- ✅ **Soporte para Ciencias**: Combina F30M + Q30M + B30M en una sola vista
- ✅ **Filtrado por asignatura**: Dentro de Ciencias, filtrar por F30M, Q30M o B30M
- ✅ **Ordenamiento por asignatura**: Opción de ordenar por asignatura origen
- ✅ **Tracking cruzado**: Actualiza los 3 archivos maestros simultáneamente

#### Tracking de uso
- ✅ **Columnas dinámicas**: Sistema que crea columnas automáticamente para cada uso
- ✅ **Estadísticas completas**: Distribución de uso, preguntas sin usar, porcentajes
- ✅ **Gestión de guías**: Listar todas las guías con detalles y fechas
- ✅ **Eliminación selectiva**: Eliminar guías específicas con actualización de contadores
- ✅ **Soporte para Ciencias**: Manejo especial para las 3 asignaturas combinadas

### 🔄 Mejoras futuras potenciales

#### Funcionalidades propuestas
- 🔄 **Exportación a PDF**: Generar guías en formato PDF además de Word
- 🔄 **Filtro por estado de uso**: Ver solo preguntas libres o usadas
- 🔄 **Búsqueda por texto**: Buscar preguntas por contenido
- 🔄 **Plantillas personalizadas**: Soportar diferentes formatos de guías
- 🔄 **Estadísticas avanzadas**: Dashboard con análisis de uso por tiempo
- 🔄 **Historial de cambios**: Tracking de modificaciones en preguntas
- 🔄 **Importación masiva**: Procesar múltiples conjuntos a la vez
- 🔄 **Validación de contenido**: Verificar coherencia entre pregunta y metadatos
- 🔄 **Exportación de estadísticas**: Generar reportes en Excel/PDF
- 🔄 **API REST**: Exponer funcionalidades vía API para integración

#### Optimizaciones técnicas
- 🔄 **Cache de preview**: Guardar conversiones PNG para evitar reconversiones
- 🔄 **Procesamiento paralelo**: Usar multiprocessing para procesar múltiples archivos
- 🔄 **Base de datos**: Migrar de Excel a SQLite/PostgreSQL para mejor rendimiento
- 🔄 **Tests automatizados**: Suite completa de tests unitarios e integración
- 🔄 **CI/CD**: Pipeline automático de testing y deployment
- 🔄 **Docker**: Containerización para deployment simplificado
- 🔄 **Logs estructurados**: Sistema de logging más robusto con niveles y rotación

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es parte del sistema M30M de generación de contenido educativo dinámico.
