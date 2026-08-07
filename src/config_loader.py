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
    database: str
    user: str
    password: str
    schema: str
    echo_sql: bool

def load_database_settings(env_path: Path) -> DatabaseSettings:
    load_dotenv(dotenv_path=env_path, override=False)
    settings = DatabaseSettings(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "work24_recruit_database"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        schema=os.getenv("PGSCHEMA", "work24_recruit_schema"),
        echo_sql=os.getenv("SQLALCHEMY_ECHO", "false").strip().lower()
        in {"1", "true", "yes", "y"},
    )
    if not settings.password:
        raise ValueError("config/.env의 PGPASSWORD를 입력하세요.")
    if not SCHEMA_PATTERN.fullmatch(settings.schema):
        raise ValueError("PGSCHEMA 형식이 올바르지 않습니다.")
    return settings