# Manga Tracker - Diseño del Sistema

**Fecha:** 2026-02-01
**Versión:** 1.0
**Estado:** Aprobado

## Contexto

MangaTaro.org cerrará en 15 días. Este proyecto migra el seguimiento de manga a un sistema propio basado en tracking directo desde grupos de scanlation, con extracción urgente de datos de MangaTaro antes del cierre.

## Objetivos

1. **Extracción urgente**: Salvar bookmarks, portadas y metadata de MangaTaro
2. **Tracking descentralizado**: Seguir mangas directamente desde grupos de scanlation
3. **Extensibilidad**: Agregar nuevos scanlators/agregadores fácilmente
4. **Automatización**: Detección automática de nuevos capítulos con notificaciones
5. **Frontend local**: Interfaz web para gestionar biblioteca y capítulos

## Arquitectura General

### Componentes Principales

#### 1. Extractor Inicial (Python + Playwright)
**Propósito**: Scraping urgente de MangaTaro antes del cierre

- Procesa `mangataro-export.json`
- Scraping de cada URL con Playwright para extraer títulos alternativos y grupos
- Descarga de portadas a `./data/img/`
- Generación de fichas markdown
- Inserción de datos base en MariaDB

#### 2. Sistema de Scanlators (Python + Arquitectura de Plugins)
**Propósito**: Tracking extensible desde múltiples fuentes

- Clase base abstracta `BaseScanlator` con interfaz común
- Implementaciones específicas por scanlator/agregador
- Auto-discovery dinámico desde carpeta `scanlators/`
- Métodos estándar: `buscar_manga()`, `obtener_capitulos()`, `parsear_numero_capitulo()`
- URLs de manga por scanlator en MariaDB

#### 3. API Backend (FastAPI)
**Propósito**: Interfaz programática para gestión y tracking

- CRUD completo de mangas, scanlators, capítulos
- Endpoint `/check-updates` para tracking
- Histórico de capítulos detectados
- Estado de último check por manga

#### 4. Frontend (Astro) + Orquestación (n8n)
**Propósito**: Interfaz visual y automatización

- Astro: Biblioteca de mangas, últimos capítulos, admin
- n8n: Ejecuta `/check-updates` periódicamente
- n8n: Envía notificaciones de nuevos capítulos

## Modelo de Datos (MariaDB)

### Tabla: mangas
```sql
CREATE TABLE mangas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mangataro_id VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    alternative_titles TEXT,
    cover_filename VARCHAR(255),
    mangataro_url VARCHAR(500),
    date_added DATETIME,
    last_checked DATETIME,
    status ENUM('reading', 'completed', 'on_hold', 'plan_to_read') DEFAULT 'reading',
    INDEX idx_title (title),
    INDEX idx_status (status)
);
```

**Campos**:
- `mangataro_id`: ID original del export (histórico)
- `title`: Título principal
- `alternative_titles`: Todos los títulos separados por " / "
- `cover_filename`: Nombre del archivo en ./data/img/
- `mangataro_url`: URL original (referencia histórica)
- `last_checked`: Último check de updates
- `status`: Estado de lectura

### Tabla: scanlators
```sql
CREATE TABLE scanlators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    base_url VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    INDEX idx_active (active)
);
```

**Campos**:
- `name`: Nombre del scanlator (ej: "Uscanlations")
- `class_name`: Nombre de la clase Python (ej: "UscanlationsScanlator")
- `base_url`: Dominio principal
- `active`: Si está operativo (para manejar sitios cerrados)

### Tabla: manga_scanlator
```sql
CREATE TABLE manga_scanlator (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT NOT NULL,
    scanlator_id INT NOT NULL,
    scanlator_manga_url VARCHAR(500) NOT NULL,
    manually_verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE CASCADE,
    UNIQUE KEY unique_manga_scanlator (manga_id, scanlator_id),
    INDEX idx_manga (manga_id),
    INDEX idx_scanlator (scanlator_id)
);
```

