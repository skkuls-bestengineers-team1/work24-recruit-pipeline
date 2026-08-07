from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    URL,
    create_engine,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Engine

from src.config_loader import DatabaseSettings, load_database_settings
from src.models import ValidationResult


from pathlib import Path

# 기본 path
BASE_PATH = Path(__file__).resolve().parent

RAW_DATA_PATH = BASE_PATH.parent / "data" / "raw" / "job_information.csv"

def create_postgresql_engine(settings:DatabaseSettings) -> Engine:
    ''' PostgreSQL Engine 생성 '''
    url = URL.create(
        drivername="postgresql+psycopg",    # psycopg : 파이썬과 PostgreSQL 데이터베이스를 연결해 주는 라이브러리
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )

    return create_engine(
        url,
        echo=settings.echo_sql,
        pool_pre_ping=True,
    )

def build_metadata(schema:str) -> tuple(MetaData,dict[str, Table]):
    '''
    MetaData()
    파이썬 ORM인 SQLAlchemy에서는 데이터베이스의 테이블 구조를 관리하는 객체이다.
    '''
    metadata = MetaData(schema=schema)

    # recruit(채용) 테이블을 생성한다.(데이터 활용)
    recruit = Table(
        "recruit",
        metadata,
        Column("no", Integer, nullable=False, server_default="0"),
        Column("company_name", String(50), nullable=False, primary_key=True),
        Column("position_title", String(200), nullable=False, primary_key=True),
        Column("recruit_provider", String(50), nullable=False),
        Column("company_category", String(20), nullable=True),
        Column("education", String(20), nullable=True),
        Column("career", String(20), nullable=True),
        Column("location", String(10), nullable=False),
        Column("working_condition", String(10), nullable=True),
        Column("deadline_date", DateTime(timezone=True), nullable=False),
        Column("registration_date", DateTime(timezone=True), nullable=False),
        Column("annual_salary", String(100), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("updated_by", String(20), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("created_by", String(20), nullable=False),
    )

    # recruit(채용) 원본 테이블을 생성한다.(데이터 적재 및 보관)
    recruit_raw = Table(
        "recruit_raw",
        metadata,
        Column("no_raw", Integer, nullable=False, server_default="0"),
        Column("company_name_raw", String(50), nullable=False, primary_key=True),
        Column("position_title_raw", String(200), nullable=False, primary_key=True),
        Column("recruit_provider_raw", String(50), nullable=False),
        Column("company_category_raw", String(20), nullable=True),
        Column("education_raw", String(20), nullable=True),
        Column("career_raw", String(20), nullable=True),
        Column("location_raw", String(10), nullable=False),
        Column("working_condition_raw", String(10), nullable=True),
        Column("deadline_date_raw", DateTime(timezone=True), nullable=False),
        Column("registration_date_raw", DateTime(timezone=True), nullable=False),
        Column("annual_salary_raw", String(100), nullable=False),
        Column("updated_at_raw", DateTime(timezone=True), nullable=False),
        Column("updated_by_raw", String(20), nullable=False),
        Column("created_at_raw", DateTime(timezone=True), nullable=False),
        Column("created_by_raw", String(20), nullable=False),
    )


    # recruit_pipeline_run_history(로그성) 테이블을 생성한다.
    recruit_pipeline_run_history = Table(
        "recruit_pipeline_run_history",
        metadata,
        Column("execution_id", PG_UUID(as_uuid=True), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=True),
        Column("status", Text, nullable=False),
        Column("raw_count", Integer, nullable=False),
        Column("standardized_count", Integer, nullable=False),
        Column("valid_count", Integer, nullable=False),
        Column("invalid_count", Integer, nullable=False),
        Column("issue_count", Integer, nullable=True),
        Column("error_message", Text, nullable=True),
    )

    # recruit_rejected(INVALID) 테이블을 생성한다.
    recruit_rejected = Table(
        "recruit_rejected",
        metadata,
        Column("no", Integer, nullable=False, server_default="0"),
        Column("execution_id", PG_UUID(as_uuid=True), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=True),
        Column("status", Text, nullable=False),
        Column("raw_count", Integer, nullable=False),
        Column("standardized_count", Integer, nullable=False),
        Column("valid_count", Integer, nullable=False),
        Column("invalid_count", Integer, nullable=False),
        Column("issue_count", Integer, nullable=True),
        Column("error_message", Text, nullable=True),
        Column('standardized_at', DateTime(timezone=True), nullable=True),
        Column('quality_status', Text, nullable=False),
        Column('quality_issue_count', Integer, nullable=False),
    )

    # recruit_standardized(표준화) 테이블을 생성한다.
    recruit_standardized = Table(
        "recruit_standardized",
        metadata,
        Column("no", Integer, nullable=False, server_default="0"),
        Column("execution_id", PG_UUID(as_uuid=True), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=True),
        Column("status", Text, nullable=False),
        Column("raw_count", Integer, nullable=False),
        Column("standardized_count", Integer, nullable=False),
        Column("valid_count", Integer, nullable=False),
        Column("invalid_count", Integer, nullable=False),
        Column("issue_count", Integer, nullable=True),
        Column("error_message", Text, nullable=True),
        Column('standardized_at', DateTime(timezone=True), nullable=True),
    )

    # recruit_valid(VALID) 테이블을 생성한다.
    recruit_valid = Table(
        "recruit_valid",
        metadata,
        Column("no", Integer, nullable=False, server_default="0"),
        Column("execution_id", PG_UUID(as_uuid=True), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=True),
        Column("status", Text, nullable=False),
        Column("raw_count", Integer, nullable=False),
        Column("standardized_count", Integer, nullable=False),
        Column("valid_count", Integer, nullable=False),
        Column("invalid_count", Integer, nullable=False),
        Column("issue_count", Integer, nullable=True),
        Column("error_message", Text, nullable=True),
        Column('standardized_at', DateTime(timezone=True), nullable=True),
        Column('quality_status', Text, nullable=False),
        Column('quality_issue_count', Integer, nullable=False),
    )

    # recruit_issue(ISSUE) 테이블을 생성한다.
    recruit_issue = Table(
        "recruit_issue",
        metadata,
        Column("no", Integer, nullable=False, server_default="0"),
        Column('rule_code', Text, nullable=False),
        Column('column_name', Text, nullable=False),
        Column('invalid_value', Text, nullable=True),
        Column('error_message', Text, nullable=False),

    )

    table_dict = {
        "recruit" : recruit,
        "recruit_pipeline_run_history": recruit_pipeline_run_history,
        "recruit_rejected": recruit_rejected,
        "recruit_standardized": recruit_standardized,
        "recruit_valid": recruit_valid,
        "recruit_issue": recruit_issue
    }

    return metadata, table_dict

def load_to_postgresql(
    # raw_df : pd.DataFrame,
    settings : DatabaseSettings,
)-> None:

    raw_df = pd.read_csv(RAW_DATA_PATH, encoding='utf-8-sig')
    print(raw_df.columns)
    print()
    # print(raw_df['position_title'])

    # 원본 데이터를 copy하여 raw_prepared 생성한다.
    # def insert(
    #         self,
    #         loc: int,
    #         column: Hashable,
    #         value: object,
    #         allow_duplicates: bool | lib.NoDefault = lib.no_default,
    # )


    raw_prepared = raw_df.copy()


    '''
    'no'(Praminary Key, 순차 증가) 컬럼을 생성한다.
    '''
    raw_prepared['no'] = range(0, len(raw_prepared))

    '''
    xx_raw 컬럼을 생성하여 원본 데이터를 해당 컬럼에 적재한다.
    '''
    raw_prepared.insert(0, 'no_raw', raw_prepared['no'])
    raw_prepared.insert(1, 'position_title_raw', raw_df['position_title'])
    raw_prepared.insert(2, 'company_name_raw', raw_df['company_name'])
    raw_prepared.insert(3, 'company_category_raw', raw_df['company_category'])
    raw_prepared.insert(4, 'recruit_provider_raw', raw_df['recruit_provider'])
    raw_prepared.insert(5, 'annual_salary_raw', raw_df['annual_salary'])
    raw_prepared.insert(6, 'career_raw', raw_df['career'])
    raw_prepared.insert(7, 'education_raw', raw_df['education'])
    raw_prepared.insert(8, 'working_condition_raw', raw_df['working_condition'])
    raw_prepared.insert(9, 'location_raw', raw_df['location'])
    raw_prepared.insert(10, 'deadline_date_raw', raw_df['deadline_date'])
    raw_prepared.insert(11, 'registration_date_raw', raw_df['registration_date'])
    raw_prepared.insert(12, 'updated_at', datetime.now().strftime('%Y-%m-%d'))
    raw_prepared.insert(13, 'updated_by', 'PJS')
    raw_prepared.insert(14, 'created_at', datetime.now().strftime('%Y-%m-%d'))
    raw_prepared.insert(15, 'created_by', 'PJS')

    '''
    기존 컬럼(_raw가 컬럼이 붙어있지 않은)을 삭제한다.
    '''
    raw_prepared.drop(columns='position_title', axis=0, inplace=True)
    raw_prepared.drop(columns='company_name', axis=0, inplace=True)
    raw_prepared.drop(columns='company_category', axis=0, inplace=True)
    raw_prepared.drop(columns='recruit_provider', axis=0, inplace=True)
    raw_prepared.drop(columns='annual_salary', axis=0, inplace=True)
    raw_prepared.drop(columns='career', axis=0, inplace=True)
    raw_prepared.drop(columns='education', axis=0, inplace=True)
    raw_prepared.drop(columns='working_condition', axis=0, inplace=True)
    raw_prepared.drop(columns='location', axis=0, inplace=True)
    raw_prepared.drop(columns='deadline_date', axis=0, inplace=True)
    raw_prepared.drop(columns='registration_date', axis=0, inplace=True)

    # print(raw_prepared.columns)
    print()

    print(raw_prepared.columns)

    # engine = create_postgresql_engine(settings)
    metadata, tables = build_metadata('work24_recruit_schema')

def main() -> None:

    # print(build_metadata('work24_recruit_schema'))
    load_to_postgresql(DatabaseSettings)
    # print(RAW_DATA_PATH)

    '''
    2026-08-10
    현재 : 원본_raw 데이터프레임 생성 완료
    다음 : recruit_raw 테이블에 insert
    '''

if __name__ == "__main__":
    main()