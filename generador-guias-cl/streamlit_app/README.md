# Streamlit App - Generador CL

## Archivo Principal

- `app.py`: interfaz de generacion de guias CL.
- `launch_app.py`: lanzador alternativo (streamlit en puerto 8501).

## Como Ejecutar

Desde raiz del proyecto:

```bash
streamlit run streamlit_app/app.py
# o
python streamlit_app/launch_app.py
```

## Requisito De Datos

La app carga datos desde:

- `output/cl_master.xlsx`

Si ese archivo no existe o esta vacio, la app se detiene con error y no construye el master automaticamente.

## Flujo En La UI

1. Estadisticas y gestion
- Muestra metricas de cobertura y distribuciones.
- Permite listar guias creadas y eliminar registro de uso de una guia especifica.

2. Filtros
- Cascada top-down: tipo de texto -> subgenero -> titulo -> descripcion.
- Filtros adicionales: programa, numero de preguntas, habilidad, tarea lectora.

3. Seleccion y orden de textos
- Seleccion por cards.
- Paginacion configurable.
- Reordenamiento por posicion numerica.
- Configuracion de objetivo de preguntas (default: 25).

4. Eliminacion de preguntas
- Seleccion por pregunta dentro de cada texto.
- Muestra historial de uso por pregunta cuando existe.

5. Resumen
- Textos seleccionados.
- Preguntas finales.
- Diferencia contra el objetivo.
- Graficos por habilidad y tarea lectora.

6. Generacion
- Nombre de guia desde `output/nombres_guias.xlsx`.
- Validacion estricta: solo habilita descarga si preguntas finales == objetivo.
- Genera ZIP con:
- `guia.docx`
- `reporte.xlsx`
- `README.txt`

7. Tracking de uso
- Al descargar, actualiza `Numero de usos` y columnas dinamicas `Nombre guia (uso N)` / `Fecha descarga (uso N)` en `output/cl_master.xlsx`.

## Dependencias Funcionales

`app.py` usa modulos del proyecto raiz:

- `config.py`
- `cl_data_processor.py`
- `cl_master.py`
- `cl_word_builder.py`
