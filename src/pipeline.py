from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.config_loader import (
    load_database_settings,
    # load_quality_rules,
    # load_raw_data,
    # load_reference_data,
)
# from src.crawler import crawl

from src.database import (
    create_work24_recruit_schema,
    create_postgresql_engine,
    build_metadata,
    insert_target_table,
)
from src.models import PipelinePaths, PipelineResult
# from src.quality_checker import validate_inquiries
# from src.reporting import build_report, save_file_outputs
# from src.standardizer import standardize_inquiries

# 테스트용(crawling 연동 후 삭제 예정)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "job_information.csv"

def run_full_pipeline(
    paths: PipelinePaths,
    env_path: Path,
) -> str:

    # 1. 크롤링 진행 여부(y/n)에 따라 로직 변경

    # 2. summary할 대상 dataframe을 생성한다.
    # valid, invalid, standardized, issue dataframe 생성 필요
    # 3. 데이터베이스에 적재한다.
    # (1) 환경변수를 load한다.
    settings = load_database_settings(env_path)

    # (2) 스키마를 생성한다.
    engine = create_postgresql_engine(settings)
    create_work24_recruit_schema(settings, engine)
    print('-' * 40)
    print(f'고용24 스키마가 정상적으로 생성되었습니다.')
    print('-' * 40)

    # (3) metadata 사용하여 table을 생성한다.
    metadata, tables = build_metadata('work24_recruit_schema')
    metadata.create_all(engine, checkfirst=True)
    print('-' * 40)
    print(f'고용24 테이블이 정상적으로 생성되었습니다.')
    print('-' * 40)

    # (5) 테이블에 데이터를 적재한다.
    target = {
        "recruit",
        "recruit_raw",
        # "recruit_pipeline_run_history"
        # "recruit_rejected",
        # "recruit_standardized",
        # "recruit_valid",
        # "recruit_issue",
    }

    # 크롤링 연동 후 삭제 예정
    # 크롤링 연동 후 크롤링 결과 값이 들어갈 예정
    crawling_df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')

    for table in target:
        insert_target_table(crawling_df
                            , table
                            , tables
                            , engine
                            , settings)

    # 4. 결과를 json 파일로 저장한다.

    #  현재 개발중이므로 주석처리
    #  반환값 String으로 임시 변경
    # return PipelineResult(
    #     crawl=crawl_result,
    #     validation=validation,
    #     report=report,
    #     database_summary=database_summary,
    # )
    return f'데이터베이스/스키마/테이블/데이터 적재까지 완료되었습니다.'