**Propósito**: Relación N:N entre mangas y scanlators (un manga puede estar en múltiples fuentes)

**Campos**:
- `scanlator_manga_url`: URL del manga en ese scanlator específico
- `manually_verified`: Si confirmaste que la URL es correcta
- `notes`: Apuntes sobre esa combinación

### Tabla: chapters
```sql
CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT NOT NULL,
    chapter_number VARCHAR(20) NOT NULL,
    chapter_title VARCHAR(255),
    chapter_url VARCHAR(500) NOT NULL,
    published_date DATETIME,
    detected_date DATETIME NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    UNIQUE KEY unique_chapter (manga_scanlator_id, chapter_number),
    INDEX idx_detected (detected_date DESC),
    INDEX idx_read (read)
);
```

**Campos**:
- `chapter_number`: Varchar para soportar formatos especiales (42.5, "Extra", etc.)
- `published_date`: Cuándo se publicó (si el sitio lo provee)
- `detected_date`: Cuándo nuestro sistema lo detectó
- `read`: Si lo leíste

### Tabla: scraping_errors (opcional pero recomendada)
```sql
CREATE TABLE scraping_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT,
    error_type VARCHAR(50),
    error_message TEXT,
    timestamp DATETIME NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_resolved (resolved)
);
```

**Propósito**: Registrar errores de scraping para debugging

## Sistema de Scanlators (Arquitectura de Plugins)

### Clase Base Abstracta

**Archivo**: `scanlators/base.py`

```python
from abc import ABC, abstractmethod
from playwright.async_api import Page

class BaseScanlator(ABC):
    """Clase base para implementaciones de scanlators"""

    def __init__(self, playwright_page: Page):
        self.page = playwright_page
        self.name = ""
        self.base_url = ""

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Busca manga por título en el sitio del scanlator.

        Returns:
            Lista de candidatos: [
                {"titulo": "...", "url": "...", "portada": "..."},
                ...
            ]
        """
        pass

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extrae capítulos de la página del manga.

        Returns:
            Lista de capítulos: [
                {
                    "numero": "42.5",
                    "titulo": "...",
                    "url": "...",
                    "fecha": datetime
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Normaliza números de capítulo según formato del scanlator.

        Ejemplos:
            "Chapter 42" -> "42"
            "Ch. 42.5" -> "42.5"
            "Episode 10" -> "10"
        """
        pass
```

### Implementaciones Específicas

**Ejemplo**: `scanlators/uscanlations.py`

```python
from .base import BaseScanlator
from datetime import datetime

class UscanlationsScanlator(BaseScanlator):
    def __init__(self, playwright_page):
        super().__init__(playwright_page)
        self.name = "Uscanlations"
        self.base_url = "https://uscanlations.com"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        # Implementación específica con selectores de Uscanlations
        pass

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        # Implementación específica
        pass

    def parsear_numero_capitulo(self, texto: str) -> str:
        # Regex específico del formato de Uscanlations
        pass
```

### Sistema de Auto-Discovery

**Archivo**: `scanlators/__init__.py`

```python
import importlib
import inspect
from pathlib import Path
from .base import BaseScanlator

def discover_scanlators() -> dict[str, type]:
    """
    Escanea la carpeta scanlators/ y registra todas las clases
    que heredan de BaseScanlator.

    Returns:
        Dict {class_name: ScanlatorClass}
    """
    scanlators = {}
    scanlator_dir = Path(__file__).parent

    for file in scanlator_dir.glob("*.py"):
        if file.stem in ["__init__", "base", "template"]:
            continue

        module = importlib.import_module(f"scanlators.{file.stem}")

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseScanlator) and obj != BaseScanlator:
                scanlators[name] = obj

    return scanlators
```

### Agregadores como Scanlators

Agregadores (ComicK, MangaDex, etc.) se tratan como un `Scanlator` más:

