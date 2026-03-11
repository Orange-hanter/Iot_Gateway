#!/usr/bin/env python3
"""Migrate legacy Arduino driver type to DHT11 naming."""

import argparse
import sqlite3
from pathlib import Path

OLD_TYPE = "arduino_button_bpm280"
NEW_TYPE = "arduino_button_dht11"


def migrate(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        cursor.execute(
            "UPDATE devices SET driver_type = ? WHERE driver_type = ?",
            (NEW_TYPE, OLD_TYPE),
        )
        updated = cursor.rowcount if cursor.rowcount is not None else 0
        conn.commit()
        return int(updated)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate devices.driver_type to DHT11")
    parser.add_argument("--db", default="data/iot_core.db", help="Path to sqlite DB")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    updated = migrate(db_path)
    print(f"Updated rows: {updated}")


if __name__ == "__main__":
    main()
