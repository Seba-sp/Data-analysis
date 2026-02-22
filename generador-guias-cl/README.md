# Generador CL

Aplicacion para construir guias de Comprension Lectora a partir de pares `docx + xlsx`, consolidar un master y generar una guia final (Word + Excel) desde Streamlit.

## Estado Actual Del Proyecto

- El flujo activo es CL-only.
- El punto de entrada CLI actual es `main.py` (menu interactivo, sin subcomandos).
- El master activo se guarda en `output/cl_master.xlsx`.
- El procesamiento validado copia insumos a `output/processed/` antes de consolidar.
- La app Streamlit activa esta en `streamlit_app/app.py`.

## Instalacion

```bash
pip install -r requirements.txt
```

Recomendado: Python 3.11+.

## Flujo De Uso

1. Copiar pares de archivos a `input/` con prefijo comun `Cxxx`:
- `C001-Preguntas+Texto.docx`
- `C001-Preguntas Datos.xlsx`

2. Ejecutar CLI interactivo:

```bash
python main.py
```

3. En el menu:
- `Procesar archivos` valida cada set y lo copia a `output/processed/`.
- `Consolidar master Excel` crea o actualiza `output/cl_master.xlsx`.

4. Ejecutar Streamlit:

```bash
streamlit run streamlit_app/app.py
o
python streamlit_app/launch_app.py
```

5. En la app:
- filtrar textos
- seleccionar y ordenar
- eliminar preguntas
- generar ZIP con Word + Excel
- registrar uso en master

## Estructura De Datos

### Entrada

- Carpeta: `input/`
- Regla: el sistema detecta pares por prefijo (ejemplo `C001`).

### Salida

- `output/processed/`: copia de sets validados.
- `output/cl_master.xlsx`: base consolidada usada por Streamlit.
- `output/nombres_guias.xlsx`: lista de nombres permitidos para guias.

## Columnas Esperadas En Excel CL

- `Titulo del texto`
- `Tipo de texto`
- `Subgenero`
- `Descripcion texto`
- `Programa `
- `N Preguntas`
- `Codigo Texto`
- `Numero de pregunta`
- `Clave`
- `Habilidad`
- `Tarea lectora`
- `Justificacion`
- `Codigo Spot`

El sistema renombra aliases de encabezados (por ejemplo versiones con acentos/encoding distinto) hacia estos nombres canonicos.

## Modulos Python (Todos Los .py Del Repo)

### Flujo activo CL

- `main.py`: CLI interactivo principal. Permite procesar sets (uno, todos, o lista `procesar.txt`) y consolidar master en modo incremental/full reset.
- `config.py`: rutas, columnas canonicas CL, aliases, filtros, defaults de app (objetivo de preguntas, prefijo de archivos, etc.) y creacion de carpetas.
- `cl_data_processor.py`: deteccion de pares `docx+xlsx`, validacion de Excel, normalizacion de encabezados, chequeo de columnas uniformes, filtros y procesamiento hacia `output/processed/`.
- `cl_master.py`: construccion del master CL (`full reset` o `incremental`), carga de master, estadisticas, tracking de uso por pregunta y borrado de historial de guias.
- `cl_word_builder.py`: parseo de DOCX por saltos de pagina, separacion texto/preguntas, armado de Word final con preguntas conservadas y creacion del reporte Excel en memoria.
- `streamlit_app/app.py`: interfaz Streamlit completa (estadisticas, filtros cascada, seleccion, orden, eliminacion de preguntas, generacion de ZIP, tracking de uso y eliminacion de guias).
- `streamlit_app/launch_app.py`: lanzador simple de Streamlit en puerto `8501`.

## Parseo De Word (Regla Central)

- Cada `docx` se divide por saltos de pagina.
- Las ultimas `N` paginas se asumen como preguntas, donde `N` es la cantidad de filas de preguntas en el Excel del texto.
- Todo lo anterior se considera cuerpo del texto.
- Al generar guia, se incluyen solo preguntas no eliminadas y se inserta salto de pagina entre textos cuando corresponde.

## Tracking De Uso

- El contador base por pregunta es `Numero de usos` en `output/cl_master.xlsx`.
- En cada descarga se incrementa el uso de cada pregunta incluida.
- Se agregan/actualizan columnas dinamicas por uso:
- `Nombre guia (uso N)`
- `Fecha descarga (uso N)`
- La app permite listar guias detectadas en estas columnas y eliminar su registro de uso.

## Notas Operativas

- Si `output/cl_master.xlsx` no existe, Streamlit no inicia flujo de trabajo (muestra error).
- La app exige que el total final de preguntas coincida con el objetivo (default: `25`) para habilitar descarga.
- El nombre de guia se selecciona desde `output/nombres_guias.xlsx`.