- **Ventajas**: Scraping más fácil (estructura consistente), múltiples mangas en un sitio
- **Desventajas**: Si cierran, pierdes esa fuente
- **Estrategia híbrida recomendada**: Mismo manga en agregador + scanlators directos

## Flujo de Trabajo

### FASE 1: Extracción Inicial (Urgente - Antes del Cierre)

**Script**: `scripts/extract_mangataro.py`

```
1. Leer mangataro-export.json
2. Por cada bookmark:
   a. Descargar portada → ./data/img/{filename}
   b. Scraping de la página con Playwright:
      - Extraer títulos alternativos
      - Extraer grupos de scanlation detectados
   c. Insertar en tabla mangas
   d. Insertar grupos en tabla scanlators (si no existen)
   e. Generar docs/fichas/{manga-slug}.md
3. Generar scanlators.md con lista consolidada
```

**Formato de ficha markdown**:
```markdown
# {titulo}
## {datos_titulos}
![Portada](../data/img/{imagen_portada})
{datos_grupo}
```

**Paso manual posterior**:
- Revisar `scanlators.md`
- Para cada manga, buscar en sitios de scanlators
- Insertar en tabla `manga_scanlator` las URLs correctas
- Marcar `manually_verified = true`

### FASE 2: Tracking Continuo

**Script**: `scripts/check_updates.py` (llamado por API o n8n)

```
1. Consultar todos los manga_scanlator activos
2. Por cada uno:
   a. Cargar la clase del scanlator (auto-discovery)
   b. Instanciar con Playwright page
   c. Ejecutar obtener_capitulos(url)
   d. Comparar con último capítulo en DB
   e. Si hay nuevos:
      - Insertar en tabla chapters
      - Agregar a lista de retorno
   f. Actualizar last_checked en mangas
3. Retornar lista de nuevos capítulos detectados
```

**n8n Workflow**:
```
Trigger: Schedule (cada 6-12 horas configurables)
  ↓
Action: HTTP Request POST /api/check-updates
  ↓
Condition: ¿Hay nuevos capítulos?
  ↓ (sí)
Action: Send Notification
  - Email / Discord / Telegram
  - Mensaje: "X nuevos capítulos detectados"
  - Lista de mangas actualizados
```

## API FastAPI - Endpoints Completos

### Estructura de archivos

```
api/
├── main.py          # FastAPI app, startup
├── views.py         # Endpoints, validaciones
├── crud.py          # Lógica de negocio
├── schemas.py       # Pydantic schemas
├── models.py        # SQLAlchemy models
├── database.py      # DB connection
├── dependencies.py  # Dependency injection
└── utils.py         # Helpers
```

### Endpoints

#### Mangas
- `GET /api/mangas` - Lista todos (filtros: status, scanlator, búsqueda)
- `GET /api/mangas/{id}` - Detalle con capítulos
- `POST /api/mangas` - Crear manga manualmente
  - Body: `{title, alternative_titles, cover_url, scanlator_id, manga_url}`
- `PUT /api/mangas/{id}` - Actualizar (status, notas)
- `DELETE /api/mangas/{id}` - Eliminar
- `PUT /api/mangas/{manga_id}/read-until` - **Binge reading**
  - Body: `{chapter_number, scanlator_id}`
  - Marca ese capítulo y todos los anteriores como leídos

#### Scanlators
- `GET /api/scanlators` - Lista todos
- `GET /api/scanlators/{id}/mangas` - Mangas de un scanlator
- `POST /api/scanlators` - Registrar nuevo
  - Body: `{name, class_name, base_url}`
- `PUT /api/scanlators/{id}` - Actualizar (marcar inactivo)

#### Fuentes Alternativas
- `POST /api/mangas/{id}/sources` - Añadir fuente alternativa
  - Body: `{scanlator_id, url}`
- `DELETE /api/manga-scanlator/{id}` - Eliminar fuente

