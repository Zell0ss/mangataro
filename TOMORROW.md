# Ready for Tomorrow - Quick Start Guide

**Date:** 2026-03-17 (End of Day)
**Status:** Production ✅
**Project:** Fully operational — VortexScans añadido, Telegram + LogCentral integrados

---

## 🆕 Cambios de hoy (2026-03-17)

### VortexScans plugin ✅ (push hecho hoy)
- **File:** `scanlators/vortex_scans.py` — clase `VortexScans`
- **DB:** scanlator ID 35
- Mapear manga en `/admin/map-sources?scanlator=35`

### Notificaciones Telegram ✅
- Reemplaza Discord. `NOTIFICATION_TYPE=telegram` en `.env`
- Variables nuevas: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Agrupa capítulos por manga: `Solo Leveling: 200-215 (AsuraScans)`
- Rangos consecutivos comprimidos, listas si hay huecos
- **Fichero:** `api/services/notification_service.py`

### LogCentral integrado ✅
- Sink JSON en `logs/mangataro-lc.log` (JSON puro, separado del log de texto)
- Vector configurado en `/data/logcentral/vector/vector.toml` — source `mangataro`
- **Pendiente verificar mañana:** que el próximo job de tracking aparezca con levels y timestamps correctos

---

## ✅ Pendiente verificar mañana

1. **LogCentral funcionando bien** — correr un job y comprobar:
   ```bash
   logcentral query --source mangataro
   ```
   Debería verse el tracking con levels correctos (INFO/WARNING/DEBUG) y timestamps reales.

2. **Alerta Telegram** — esperar al próximo cron. Si no llega nada, puede ser que no haya capítulos nuevos (el job de hoy encontró 0).

---

## 🗂 Estado del sistema

| Scanlator   | ID | Estado    |
|-------------|-----|-----------|
| AsuraScans  | 7  | ✅ activo |
| RavenScans  | 32 | ✅ activo |
| MadaraScans | 33 | ✅ activo |
| MangaDex    | 34 | ✅ activo |
| VortexScans | 35 | ✅ activo |

**Scanlators bloqueados (ver sección en CLAUDE.md):** Bato.to (cerrado), ManhwaClan, Manta.net (Cloudflare Turnstile)

---

## 🔧 Comandos útiles

```bash
# Trigger tracking manual
curl -s -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": true}' | python3 -m json.tool

# Ver logs de tracking
tail -f /data/mangataro/logs/tracking.log

# Ver en LogCentral
logcentral query --source mangataro
logcentral query --source mangataro --level warning,error

# Reiniciar servicio
sudo systemctl restart mangataro.service
```
