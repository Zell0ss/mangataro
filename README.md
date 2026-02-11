# MangaTaro

Self-hosted manga chapter tracker. Automatically monitors scanlation sites and shows you new chapters.

![Homepage Updates](docs/images/homepage_updates.png)

## Quick Start

```bash
cp .env.example .env
# Edit .env with your database credentials

pip install -r requirements.txt && cd frontend && npm install && cd ..
uvicorn api.main:app --reload &
cd frontend && npm run dev
```

Visit: **http://localhost:4343**

See [Getting Started](docs/GETTING_STARTED.md) for detailed installation.

## Features

- 📚 **Track Manga Across Scanlators** - Monitor multiple sources for each manga
- 🔍 **Automatic Chapter Detection** - Background jobs fetch new chapters
- 🌐 **Modern Web Interface** - Clean UI built with Astro + TailwindCSS
- 🔔 **Discord Notifications** - Get notified when new chapters drop
- 🧩 **Extensible Plugin System** - Add new scanlators in minutes

## Screenshots

<table>
<tr>
<td width="33%">
<img src="docs/images/homepage_updates.png" alt="Updates Feed"/>
<p align="center"><strong>Updates Feed</strong></p>
</td>
<td width="33%">
<img src="docs/images/library-grid.png" alt="Library Grid"/>
<p align="center"><strong>Library Grid</strong></p>
</td>
<td width="33%">
<img src="docs/images/manga-detail.png" alt="Manga Detail"/>
<p align="center"><strong>Manga Detail</strong></p>
</td>
</tr>
</table>

## Documentation

**For Users:**
- 📖 [Getting Started](docs/GETTING_STARTED.md) - Installation and setup
- 👤 [User Guide](docs/USER_GUIDE.md) - Daily operations

**For Developers:**
- 🛠️ [Developer Guide](docs/DEVELOPER_GUIDE.md) - Architecture and API
- ⚡ [Plugin Quick Reference](docs/PLUGIN_QUICK_REFERENCE.md) - Add scanlators fast
- 🤖 [CLAUDE.md](CLAUDE.md) - Guide for AI assistants

## Tech Stack

FastAPI • Astro • Playwright • MariaDB

## Status

✅ **Production Ready** - Tracking 90+ manga across multiple scanlators

## License

MIT