#### Capítulos
- `GET /api/chapters/recent` - Últimos capítulos (homepage)
- `GET /api/chapters/unread` - Capítulos no leídos
- `PUT /api/chapters/{id}/read` - Marcar como leído

#### Tracking
- `POST /api/check-updates` - Check manual o desde n8n
- `POST /api/check-updates/{manga_id}` - Check de un manga específico
- `GET /api/tracking/status` - Estado del último tracking

### Separación de Responsabilidades

**views.py**:
```python
@router.put("/mangas/{manga_id}/read-until")
async def mark_read_until(
    manga_id: int,
    payload: ReadUntilSchema,
    db: Session = Depends(get_db)
):
    # Validar entrada con schema
    # Llamar a CRUD
    result = crud.mark_read_until(db, manga_id, payload.chapter_number, payload.scanlator_id)
    # Formatear respuesta
    return {"chapters_marked": result}
```

**crud.py**:
```python
def mark_read_until(
    db: Session,
    manga_id: int,
    chapter_number: str,
    scanlator_id: int
) -> int:
    # Query a DB
    # Lógica de negocio
    # Retornar resultado
    pass
```

## Frontend (Astro)

### Páginas

#### 1. Homepage (`src/pages/index.astro`)
- Grid de portadas de mangas (estilo biblioteca)
- Filtros: status, scanlator, búsqueda
- Badge en portadas: número de capítulos no leídos
- Ordenar: Últimos añadidos, Alfabético, Última actualización

#### 2. Detalle de Manga (`src/pages/manga/[id].astro`)
- Portada grande + títulos alternativos
- Lista de fuentes (scanlators disponibles)
- Tabla de capítulos por scanlator:
  - Columnas: Número, Título, Fecha publicación, Fecha detectado
  - Botón "Leer" → abre URL + marca como leído
  - Botón "Marcar hasta aquí" → binge reading
- Dropdown para cambiar status

#### 3. Últimos Capítulos (`src/pages/recent.astro`)
- Feed de capítulos recientes
- Agrupados por fecha (Hoy, Ayer, Esta semana)
- Click → marca como leído y abre URL

#### 4. Scanlators (`src/pages/scanlators.astro`)
- Lista de todos los scanlators
- Info: logo/nombre, cantidad de mangas, último check, estado
- Click → filtro de mangas de ese scanlator

#### 5. Admin (`src/pages/admin.astro`)
- Formulario: añadir manga manualmente
- Formulario: añadir scanlator
- Botón: trigger manual de check-updates
- Tabla: logs de errores de scraping

### Componentes Reutilizables

- `MangaCard.astro` - Tarjeta de portada con badge
- `ChapterList.astro` - Lista de capítulos con acciones
- `ScanlatorBadge.astro` - Badge con nombre/logo
- `StatusDropdown.astro` - Selector de status
- `FilterBar.astro` - Barra de filtros y búsqueda

## Error Handling y Robustez

### Estrategias por Tipo de Error

#### 1. Timeouts y Sitios Caídos
- Timeout configurable por scanlator (algunos lentos)
- Retry con backoff exponencial: 3 intentos (5s, 15s, 45s)
- Si falla: log error, continuar con siguiente manga
- No crashear el check completo

#### 2. Cambios en Estructura HTML
- Try/except en cada selector CSS/XPath
- Si falla extracción: registrar en `scraping_errors`
  - Campos: manga_scanlator_id, error_type, error_message, timestamp
- Notificación especial: "Scanlator X cambió estructura, revisar"
- Permite debugging sin perder track

#### 3. Anti-bot / Rate Limiting
- Delay aleatorio entre requests (2-5 segundos)
- User-agent rotativo
- Respetar robots.txt
- Si detecta captcha → marcar scanlator como `requires_manual_check`

