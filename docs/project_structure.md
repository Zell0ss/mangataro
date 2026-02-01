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

