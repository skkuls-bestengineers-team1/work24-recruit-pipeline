from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config_loader import (
    load_database_settings,
    load_quality_rules,
    load_raw_data,
    load_reference_data,
)
from src.crawler import crawl_jobs
from src.database import (
    build_metadata,
    create_postgresql_engine,
    create_work24_recruit_schema,
    insert_recruit_table,
    insert_recruit_raw_table,
    insert_recruit_run_pipeline_history_table,
    insert_recruit_standardized_table,
    insert_recruit_valid_table,
    insert_recruit_rejected_table,
    insert_recruit_issue_table
)
from src.models import PipelinePaths
from src.quality_checker import validate_jobs
from src.standardizer import normalize_company_category, standardize_jobs


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _prepare_raw_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    raw_df = dataframe.copy()
    if "company_category" in raw_df.columns:
        raw_df["company_category"] = raw_df["company_category"].map(
            normalize_company_category
        )
    return raw_df


def _prepare_recruit_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    recruit_columns = [
        "company_name",
        "position_title",
        "recruit_provider",
        "company_category",
        "education",
        "career",
        "location",
        "working_condition",
        "deadline_date",
        "registration_date",
        "annual_salary",
        "min_annual_salary",
        "max_annual_salary",
    ]
    recruit_df = dataframe.copy()
    for column in recruit_columns:
        if column not in recruit_df.columns:
            recruit_df[column] = pd.NA
    recruit_df = recruit_df[recruit_columns].copy()
    recruit_df["min_annual_salary"] = (
        pd.to_numeric(recruit_df["min_annual_salary"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    recruit_df["max_annual_salary"] = (
        pd.to_numeric(recruit_df["max_annual_salary"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    return recruit_df


def run_full_pipeline(
    paths: PipelinePaths,
    env_path: Path,
    skip_crawl: bool = False,
) -> str:
    print("-" * 40)
    if skip_crawl:
        print("기존 raw CSV를 사용합니다.")
        crawling_df = load_raw_data(paths.raw_csv)
    else:
        print("크롤링을 시작합니다.")
        crawling_df = crawl_jobs(save=True, save_path=paths.raw_csv)
    crawling_df = _prepare_raw_dataframe(crawling_df)
    print(f"원천 데이터: {len(crawling_df)}건")
    print("-" * 40)

    references = load_reference_data(paths.reference_dir)
    standardized_df = standardize_jobs(
        raw_df=crawling_df,
        references=references,
    )
    print(f"표준화 데이터: {len(standardized_df)}건")

    rules = load_quality_rules(paths.quality_rules)
    validation = validate_jobs(
        standardized_df=standardized_df,
        rules=rules,
    )
    print(
        f"품질 검증 완료 | valid={len(validation.valid_df)} "
        f"invalid={len(validation.invalid_df)} "
        f"issue={len(validation.issue_detail_df)}"
    )

    for path, dataframe in [
        (paths.standardized_csv, standardized_df),
        (paths.valid_csv, validation.valid_df),
        (paths.invalid_csv, validation.invalid_df),
        (paths.issue_csv, validation.issue_detail_df),
        (paths.quality_result_csv, validation.row_result_df),
    ]:
        _ensure_parent(path)
        dataframe.to_csv(path, index=False, encoding="utf-8-sig")

    settings = load_database_settings(env_path)
    engine = create_postgresql_engine(settings)
    create_work24_recruit_schema(settings, engine)
    engine = create_postgresql_engine(settings)
    print("-" * 40)
    print("고용24 스키마가 정상적으로 생성되었습니다.")
    print("-" * 40)

    metadata, tables = build_metadata(settings.schema)
    metadata.create_all(engine, checkfirst=True)
    print("-" * 40)
    print("고용24 테이블이 정상적으로 생성되었습니다.")
    print("-" * 40)

    recruit_df = _prepare_recruit_dataframe(validation.valid_df)
    raw_df = _prepare_raw_dataframe(crawling_df)

    # 실제 데이터 적재
    insert_recruit_table(recruit_df, "recruit", tables, engine, settings)
    insert_recruit_raw_table(raw_df, "recruit_raw", tables, engine, settings)
    insert_recruit_run_pipeline_history_table(
                        crawling_df,
                        standardized_df,
                        validation.valid_df,
                        validation.invalid_df,
                        validation.issue_detail_df,
                        "recruit_pipeline_run_history",
                        tables,
                        engine)
    insert_recruit_standardized_table(standardized_df, 'recruit_standardized', tables, engine, settings)
    insert_recruit_valid_table(validation.valid_df, 'recruit_valid', tables, engine)
    insert_recruit_rejected_table(validation.invalid_df, 'recruit_rejected', tables, engine)
    insert_recruit_issue_table(validation.issue_detail_df, 'recruit_issue', tables, engine)



    return (
        "데이터베이스/스키마/테이블/데이터 적재까지 완료되었습니다. "
        f"(raw={len(crawling_df)}, standardized={len(standardized_df)}, "
        f"valid={len(validation.valid_df)}, invalid={len(validation.invalid_df)})"
    )