#### 4. Capítulos Duplicados o Mal Parseados
- Normalización de números antes de comparar
- UNIQUE constraint en DB: `(manga_scanlator_id, chapter_number)`
- Log de capítulos no parseables

#### 5. Imágenes de Portada
- Validar descarga (tamaño > 0, formato válido)
- Fallback a placeholder si falla
- Re-intentar después si falló

### Logging Estructurado

- Librería: `loguru` o `structlog`
- Niveles:
  - INFO: checks normales, operaciones exitosas
  - WARNING: fallos recuperables, retries
  - ERROR: requiere atención manual
- Logs rotativos diarios
- Formato: timestamp, nivel, scanlator, manga, mensaje

## Estructura del Proyecto

```
mangataro/
├── data/
│   ├── mangataro-export.json      # Export original (histórico)
│   └── img/                        # Portadas descargadas
│
├── docs/
│   ├── plans/                      # Documentación de diseño
│   │   ├── 2026-02-01-manga-tracker-design.md
│   │   └── 2026-02-01-manga-tracker-implementation.md
│   └── fichas/                     # Markdown generados por manga
│       ├── girls-x-vampire.md
│       └── ...
│
├── scanlators/
│   ├── __init__.py                # Auto-discovery
│   ├── base.py                    # BaseScanlator
│   ├── uscanlations.py            # Implementación
│   ├── asura_scans.py             # Implementación
│   ├── template.py                # Template para nuevos
│   └── ...
│
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── views.py                   # Endpoints
│   ├── crud.py                    # Lógica de negocio
│   ├── schemas.py                 # Pydantic schemas
│   ├── models.py                  # SQLAlchemy models
│   ├── database.py                # DB connection
│   ├── dependencies.py            # Dependency injection
│   └── utils.py                   # Helpers
│
├── scripts/
│   ├── extract_mangataro.py       # Script inicial (Fase 1)
│   ├── check_updates.py           # Script de tracking
│   ├── add_manga.py               # CLI añadir manga
│   └── add_scanlator.py           # CLI añadir scanlator
│
├── frontend/                       # Proyecto Astro
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.astro
│   │   │   ├── manga/[id].astro
│   │   │   ├── recent.astro
│   │   │   ├── scanlators.astro
│   │   │   └── admin.astro
│   │   ├── components/
│   │   │   ├── MangaCard.astro
│   │   │   ├── ChapterList.astro
│   │   │   ├── ScanlatorBadge.astro
│   │   │   ├── StatusDropdown.astro
│   │   │   └── FilterBar.astro
│   │   └── layouts/
│   │       └── Layout.astro
│   ├── package.json
│   └── astro.config.mjs
│
├── n8n/
│   └── workflows/
│       ├── check-updates.json     # Workflow de tracking
│       └── README.md              # Instrucciones
│
├── requirements.txt               # Python dependencies
├── .env.example                   # Template variables
├── README.md                      # Documentación principal
├── CLAUDE.md                      # Memoria del proyecto
└── .gitignore
```

## Plan de Implementación (15 Días)

### FASE 1: EXTRACCIÓN URGENTE (Días 1-3) - PRIORITARIO

**Objetivo**: Salvar datos de MangaTaro antes del cierre

**Tareas**:
1. Setup inicial:
   - Crear base de datos MariaDB con schema
   - Instalar dependencies: `playwright`, `beautifulsoup4`, `sqlalchemy`, `pymysql`
   - `playwright install chromium`

2. Implementar extractor:
   - Crear modelos SQLAlchemy (mangas, scanlators, manga_scanlator)
   - Script `extract_mangataro.py`:
     - Procesar JSON
     - Scraping con Playwright de cada URL
     - Descargar portadas
     - Insertar en DB
     - Generar markdowns

3. Completar manualmente:
   - Revisar lista de scanlators generada
   - Buscar cada manga en sitios de scanlators
   - Insertar URLs en `manga_scanlator` (SQL o script helper)
   - Marcar `manually_verified = true`

