from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import json

from src.config_loader import load_database_settings
from src.database import create_postgresql_engine


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
REPORT_DIR = BASE_DIR / "reports"


def load_data() -> pd.DataFrame:
    """
    PostgreSQL의 recruit 테이블을 DataFrame으로 불러옵니다.
    """

    settings = load_database_settings(ENV_PATH)
    engine = create_postgresql_engine(settings)

    try:
        df = pd.read_sql_table(
            table_name="recruit",
            con=engine,
            schema=settings.schema,
        )
    finally:
        engine.dispose()

    # 날짜 컬럼 타입 변환
    for column in ["deadline_date", "registration_date"]:
        if column in df.columns:
            df[column] = (
                pd.to_datetime(
                    df[column],
                    errors="coerce",
                    utc=True,
                )
                .dt.tz_convert(None)
                .dt.normalize()
            )

    # 연봉 컬럼 숫자형 변환
    for column in ["min_annual_salary", "max_annual_salary"]:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def get_summary(df: pd.DataFrame) -> dict:
    """
    Streamlit 대시보드 상단 KPI에 사용할 요약 정보를 계산합니다.
    """

    total_postings = len(df)

    company_count = (
        df["company_name"].nunique()
        if "company_name" in df.columns
        else 0
    )

    # 최소/최대 연봉이 모두 정상적으로 존재하는 데이터만 사용
    salary_df = df[
        (df["min_annual_salary"] > 0)
        & (df["max_annual_salary"] > 0)
    ].copy()

    if salary_df.empty:
        average_salary = None
    else:
        salary_mid = (
            salary_df["min_annual_salary"]
            + salary_df["max_annual_salary"]
        ) / 2

        average_salary = round(float(salary_mid.mean()), 1)

    # 오늘부터 7일 이내 마감되는 공고
    today = pd.Timestamp(date.today())
    seven_days_later = pd.Timestamp(
        date.today() + timedelta(days=7)
    )

    if "deadline_date" in df.columns:
        deadline_soon_count = df[
            df["deadline_date"].between(
                today,
                seven_days_later,
                inclusive="both",
            )
        ].shape[0]
    else:
        deadline_soon_count = 0

    return {
        "total_postings": total_postings,
        "company_count": company_count,
        "average_salary": average_salary,
        "deadline_soon_count": deadline_soon_count,
    }


def filter_jobs(
    df: pd.DataFrame,
    keyword: str = "",
    providers: list[str] | None = None,
    careers: list[str] | None = None,
    educations: list[str] | None = None,
    min_salary: float | None = None,
    max_salary: float | None = None,
    deadline_start: date | None = None,
    deadline_end: date | None = None,
) -> pd.DataFrame:
    """
    Streamlit의 채용공고 검색 조건에 따라 데이터를 필터링합니다.
    """

    filtered_df = df.copy()

    # 공고명 / 기업명 검색
    if keyword:
        keyword = keyword.strip()

        title_mask = filtered_df["position_title"].fillna("").str.contains(
            keyword,
            case=False,
            regex=False,
        )

        company_mask = filtered_df["company_name"].fillna("").str.contains(
            keyword,
            case=False,
            regex=False,
        )

        filtered_df = filtered_df[
            title_mask | company_mask
        ]

    # 채용정보 제공처
    if providers:
        filtered_df = filtered_df[
            filtered_df["recruit_provider"].isin(providers)
        ]

    # 경력
    if careers:
        filtered_df = filtered_df[
            filtered_df["career"].isin(careers)
        ]

    # 학력
    if educations:
        filtered_df = filtered_df[
            filtered_df["education"].isin(educations)
        ]

    # 최소 희망 연봉
    if min_salary is not None:
        filtered_df = filtered_df[
            filtered_df["max_annual_salary"] >= min_salary
        ]

    # 최대 희망 연봉
    if max_salary is not None:
        filtered_df = filtered_df[
            filtered_df["min_annual_salary"] <= max_salary
        ]

    # 마감일 시작
    if deadline_start is not None:
        deadline_start_ts = pd.Timestamp(deadline_start)

        filtered_df = filtered_df[
            filtered_df["deadline_date"] >= deadline_start_ts
        ]

    # 마감일 종료
    if deadline_end is not None:
        deadline_end_ts = pd.Timestamp(deadline_end)

        filtered_df = filtered_df[
            filtered_df["deadline_date"] <= deadline_end_ts
        ]

    return filtered_df.reset_index(drop=True)


def get_filter_options(df: pd.DataFrame) -> dict:
    """
    Streamlit 필터에서 사용할 선택지 목록을 반환합니다.
    """

    def unique_values(column: str) -> list[str]:
        if column not in df.columns:
            return []

        return sorted(
            df[column]
            .dropna()
            .astype(str)
            .loc[lambda x: x.str.strip() != ""]
            .unique()
            .tolist()
        )

    return {
        "providers": unique_values("recruit_provider"),
        "careers": unique_values("career"),
        "educations": unique_values("education"),
    }


def load_quality_report() -> dict:
    """
    품질검증 Reporting JSON을 불러옵니다.
    """

    report_path = REPORT_DIR / "quality_report.json"

    with open(
        report_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_quality_rule_summary() -> pd.DataFrame:
    """
    품질 규칙별 오류 요약 CSV를 불러옵니다.
    """

    report_path = REPORT_DIR / "quality_rule_summary.csv"

    return pd.read_csv(
        report_path,
        encoding="utf-8-sig",
    )


def load_missing_value_summary() -> pd.DataFrame:
    """
    컬럼별 결측치 요약 CSV를 불러옵니다.
    """

    report_path = REPORT_DIR / "missing_value_summary.csv"

    return pd.read_csv(
        report_path,
        encoding="utf-8-sig",
    )


def get_career_group_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    세부 경력 조건을 4개 대표 그룹으로 묶어 공고 수를 계산합니다.
    """

    def classify_career(value: object) -> str:
        if pd.isna(value):
            return "미상"

        career = str(value).strip()

        if not career:
            return "미상"

        if career == "경력무관":
            return "경력무관"

        if career == "신입":
            return "신입"

        if career.startswith("신입/경력"):
            return "신입/경력"

        if career.startswith("경력"):
            return "경력"

        return career

    career_group = df["career"].map(classify_career)

    return (
        career_group
        .value_counts()
        .rename_axis("경력")
        .reset_index(name="공고 수")
    )