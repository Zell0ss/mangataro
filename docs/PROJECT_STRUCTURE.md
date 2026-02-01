# Project structure

## Initial version
```bash
mangataro/
├── data/
│   ├── mangataro-export.json      # Export original (histórico)
│   └── img/                        # Portadas descargadas
│
├── docs/
│   ├── plans/                      # Documentación de diseño
│   └── fichas/                     # Markdown generados por manga
│
├── scanlators/
│   ├── __init__.py                # Auto-discovery de scanlators
│   ├── base.py                    # BaseScanlator (clase abstracta)
│   ├── uscanlations.py            # Implementación específica
│   ├── asura_scans.py             # Implementación específica
│   └── template.py                # Template para nuevos scanlators
│
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
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
│   ├── add_manga.py               # CLI para añadir manga
│   └── add_scanlator.py           # CLI para añadir scanlator
│
├── frontend/                       # Proyecto Astro separado
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.astro        # Homepage
│   │   │   ├── manga/[id].astro   # Detalle
│   │   │   ├── recent.astro       # Últimos capítulos
│   │   │   ├── scanlators.astro   # Lista scanlators
│   │   │   └── admin.astro        # Admin panel
│   │   ├── components/
│   │   │   ├── MangaCard.astro
│   │   │   ├── ChapterList.astro
│   │   │   └── ...
│   │   └── layouts/
│   │       └── Layout.astro
│   └── package.json
│
├── n8n/
│   └── workflows/
│       ├── check-updates.json     # Workflow de tracking
│       └── README.md              # Instrucciones de importación
│
├── requirements.txt               # Python dependencies
├── pyproject.toml                # Poetry config (alternativa)
├── .env.example                  # Template de variables
└── README.md                     # Documentación principal
```



### API FastAPI - Endpoints Completos
Mangas:

GET /api/mangas - Lista todos los mangas (con filtros: status, scanlator, búsqueda)
GET /api/mangas/{id} - Detalle de un manga con sus capítulos
POST /api/mangas - Crear manga manualmente (título, alt_titles, cover_url, scanlator_id, manga_url)
PUT /api/mangas/{id} - Actualizar manga (cambiar status, notas)
DELETE /api/mangas/{id} - Eliminar manga
Scanlators:

GET /api/scanlators - Lista todos los scanlators
GET /api/scanlators/{id}/mangas - Mangas de un scanlator específico
POST /api/scanlators - Registrar nuevo scanlator (name, class_name, base_url)
PUT /api/scanlators/{id} - Actualizar scanlator (marcar inactivo si cierra)
Manga-Scanlator (fuentes alternativas):

POST /api/mangas/{id}/sources - Añadir fuente alternativa (scanlator_id, url)
DELETE /api/manga-scanlator/{id} - Eliminar fuente
Capítulos:

GET /api/chapters/recent - Últimos capítulos detectados (para homepage)
GET /api/chapters/unread - Capítulos no leídos
PUT /api/chapters/{id}/read - Marcar como leído
Tracking:

POST /api/check-updates - Ejecutar check manual (o desde n8n)
POST /api/check-updates/{manga_id} - Check de un manga específico
GET /api/tracking/status - Estado del último tracking (cuándo, cuántos checks, errores)

### Estructura de la API
Tu propuesta (views/crud/models) es perfecta. Es clara, escalable y separa responsabilidades. Te sugiero una pequeña expansión:


api/
├── __init__.py
├── views.py          # Endpoints, validaciones de entrada, responses
├── crud.py           # Lógica de negocio, queries a DB
├── schemas.py        # Pydantic schemas (request/response)
├── models.py         # SQLAlchemy models (tablas DB)
├── dependencies.py   # Database session, auth (futuro)
└── utils.py          # Helpers (descarga imágenes, etc.)
Separar schemas.py de models.py es útil:

models.py: Clases SQLAlchemy que mapean tablas MariaDB
schemas.py: Pydantic schemas para validación y serialización API
Evita mezclar responsabilidades ORM vs validación
Endpoint de binge reading:


PUT /api/mangas/{manga_id}/read-until
Body: { "chapter_number": "42.5", "scanlator_id": 3 }
Marca ese capítulo y todos los anteriores del mismo scanlator como leídos
Retorna cantidad de capítulos marcados
Útil también para "marcar todo como leído"
Flujo views → crud:

views.py: Recibe request, valida con schema, llama crud.mark_read_until()
crud.py: Query a DB, actualiza registros, retorna resultado
views.py: Formatea response con schema de salida


### Frontend (Astro)

Páginas principales:

1. Homepage (/)

Grid de portadas de mangas (estilo biblioteca)
Filtros: Por status, por scanlator, búsqueda
Badge en portadas con número de capítulos no leídos
Ordenar por: Últimos añadidos, Alfabético, Última actualización

2. Detalle de manga (/manga/[id])

Portada grande + títulos alternativos
Lista de fuentes (scanlators donde está disponible)
Tabla de capítulos por scanlator:
Número, Título, Fecha publicación, Fecha detectado
Botón "Leer" → abre URL en nueva pestaña + marca como leído
Botón "Marcar hasta aquí" → binge reading
Cambiar status del manga (dropdown)

3. Últimos capítulos (/recent)

Feed de capítulos detectados recientemente
Agrupados por fecha (Hoy, Ayer, Esta semana)
Click en capítulo → marca como leído y abre

4. Scanlators (/scanlators)

Lista de todos los scanlators
Por cada uno: logo/nombre, cantidad de mangas, último check, estado (activo/inactivo)
Click → filtro de mangas de ese scanlator

5. Admin (/admin) - Futuro

Formulario añadir manga manualmente
Formulario añadir scanlator
Trigger manual de check-updates
Ver logs de errores de scraping

Componentes reutilizables:

MangaCard.astro - Tarjeta de portada
ChapterList.astro - Lista de capítulos
ScanlatorBadge.astro - Badge con nombre scanlator
StatusDropdown.astro - Selector de status
