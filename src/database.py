from __future__ import annotations

import re
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
from sqlalchemy.exc import SQLAlchemyError

from src.config_loader import DatabaseSettings
from src.models import ValidationResult


from pathlib import Path

def create_work24_recruit_schema(settings:DatabaseSettings , engine:Engine)->None:
    ''' PostgreSQL Engine 생성(스키마용) '''
    try:
        with engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(
                text(f'create schema if not exists "{settings.schema}"')
            )
    except Exception as error:
        raise SQLAlchemyError(f'{settings.schema} 생성에 실패하였습니다.')
    finally:
        engine.dispose()

def create_postgresql_engine(settings:DatabaseSettings) -> Engine:
    ''' PostgreSQL Engine 생성(테이블용) '''
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
    '''테이블 metadata 생성'''

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
        Column("company_category", String(100), nullable=True),
        Column("education", String(100), nullable=True),
        Column("career", String(100), nullable=True),
        Column("location", String(100), nullable=False),
        Column("working_condition", String(100), nullable=True),
        Column("deadline_date", DateTime(timezone=True), nullable=False),
        Column("registration_date", DateTime(timezone=True), nullable=False),
        Column("annual_salary", String(100), nullable=False),
        Column("min_annual_salary", Integer, nullable=False, server_default="0"),
        Column("max_annual_salary", Integer, nullable=False, server_default="0"),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("updated_by", String(100), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("created_by", String(100), nullable=False),
    )

    # recruit(채용) 원본 테이블을 생성한다.(데이터 적재 및 보관)
    recruit_raw = Table(
        "recruit_raw",
        metadata,
        Column("no_raw", Integer, nullable=False, server_default="0"),
        Column("company_name_raw", String(50), nullable=False, primary_key=True,server_default="0"),
        Column("position_title_raw", String(200), nullable=False, primary_key=True,server_default="0"),
        Column("recruit_provider_raw", String(50), nullable=False),
        Column("company_category_raw", String(100), nullable=True),
        Column("education_raw", String(100), nullable=True),
        Column("career_raw", String(100), nullable=True),
        Column("location_raw", String(100), nullable=False),
        Column("working_condition_raw", String(100), nullable=True),
        Column("deadline_date_raw", DateTime(timezone=True), nullable=False),
        Column("registration_date_raw", DateTime(timezone=True), nullable=False),
        Column("annual_salary_raw", String(100), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("updated_by", String(100), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("created_by", String(100), nullable=False),
    )

    # recruit_pipeline_run_history(로그성) 테이블을 생성한다.
    recruit_pipeline_run_history = Table(
        "recruit_pipeline_run_history",
        metadata,
        Column("execution_id", PG_UUID(as_uuid=True), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=True),
        Column("status", Text, nullable=False),
        Column("raw_count", Integer, nullable=False,server_default="0"),
        Column("standardized_count", Integer, nullable=False,server_default="0"),
        Column("valid_count", Integer, nullable=False, server_default="0"),
        Column("invalid_count", Integer, nullable=False, server_default="0"),
        Column("issue_count", Integer, nullable=True, server_default="0"),
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
        "recruit_raw": recruit_raw,
        "recruit_pipeline_run_history": recruit_pipeline_run_history,
        "recruit_rejected": recruit_rejected,
        "recruit_standardized": recruit_standardized,
        "recruit_valid": recruit_valid,
        "recruit_issue": recruit_issue
    }

    return metadata, table_dict

def insert_recruit_raw_table(
    crawling_df : pd.DataFrame
   , target : str
   , tables : dict[str, Table]
   , engine : Engine
   , settings : DatabaseSettings
) -> bool:
    ''' recruit_raw 테이블에 데이터를 적재한다. '''

    # 1. 원본 데이터를 복사한다.
    _recruit_df = crawling_df.copy()

    # 2. _recruit_df['no'] 컬럼(Primary Key, 순차증가), 데이터 관리 컬럼을 생성한다.
    _recruit_df['no'] = range(0, len(crawling_df))


    for col in _recruit_df.columns:
        # min_annual_salary, max_annual_salary 파생 컬럼이므로 raw 테이블에서는 제외된다.
        if col != "min_annual_salary" and col != 'max_annual_salary':
            raw_col = col+'_raw'
            _recruit_df.rename(
            columns={
                col : raw_col,
                },
                inplace=True
            )

    _recruit_df['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _recruit_df['updated_by'] = settings.author

    _recruit_df['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _recruit_df['created_by'] = settings.author

    # 3. 기존에 있는 데이터를 삭제한다.(Duplicate Key 방지)
    try:
        with engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(
                text(f'delete from work24_recruit_schema.{target}')
            )
    except SQLAlchemyError as error:
        print(f'SQLALCHEMY_ERROR: {error}')

    # 4. 테이블에 데이터를 적재한다.
    try:
        with engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
        ) as connection:
            for idx in range(0, len(crawling_df.to_dict(orient='records'))):
                connection.execute(
                    tables[f'{target}'].insert(),
                    _recruit_df.to_dict(orient='records')[idx]
                )
        return True
    except SQLAlchemyError as error:
        print(f'SQLALCHEMY_ERROR: {error}')
        return False

def insert_recruit_table(
    crawling_df : pd.DataFrame
   , target : str
   , tables : dict[str, Table]
   , engine : Engine
   , settings : DatabaseSettings
) -> bool:
    ''' recruit 테이블에 데이터를 적재한다. '''
    # 1. 원본 데이터를 복사한다.
    _recruit_df = crawling_df.copy()

    # 2. _recruit_df['no'] 컬럼(Primary Key, 순차증가), 데이터 관리 컬럼을 생성한다.
    _recruit_df['no'] = range(0, len(crawling_df))

    _recruit_df['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _recruit_df['updated_by'] = settings.author

    _recruit_df['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _recruit_df['created_by'] = settings.author

    # 3. 기존에 있는 데이터를 삭제한다.(Duplicate Key 방지)
    try:
        with engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(
                text(f'delete from work24_recruit_schema.{target}')
            )
    except SQLAlchemyError as error:
        print(f'SQLALCHEMY_ERROR: {error}')

    # 4. 테이블에 데이터를 적재한다.
    try:
        with engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
        ) as connection:
            for idx in range(0, len(crawling_df.to_dict(orient='records'))):
                connection.execute(
                    tables[f'{target}'].insert(),
                    _recruit_df.to_dict(orient='records')[idx]
                )
        return True
    except SQLAlchemyError as error:
        print(f'SQLALCHEMY_ERROR: {error}')
        return False

'''
현재 :  recruit, recruit_raw 생성 및 데이터 적재까지 완료
다음 : 
# insert_recruit_pipeline_run_history_table
# recruit_rejected
# recruit_standardized
# recruit_valid
# recruit_issue
'''
def insert_target_table(crawling_df : pd.DataFrame
                   , target : str
                   , tables : dict[str, Table]
                   , engine : Engine
                   , settings : DatabaseSettings):
    print('-' * 40)
    print('table insert start')
    print('-' * 40)

    if target == 'recruit':
        if insert_recruit_table(
             crawling_df
            , target
            , tables
            , engine
            , settings
        ):
            print(f'{target} 테이블에 데이터가 정상적으로 적재되었습니다.')
        else:
            print(f'{target} 테이블에 데이터 적재가 실패하였습니다.')

    elif target == 'recruit_raw':
        if insert_recruit_raw_table(
                crawling_df
                , target
                , tables
                , engine
                , settings
        ):
            print(f'{target} 테이블에 데이터가 정상적으로 적재되었습니다.')
        else:
            print(f'{target} 테이블에 데이터 적재가 실패하였습니다.')

    ## 나머지 테이블 구현 예정


    print('-' * 40)
    print('table insert end')
    print('-' * 40)