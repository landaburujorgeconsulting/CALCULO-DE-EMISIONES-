# Inventario de Emisiones GEI — Aplicación Web Flask

## Estructura del proyecto

```
huella_carbono/
├── app.py              ← Servidor Flask principal
├── requirements.txt    ← Dependencias Python
├── templates/
│   └── index.html      ← Página web principal (Jinja2)
└── static/
    ├── style.css       ← Estilos CSS
    └── app.js          ← Lógica JavaScript del formulario
```

## Instalación y puesta en marcha

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Correr el servidor de desarrollo
```bash
python app.py
```
→ Abrir en el navegador: http://localhost:5000

### 3. Producción (con un dominio www.)
Para que los clientes accedan vía dominio:

```bash
# Instalar gunicorn (servidor de producción)
pip install gunicorn

# Correr con gunicorn
gunicorn -w 4 -b 0.0.0.0:80 app:app
```

Luego configurar un servidor web (nginx o Apache) que apunte al puerto 80.
Con cualquier proveedor de hosting (DigitalOcean, Railway, Render, etc.)
podés poner un dominio personalizado como www.huellacarbono.com.ar

## Despliegue rápido en Railway (gratis)
1. Subir el proyecto a GitHub
2. Crear cuenta en https://railway.app
3. "Deploy from GitHub" → seleccionar el repositorio
4. En Settings → añadir dominio personalizado

## Flujo de la aplicación
- El usuario completa el formulario de 5 pasos
- Al hacer clic en "Generar informe PDF", el formulario envía los datos al servidor Flask vía POST /generar-pdf
- Flask procesa los datos, calcula las emisiones y genera un PDF con ReportLab (GRI 305)
- El PDF se descarga automáticamente en el navegador del cliente
