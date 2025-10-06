# 🧠 Generador de Guías Escolares – M30M

Este proyecto permite automatizar la creación de guías escolares filtradas por tema, habilidad, dificultad, etc., a partir de un conjunto de preguntas clasificadas en Word y Excel.  
El flujo convierte archivos Word con múltiples preguntas en preguntas individuales, las indexa en Excel, y permite al usuario generar una guía final en PDF o Word con una app web local.

---

## 📁 Estructura de entrada (por set)

Cada set de preguntas incluye:

- Un archivo Word (`.docx`) con ~25 preguntas numeradas con alternativas (formato PSU).
- Un archivo Excel (`.xlsx`) con etiquetas para cada pregunta, donde cada fila corresponde a una pregunta del Word, con las siguientes columnas:

| Columna                | Descripción                                      |
|------------------------|--------------------------------------------------|
| `Eje temático`         | Ej: Ondas, Geometría, Lectura literal            |
| `Área temática`        | Ej: Física, Matemática, Lenguaje                 |
| `Conocimiento/Subtema` | Subtema específico (opcionalmente jerárquico)    |
| `Habilidad`            | Habilidad cognitiva evaluada                     |
| `Dificultad`           | Baja, Media o Alta                               |
| `Tipo`                 | Ej: Ensayo, Diagnóstico, Simulacro               |
| `Clave`                | Letra de la respuesta correcta (A–D)             |
| `Fecha creación`       | Fecha en que fue creada o ingresada la pregunta  |

---

## 📌 Objetivo del sistema

1. Dividir cada archivo Word en preguntas individuales (1 archivo Word por pregunta).
2. Asignar un identificador único (`PreguntaID`) a cada pregunta basado en sus etiquetas.
3. Actualizar el Excel con la ruta y nombre del archivo generado.
4. Consolidar todos los Excel por eje en un Excel maestro por asignatura.
5. Usar una app en Streamlit para generar guías personalizadas filtrando por etiquetas.

---

## 🔑 Generación del PreguntaID

Cada pregunta recibe un `PreguntaID` único con el siguiente formato:

{EJE}-{AREA}-{SUBTEMA}-{HABILIDAD}-{DIFICULTAD}-{CLAVE}-{RANDOM}


**Ejemplo:**

OND-FIS-LONG-ANA-MED-C-A1B2


- Abreviaciones se generan a partir de las 3 primeras letras sin tildes
- El sufijo es un código alfanumérico aleatorio de 4 caracteres (mayúsculas + dígitos)

---

## 🗂️ Organización de archivos de salida

### Archivos Word individuales:
- Se guardan como: `OND-FIS-LONG-ANA-MED-C-A1B2.docx`
- Todos los archivos Word se almacenan en una carpeta por eje:

/preguntas_divididas/FISICA/

OND-FIS-LONG-ANA-MED-C-A1B2.docx

...

/preguntas_divididas/MATEMATICA/

ALG-MAT-RAIZ-APL-MED-D-4G7H.docx


### Excel por set:
- Se actualiza el archivo Excel original agregando columnas:
  - `PreguntaID`
  - `Archivo generado`
  - `Ruta absoluta`
- Se guarda como `base_fisica_agosto_actualizado.xlsx` u otro nombre único

---

## 📘 Excel maestro

Cada eje (Física, Matemática, etc.) tendrá su propio Excel maestro consolidado:

- `excel_maestro_fisica.xlsx`
- `excel_maestro_matematica.xlsx`
- `excel_maestro_lenguaje.xlsx`

Estos archivos sirven como fuente para el generador de guías.

---

## 🧩 Funciones clave del sistema

### 1. `procesar_set(docx_path, excel_path, output_dir, eje)`

- Divide el Word en 1 archivo por pregunta
- Genera un `PreguntaID` para cada fila del Excel
- Guarda los archivos Word individuales en: `/preguntas_divididas/{eje}/`
- Actualiza el Excel agregando:
  - `PreguntaID`
  - `Nombre archivo`
  - `Ruta`
- Guarda Excel actualizado en `/excels_actualizados/{eje}/`

---

### 2. `consolidar_excel_maestro(carpeta_excels, eje, output_file)`

- Lee todos los Excel actualizados para un eje
- Concatena las filas en un solo DataFrame
- Elimina duplicados por `PreguntaID` si existen
- Guarda como: `excel_maestro_{eje}.xlsx`

---

### 3. `streamlit_gui.py` – Generador de Guías

App en Streamlit que permite:

1. Cargar el Excel maestro correspondiente al eje
2. Filtrar preguntas por:
   - Área temática
   - Habilidad
   - Subtema
   - Dificultad
   - Tipo
3. Ver una **previsualización** del contenido de cada pregunta (Word renderizado)
4. Seleccionar/deseleccionar preguntas sugeridas por el sistema
5. Buscar y agregar preguntas manualmente desde la base
6. Generar un documento final con las preguntas seleccionadas:
   - PDF o Word con formato para imprimir o subir a plataforma

---

## 🧪 Tecnologías utilizadas

- Python 3.10+
- Librerías:
  - `pandas`
  - `python-docx`
  - `unidecode`
  - `openpyxl`
  - `streamlit`
  - `reportlab` (si se desea generar PDF)

---

## 📂 Estructura esperada del proyecto

/input/

ensayo_fisica_agosto.docx

etiquetas_fisica_agosto.xlsx

/output/
/preguntas_divididas/
/FISICA/
- OND-FIS-LONG-ANA-MED-C-A1B2.docx

/excels_actualizados/
- base_fisica_agosto_actualizado.xlsx

/exceles_maestros/
- excel_maestro_fisica.xlsx

---

## 🚀 Próximos pasos sugeridos

- [ ] Implementar `procesar_set()` para un set completo
- [ ] Validar el formato del Word para que la separación funcione (numeración)
- [ ] Confirmar nomenclatura final de IDs y carpetas
- [ ] Construir la app `streamlit_gui.py` conectada al Excel maestro
- [ ] Validar exportación a Word/PDF

---

## 🧠 Autor / contexto

Este proyecto es parte del sistema M30M de generación de contenido educativo dinámico para ensayos, diagnósticos y guías.

