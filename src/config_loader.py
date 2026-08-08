from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    admin_database: str
    database: str
    user: str
    password: str
    schema: str
    echo_sql: bool
    author: str


def load_raw_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def load_reference_data(reference_dir: Path) -> dict[str, pd.DataFrame]:
    references: dict[str, pd.DataFrame] = {}
    if not reference_dir.exists():
        return references

    for csv_path in sorted(reference_dir.glob("*.csv")):
        references[csv_path.stem.replace("_reference", "")] = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
        )
    return references


def load_quality_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_database_settings(env_path: Path) -> DatabaseSettings:
    load_dotenv(dotenv_path=env_path, override=True)

    settings = DatabaseSettings(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        admin_database=os.getenv("PGADMINDATABASE", "postgres"),
        database=os.getenv("PGDATABASE", ""),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        schema=os.getenv("PGSCHEMA", ""),
        echo_sql=os.getenv("SQLALCHEMY_ECHO", "false").strip().lower()
        in {"1", "true", "yes", "y"},
        author=os.getenv("PGAUTHOR", ""),
    )

    if not settings.password:
        raise ValueError("config/.env의 PGPASSWORD를 입력하세요.")
    if not settings.author:
        raise ValueError("config/.env의 PGAUTHOR를 입력하세요.")
    if not SCHEMA_PATTERN.fullmatch(settings.schema):
        raise ValueError("PGSCHEMA 형식이 올바르지 않습니다.")
    return settings
