# Sistema de Automatización Beiplas

Sistema de automatización basado en Python para el procesamiento, análisis y validación de Órdenes de Trabajo (OT) a partir de documentos PDF.

## 🚀 Descripción

Esta aplicación permite a los usuarios subir lotes de archivos PDF correspondientes a Órdenes de Trabajo. El sistema extrae automáticamente la información relevante (Cliente, OT, Medidas, Calibres, etc.) y realiza validaciones matemáticas para asegurar que el peso de la bolsa y los kilos totales planificados coincidan con los parámetros técnicos de producción.

## 🛠️ Tecnologías Utilizadas

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Frontend**: [HTMX](https://htmx.org/) (Interactividad dinámica sin JS complejo)
- **Templating**: [Jinja2](https://palletsprojects.com/p/jinja/)
- **Estilos**: [Tailwind CSS](https://tailwindcss.com/) (vía CDN)
- **Procesamiento PDF**: [pdfplumber](https://github.com/jsvine/pdfplumber)
- **Servidor**: [Uvicorn](https://www.uvicorn.org/)

## 📂 Estructura del Proyecto

```text
Sistema Automatizacion/
├── main.py              # Punto de entrada de la aplicación
├── src/
│   ├── routes/          # Definición de endpoints (vistas y carga)
│   ├── services/
│   │   ├── pdf/         # Extracción de texto de PDF
│   │   ├── parsers/     # Análisis de texto y Regex
│   │   ├── validators/  # Lógica de validación y tolerancia
│   │   └── calculators/ # Fórmulas matemáticas
│   ├── templates/       # Plantillas HTML (Base, Index, Componentes)
│   └── utils/           # Utilidades de formateo y normalización
├── requirements.txt     # Dependencias del proyecto
└── AGENTS.md            # Instrucciones específicas para el desarrollo IA
```

## ⚙️ Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd "Sistema Automatizacion"
```

### 2. Crear y activar entorno virtual
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación
```bash
python main.py
```
O usando uvicorn directamente:
```bash
uvicorn main:app --reload
```

La aplicación estará disponible en `http://localhost:8000`.

## 📋 Funcionalidades Principales

- **Carga Masiva**: Arrastre y suelte múltiples archivos PDF simultáneamente.
- **Validación en Tiempo Real**: Cálculo automático de Peso Bolsa y Kilos Totales con porcentaje de tolerancia ajustable.
- **Interfaz Premium**: Diseño limpio, responsivo y con feedback visual instantáneo mediante alertas y tooltips.
- **Fallback Inteligente**: El sistema detecta automáticamente variaciones en el formato del PDF (ej: Ancho General vs Ancho Extrusión).

---
Desarrollado para **Beiplas S.A.S.**
