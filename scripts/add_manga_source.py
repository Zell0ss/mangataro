#!/usr/bin/env python3
"""Interactive script to add scanlator URLs for mangas"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator
from loguru import logger


def main():
    db = SessionLocal()

    try:
        # List all mangas
        mangas = db.query(Manga).order_by(Manga.title).all()
        print(f"\n=== Found {len(mangas)} mangas ===\n")

        for idx, manga in enumerate(mangas, 1):
            print(f"{idx}. {manga.title}")

        # Select manga
        manga_idx = int(input("\nSelect manga number (0 to exit): "))
        if manga_idx == 0:
            return

        manga = mangas[manga_idx - 1]
        print(f"\nSelected: {manga.title}")

        # List scanlators
        scanlators = db.query(Scanlator).filter_by(active=True).order_by(Scanlator.name).all()
        print(f"\n=== Available Scanlators ===\n")

        for idx, scanlator in enumerate(scanlators, 1):
            print(f"{idx}. {scanlator.name}")

        scanlator_idx = int(input("\nSelect scanlator number: "))
        scanlator = scanlators[scanlator_idx - 1]

        # Get URL
        url = input(f"\nEnter manga URL on {scanlator.name}: ").strip()

        # Check if already exists
        existing = db.query(MangaScanlator).filter_by(
            manga_id=manga.id,
            scanlator_id=scanlator.id
        ).first()

        if existing:
            print(f"\nWarning: Entry already exists with URL: {existing.scanlator_manga_url}")
            overwrite = input("Overwrite? (y/n): ").lower()
            if overwrite == 'y':
                existing.scanlator_manga_url = url
                existing.manually_verified = True
                db.commit()
                print("Updated!")
            return

        # Create new
        manga_scanlator = MangaScanlator(
            manga_id=manga.id,
            scanlator_id=scanlator.id,
            scanlator_manga_url=url,
            manually_verified=True
        )

        db.add(manga_scanlator)
        db.commit()

        print(f"\n✓ Added {manga.title} on {scanlator.name}")

        # Continue?
        continue_input = input("\nAdd another? (y/n): ").lower()
        if continue_input == 'y':
            main()  # Recursive call

    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