### FASE 2: SISTEMA DE TRACKING (Días 4-7)

**Objetivo**: Implementar tracking de capítulos

**Tareas**:
1. Arquitectura de scanlators:
   - Clase `BaseScanlator` abstracta
   - Implementar 2-3 scanlators iniciales (más comunes)
   - Sistema de auto-discovery

2. Script de tracking:
   - `check_updates.py` usando clases de scanlators
   - Detectar nuevos capítulos
   - Insertar en tabla `chapters`
   - Actualizar `last_checked`

3. Pruebas manuales:
   - Ejecutar tracking, verificar detección
   - Refinar selectores si necesario
   - Ajustar parsers de números de capítulo

### FASE 3: API (Días 8-10)

**Objetivo**: Backend funcional

**Tareas**:
1. FastAPI básica:
   - Setup proyecto, estructura de archivos
   - Models, schemas, database connection
   - Implementar endpoints de lectura (GET)
   - Endpoint `/check-updates`

2. Endpoints de escritura:
   - POST/PUT/DELETE para mangas
   - POST para scanlators
   - Endpoint marcar leído
   - Endpoint binge reading (`/read-until`)

3. Testing:
   - Probar todos los endpoints
   - Validar schemas

### FASE 4: FRONTEND (Días 11-13)

**Objetivo**: Interfaz web funcional

**Tareas**:
1. Setup Astro:
   - Crear proyecto Astro
   - Configurar layout base
   - Integración con API (fetch)

2. Páginas principales:
   - Homepage con grid de mangas
   - Detalle de manga con capítulos
   - Recent chapters feed

3. Componentes:
   - MangaCard, ChapterList, ScanlatorBadge
   - FilterBar, StatusDropdown

4. Funcionalidades:
   - Marcar como leído
   - Binge reading
   - Cambiar status

### FASE 5: AUTOMATIZACIÓN (Día 14)

**Objetivo**: Sistema automático end-to-end

**Tareas**:
1. n8n workflow:
   - Crear workflow que llame `/check-updates`
   - Configurar schedule (cada 6-12 horas)
   - Configurar notificaciones (email/Discord/Telegram)
   - Probar trigger manual

2. Testing end-to-end:
   - Ejecutar workflow completo
   - Verificar detección de capítulos
   - Verificar notificaciones
   - Ajustar tiempos si necesario

### FASE 6: DOCUMENTACIÓN Y PULIDO (Día 15)

**Objetivo**: Proyecto documentado y usable

**Tareas**:
1. Documentación:
   - README.md completo
   - CLAUDE.md con decisiones de arquitectura
   - Comentarios en código crítico

2. Scripts de utilidad:
   - `add_manga.py` CLI
   - `add_scanlator.py` CLI
   - Script de backup de DB

3. Pulido:
   - Manejo de errores mejorado
   - Logging apropiado
   - .env.example con todas las variables

## Funcionalidades Futuras

### Añadir Mangas Manualmente

**API Endpoint**: `POST /api/mangas`
```json
{
  "title": "Nuevo Manga",
  "alternative_titles": "Alt Title / Other Title",
  "cover_url": "https://...",
  "scanlator_id": 3,
  "manga_url": "https://scanlator.com/manga/nuevo-manga"
}
```

**Script CLI**: `scripts/add_manga.py`
```bash
python add_manga.py --title "Nuevo Manga" --scanlator "Uscanlations" --url "https://..."
```
- Modo interactivo: pregunta datos faltantes
- Descarga portada automáticamente
- Crea registro en DB
- Genera markdown

### Añadir Nuevos Scanlators

**Proceso**:
1. Crear clase Python (`scanlators/nuevo_scanlator.py`):
   - Copiar de `template.py`
   - Implementar métodos abstractos
   - Probar manualmente primero

2. Registrar en DB:
   - `POST /api/scanlators`
   - O script: `python add_scanlator.py --name "Nuevo" --class "NuevoScanlator" --url "https://..."`

