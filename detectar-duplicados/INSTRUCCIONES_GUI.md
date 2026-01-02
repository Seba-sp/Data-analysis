# 🔍 Detector de Preguntas Duplicadas - Guía de Uso

## Para Usuarios Sin Conocimientos de Programación

Esta herramienta te permite detectar preguntas duplicadas entre documentos Word (.docx) de manera visual y fácil.

---

## 📋 Requisitos Previos

1. **Python instalado** en tu computadora
   - Si no lo tienes, descárgalo de: https://www.python.org/downloads/
   - Durante la instalación, marca la opción "Add Python to PATH"

2. **Bibliotecas necesarias**
   - Abre una terminal/consola y ejecuta:
     ```
     pip install python-docx
     ```

---

## 🚀 Cómo Usar la Aplicación

### Opción 1: Doble Clic (Windows)

1. Haz doble clic en el archivo: **`Abrir_Detector_Duplicados.bat`**
2. Se abrirá la ventana de la aplicación

### Opción 2: Desde la Terminal

1. Abre una terminal/consola
2. Navega hasta la carpeta `input`
3. Ejecuta:
   ```
   python detectar_duplicados_gui.py
   ```

---

## 📖 Uso de la Interfaz

### Paso 1: Seleccionar Archivo Principal
- Haz clic en **"Seleccionar"** junto a "Archivo principal"
- Busca y selecciona el archivo Word que quieres usar como referencia

### Paso 2: Elegir Modo de Comparación

**Opción A: Comparar con un solo archivo**
- Marca la opción "Un solo archivo"
- Selecciona el segundo archivo Word

**Opción B: Comparar con todos los archivos de una carpeta**
- Marca la opción "Todos los archivos en una carpeta"
- Selecciona la carpeta que contiene los archivos a comparar

### Paso 3: Configurar Opciones (Opcional)

- **Nombre del reporte**: Nombre para los archivos de reporte (por defecto: "duplicate_report")
- **Similitud**: Qué tan similar deben ser las preguntas para considerarse "posible duplicado" (por defecto: 0.04 = 4%)
- **Modo debug**: Actívalo si quieres ver información técnica detallada

### Paso 4: Ejecutar

- Haz clic en el botón **"🔍 Buscar Duplicados"**
- Espera mientras la aplicación procesa los archivos
- Los resultados aparecerán en el área de texto

---

## 📄 Resultados

La aplicación genera dos archivos en la misma carpeta donde está el archivo principal:

### 1. `duplicate_report.docx`
Reporte completo en Word con:
- Lista de duplicados exactos
- Lista de posibles coincidencias (para revisar manualmente)
- Texto completo de cada pregunta y sus alternativas
- Números de página aproximados

### 2. `duplicate_report.txt`
Resumen en texto plano con:
- Conteo total de duplicados
- Lista resumida de coincidencias

---

## 🎯 Tipos de Preguntas Detectadas

La herramienta detecta preguntas con:
- ✅ **4 alternativas** (A, B, C, D)
- ✅ **5 alternativas** (A, B, C, D, E)
- ✅ Formatos de una pregunta por página
- ✅ Preguntas en párrafos normales
- ✅ Preguntas en tablas

---

## 📊 Tipos de Coincidencias

### Duplicados Exactos
Preguntas idénticas con las mismas alternativas (ignorando acentos y mayúsculas)

### Posibles Coincidencias
Preguntas muy similares que deberías revisar manualmente:
- El texto de la pregunta es casi idéntico
- Las alternativas son exactamente iguales
- Puede haber pequeñas diferencias de redacción

---

## 💡 Consejos

1. **Usa el modo carpeta** cuando tengas muchos archivos que comparar
2. **Revisa las "posibles coincidencias"** manualmente, pueden ser variaciones válidas
3. **Activa el modo debug** si algo no funciona correctamente
4. **Asegúrate** de que tus archivos estén en formato .docx (no .doc)
5. **Redimensiona la ventana** si necesitas ver más información (puedes hacerla más grande o más pequeña)
6. **El área de resultados tiene scroll** - usa la barra de desplazamiento a la derecha para ver todos los resultados

---

## ❓ Solución de Problemas

### La aplicación no abre
- Verifica que Python esté instalado: abre una terminal y escribe `python --version`
- Asegúrate de haber instalado python-docx: `pip install python-docx`

### No detecta mis preguntas
- Asegúrate de que las alternativas empiecen con "A)", "B)", "C)", "D)" o "E)"
- Activa el modo debug para ver qué está detectando
- Las preguntas deben tener al menos 4 alternativas

### Error al abrir archivos
- Cierra los archivos Word antes de procesarlos
- Verifica que no sean archivos temporales (que empiecen con ~$)

---

## 📞 Soporte

Si tienes problemas, activa el **modo debug** y revisa los mensajes en el área de resultados para más información.

---

¡Listo! Ahora puedes detectar preguntas duplicadas fácilmente 🎉

