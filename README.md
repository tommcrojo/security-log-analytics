# 🛡️ Automated Security Log Analytics Pipeline

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.1.0-150458.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Pipeline ETL automatizado para transformar logs crudos de seguridad en inteligencia de negocio procesable.

## 💼 Contexto de Negocio y Problema

**El Cliente:** Una empresa de gestión inmobiliaria ("Cámara de Gestión") manejando datos sensibles de propiedades.

**La Infraestructura:** Una aplicación web Next.js protegida por un Edge Middleware personalizado que registra cada petición en una base de datos Supabase (PostgreSQL).

**El Problema:** El sistema generaba ~50,000 entradas de log por mes. El equipo de IT tenía **cero visibilidad** sobre estos datos. No podían responder preguntas básicas como:
- *"¿Estamos bajo ataque ahora mismo?"*
- *"¿El geo-blocking realmente funciona?"*
- *"¿Cuánto de nuestro tráfico son bots vs clientes reales?"*

**Mi Rol:** Fui contratado para diseñar e implementar un **Pipeline de Datos Automatizado** que extrajera estos datos crudos, los transformara en métricas significativas y entregara un reporte mensual de inteligencia de seguridad a los stakeholders.

---

## 🏗️ Arquitectura Técnica

Diseñé una arquitectura **ETL (Extract, Transform, Load)** serverless para desacoplar el analytics del servidor web de producción.

```
┌─────────────────┐
│  Supabase DB    │
│  (Raw Logs)     │
│  access_logs    │
└────────┬────────┘
         │ Extract (Python Client)
         ▼
┌─────────────────┐
│  Python Script  │
│  ETL Process    │
└────────┬────────┘
         │ Transform (Pandas)
         ▼
┌─────────────────┐
│ Data Processing │
│ - Clean         │
│ - Aggregate     │
│ - Categorize    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Key Metrics    │ ───> │  HTML Report     │
│  - Attack Stats │      │  (Jinja2 Render) │
│  - Geo Analysis │      └────────┬─────────┘
│  - Performance  │               │
└─────────────────┘               │ Dispatch
                                  ▼
                         ┌──────────────────┐
                         │  Resend API      │
                         │  Email Delivery  │
                         └──────────────────┘

┌─────────────────────────────────────────┐
│  GitHub Actions (Cron: Monthly)         │
│  Orchestrates entire pipeline           │
└─────────────────────────────────────────┘
```

### Tech Stack

| Componente | Tecnología |
|------------|------------|
| **Source** | Supabase (PostgreSQL) |
| **Processing** | Python 3.10 + Pandas |
| **Orchestration** | GitHub Actions (CI/CD Cron) |
| **Delivery** | Resend API (Email) |
| **Templating** | Jinja2 |

---

## 🚀 Características Clave y Detalles de Implementación

### 1. Extracción de Datos (Integración API)

En lugar de consultar continuamente la base de datos de producción, el script realiza una extracción por lotes de los datos del mes anterior usando el cliente Python de Supabase, asegurando un impacto mínimo en el rendimiento web.

```python
response = self.supabase.table("access_logs") \
    .select("*") \
    .gte("timestamp", start_date.isoformat()) \
    .lt("timestamp", end_date.isoformat()) \
    .execute()
```

### 2. Transformación de Datos (Pandas)

Los logs crudos son desordenados. El pipeline realiza varios pasos de limpieza:

- **Conversión de Tipos**: Convertir strings ISO 8601 a objetos Python Datetime
- **Categorización**: Lógica para clasificar tráfico en buckets `Legítimo`, `Bots` y `Malicioso` basándose en códigos de acción del middleware
- **Agregación**: Agrupar ataques por códigos de país ISO y calcular distribuciones de frecuencia para IPs sospechosas

### 3. Inteligencia de Negocio (El Reporte)

El output no es solo un CSV. Es un dashboard HTML renderizado que responde preguntas de negocio:

- **Postura de Seguridad**: % de ataques bloqueados vs. tráfico total
- **Análisis Geo-Espacial**: Top 5 países atacando la infraestructura
- **Rendimiento**: Seguimiento de latencia promedio para asegurar que la capa de seguridad no esté ralentizando la UX

---

## 🛠️ Configuración y Uso

### Prerrequisitos

- Python 3.9+
- Un proyecto Supabase con una tabla `access_logs`
- Una API Key de Resend.com

### Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/tommcrojo/middleware-analytics.git
cd middleware-analytics
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar Variables de Entorno (`.env`):

```bash
SUPABASE_URL="your-project-url"
SUPABASE_KEY="your-service-role-key"
RESEND_API_KEY="your-resend-key"
ADMIN_EMAIL="admin@company.com"
```

### Ejecutar el Pipeline

```bash
python src/main.py
```

### Demo con Datos Mock

Si no tienes credenciales de Supabase, puedes usar los datos de ejemplo:

```bash
python src/main.py --use-mock-data
```

---

## 📊 Estructura del Proyecto

```
middleware-analytics/
├── src/
│   └── main.py                 # Script ETL principal
├── data/
│   └── mock_logs.csv          # Datos de ejemplo para demos
├── examples/
│   └── sample_report.png      # Captura del reporte HTML
├── .github/
│   └── workflows/
│       └── monthly_report.yml # Automatización CI/CD
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🤖 Automatización con GitHub Actions

El pipeline se ejecuta automáticamente el día 1 de cada mes a las 9:00 AM UTC:

```yaml
on:
  schedule:
    - cron: '0 9 1 * *'
  workflow_dispatch:  # También permite ejecución manual
```

Las credenciales se gestionan de forma segura usando GitHub Secrets.

---

## 💡 Habilidades Demostradas

- **Ingeniería de Datos**: Diseño de un proceso ETL robusto desde cero
- **Ecosistema Python**: Uso avanzado de Pandas para manipulación de datos
- **Automatización Cloud**: Utilización de GitHub Actions para scheduling basado en cron
- **SQL y Bases de Datos**: Interacción con APIs basadas en PostgreSQL
- **Comunicación de Negocio**: Traducir logs técnicos crudos a insights de nivel ejecutivo

---

## 📈 Métricas Clave Generadas

El reporte incluye:

1. **Resumen Ejecutivo**
   - Total de peticiones procesadas
   - Amenazas bloqueadas
   - Score de seguridad (%)
   - Latencia promedio del middleware

2. **Análisis Geográfico**
   - Top 5 países origen de ataques
   - Distribución de tráfico legítimo vs malicioso

3. **Inteligencia de Amenazas**
   - IPs de alto riesgo (>5 intentos bloqueados)
   - Patrones de ataque recurrentes

4. **Calidad del Tráfico**
   - Ratio de bots vs usuarios reales
   - Efectividad del filtrado

---

## 🔒 Consideraciones de Seguridad

- Las credenciales nunca se commitean al repositorio (uso de `.env` y GitHub Secrets)
- El script usa `service_role_key` de Supabase con permisos de solo lectura
- Los datos sensibles (IPs reales) se pueden anonimizar antes del envío del reporte

---

## 🚀 Mejoras Futuras

- **Alertas en Tiempo Real**: Integración con Slack/PagerDuty para ataques en curso
- **Dashboard Interactivo**: Panel web con Streamlit o Metabase
- **Machine Learning**: Detección de anomalías usando modelos de clustering
- **Almacenamiento Histórico**: Data warehouse para análisis de tendencias a largo plazo

---

## 📄 Licencia

Este proyecto está licenciado bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

## 👤 Autor

**Tomás Campoy Rojo**
- GitHub: [@tommcrojo](https://github.com/tommcrojo)

---

## 🙏 Agradecimientos

Este proyecto fue desarrollado como parte de una consultoría real para optimizar la visibilidad de seguridad de infraestructura web empresarial.
