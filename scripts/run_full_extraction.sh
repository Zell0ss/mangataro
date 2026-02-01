#!/bin/bash
# Helper script to run the full MangaTaro extraction

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "MangaTaro Full Extraction"
echo "=========================================="
echo ""
echo "This will extract all 94 manga bookmarks from MangaTaro."
echo "Estimated time: 1-2 hours (with 2-5 second delays between requests)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Extraction cancelled."
    exit 1
fi

echo ""
echo "Starting extraction..."
echo "You can monitor progress by running in another terminal:"
echo "  tail -f $PROJECT_DIR/logs/extract_mangataro_*.log"
echo ""

cd "$PROJECT_DIR"
source .venv/bin/activate
python scripts/extract_mangataro.py

echo ""
echo "=========================================="
echo "Extraction Complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "  - Cover images: data/img/"
echo "  - Markdown fichas: docs/fichas/"
echo "  - Scanlators list: docs/scanlators.md"
echo ""
echo "Check database:"
echo "  mysql -u mangataro_user -pyour_password_here mangataro -e 'SELECT COUNT(*) FROM mangas;'"
echo "  mysql -u mangataro_user -pyour_password_here mangataro -e 'SELECT COUNT(*) FROM scanlators;'"
echo ""