### Agregadores como Scanlators

ComicK, MangaDex, etc. se tratan como scanlators regulares:

- **Ventajas**:
  - Scraping más fácil (estructura consistente)
  - Múltiples mangas centralizados
  - Suelen tener APIs o estructuras limpias

- **Desventajas**:
  - Riesgo de cierre (como MangaTaro)
  - Dependencia de terceros

- **Estrategia recomendada**:
  - Agregar mismo manga en agregador + scanlators directos
  - Redundancia de fuentes
  - Priorizar agregadores para descubrimiento, scanlators para estabilidad

## Dependencias Técnicas

### Python (requirements.txt)
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pymysql==1.1.0
pydantic==2.5.0
playwright==1.41.0
beautifulsoup4==4.12.3
requests==2.31.0
loguru==0.7.2
python-dotenv==1.0.0
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "astro": "^4.0.0",
    "@astrojs/tailwind": "^5.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

### MariaDB
- Versión: 10.6 o superior
- Charset: utf8mb4 (para títulos en múltiples idiomas)

### n8n
- Self-hosted o cloud
- Nodes necesarios: HTTP Request, Schedule Trigger, Notification nodes

## Variables de Entorno (.env.example)

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=your_password_here

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Scraping
PLAYWRIGHT_TIMEOUT=30000
SCRAPING_DELAY_MIN=2
SCRAPING_DELAY_MAX=5
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# n8n (si se usa)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/check-updates
N8N_API_KEY=your_n8n_api_key

# Notifications
NOTIFICATION_TYPE=discord  # discord, telegram, email
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=your_email@gmail.com
```

## Consideraciones de Seguridad

1. **Respeto a robots.txt**: Verificar antes de scrapear
2. **Rate limiting**: No sobrecargar sitios de scanlators
3. **User-agent honesto**: Identificar el bot apropiadamente
4. **Manejo de credenciales**: Variables de entorno, nunca en código
5. **Validación de entrada**: Sanitizar URLs y datos de usuario
6. **SQL injection**: Usar ORM (SQLAlchemy) siempre
7. **CORS**: Configurar apropiadamente en FastAPI

## Métricas de Éxito

- [ ] Todos los bookmarks de MangaTaro extraídos antes del cierre
- [ ] Al menos 3 scanlators implementados y funcionales
- [ ] Sistema de tracking detecta nuevos capítulos correctamente
- [ ] Frontend permite navegar y gestionar biblioteca
- [ ] n8n envía notificaciones cuando hay actualizaciones
- [ ] Sistema robusto ante fallos de sitios individuales
- [ ] Documentación completa para uso y mantenimiento

## Decisiones de Arquitectura

### ¿Por qué Playwright en lugar de requests?
- Sitios modernos usan JavaScript para cargar contenido
- Playwright ve el DOM completo como un navegador real
- Más robusto para sitios dinámicos
- Trade-off: más lento, más recursos

### ¿Por qué MariaDB en lugar de SQLite?
- Usuario ya tiene MariaDB disponible
- Mejor para datos estructurados complejos
- Soporta queries concurrentes (API + n8n)
- Escalable si crece el proyecto

### ¿Por qué FastAPI?
- Performance excelente
- Validación automática con Pydantic
- Documentación auto-generada (Swagger)
- Async nativo para I/O

### ¿Por qué Astro?
- Genera HTML estático, muy rápido
- Hidratación parcial (islands architecture)
- Perfecto para sitios con mucho contenido estático
- Fácil integración con APIs

### ¿Por qué arquitectura de plugins para scanlators?
- Cada sitio tiene estructura diferente
- Permite agregar nuevos sin modificar core
- Aísla fallos (un scanlator roto no afecta otros)
- Extensible para comunidad (si se comparte)

---

**Próximos pasos**: Crear plan de implementación detallado con checklist de tareas específicas.
