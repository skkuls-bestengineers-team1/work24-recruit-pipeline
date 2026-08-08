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
    author : str

def load_database_settings(env_path: Path) -> DatabaseSettings:

    load_dotenv(dotenv_path=env_path, override=False)
    print(load_dotenv(dotenv_path=env_path, override=False))

    settings = DatabaseSettings(
        host=os.getenv("PGHOST"),
        port=int(os.getenv("PGPORT")),
        admin_database=os.getenv("PGADMINDATABASE"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        schema=os.getenv("PGSCHEMA"),
        echo_sql=os.getenv("SQLALCHEMY_ECHO", "false").strip().lower()
        in {"1", "true", "yes", "y"},
        author=os.getenv("PGAUTHOR"),
    )

    if not settings.password:
        raise ValueError("config/.env의 PGPASSWORD를 입력하세요.")
    if not SCHEMA_PATTERN.fullmatch(settings.schema):
        raise ValueError("PGSCHEMA 형식이 올바르지 않습니다.")
    return settings