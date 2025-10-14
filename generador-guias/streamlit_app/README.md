# Generador de Guías M30M - Terminal Launcher

Esta aplicación ahora utiliza un sistema de selección de asignatura basado en terminal para una mejor experiencia de usuario.

## 🚀 Cómo Usar

### Opción 1: Script de Lanzamiento (Recomendado)
```bash
python launch_app.py
```

### Opción 2: Archivos de Inicio Rápido

**Windows:**
```bash
start_app.bat
```

**Linux/Mac:**
```bash
./start_app.sh
```

## 📋 Proceso de Inicio

1. **Ejecuta el launcher** - Se abrirá una interfaz en terminal
2. **Selecciona la asignatura** - Elige un número del 1 al 7
3. **La app se inicia automáticamente** - Streamlit se abre con la asignatura seleccionada

## 📚 Asignaturas Disponibles

1. M30M - Matemáticas
2. L30M - Lenguaje  
3. H30M - Historia
4. B30M - Biología
5. Q30M - Química
6. F30M - Física
7. Ciencias - Ciencias Combinadas (F30M + Q30M + B30M)

## ✨ Ventajas

- **Selección clara** - Menú numerado fácil de usar
- **Sin confusión** - No hay menús en la interfaz web
- **Persistente** - La asignatura se mantiene durante toda la sesión
- **Seguro** - Cada usuario solo ve su asignatura asignada
- **Fácil de usar** - Un solo comando para iniciar

## 🔧 Para Desarrolladores

El launcher:
1. Muestra el menú de selección en terminal
2. Establece la variable de entorno `STREAMLIT_SELECTED_SUBJECT`
3. Inicia Streamlit con la asignatura seleccionada
4. La app lee la asignatura de la variable de entorno

## 📝 Notas

- Si ejecutas `streamlit run app.py` directamente, verás un error pidiendo usar el launcher
- La asignatura seleccionada se mantiene durante toda la sesión
- Para cambiar de asignatura, cierra la app y vuelve a ejecutar el launcher
