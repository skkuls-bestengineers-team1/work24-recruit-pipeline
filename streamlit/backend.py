from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.config_loader import load_database_settings
from src.database import create_postgresql_engine


# ==================================================
# 경로 설정
# ==================================================
# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent

# PostgreSQL 접속 정보가 저장된 환경변수 파일
ENV_PATH = BASE_DIR / "config" / ".env"

# 품질검증 결과 리포트가 저장되는 디렉토리
REPORT_DIR = BASE_DIR / "reports"


# ==================================================
# 채용공고 데이터 조회
# ==================================================
def load_data() -> pd.DataFrame:
    """
    PostgreSQL의 recruit 테이블을 조회하여
    Streamlit에서 사용할 DataFrame으로 반환합니다.

    조회 후 날짜 및 연봉 컬럼의 데이터 타입을
    Streamlit 필터/분석에 적합한 형태로 변환합니다.
    """

    # .env 설정을 읽어 PostgreSQL 연결 정보 생성
    settings = load_database_settings(ENV_PATH)

    # SQLAlchemy Engine 생성
    engine = create_postgresql_engine(settings)

    try:
        # 품질검증을 통과해 최종 적재된 recruit 테이블 조회
        df = pd.read_sql_table(
            table_name="recruit",
            con=engine,
            schema=settings.schema,
        )

    finally:
        # DB 연결 자원 정리
        engine.dispose()

    # --------------------------------------------------
    # 날짜 컬럼 타입 정리
    # --------------------------------------------------
    # DB에서 읽어온 날짜를 pandas datetime 타입으로 변환합니다.
    # utc=True로 파싱한 뒤 timezone 정보를 제거하고 날짜 단위로 정규화합니다.
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

    # --------------------------------------------------
    # 연봉 컬럼 타입 정리
    # --------------------------------------------------
    # 문자열 또는 기타 타입으로 조회될 가능성에 대비해 숫자형으로 변환합니다.
    # 변환할 수 없는 값은 NaN으로 처리합니다.
    for column in [
        "min_annual_salary",
        "max_annual_salary",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


# ==================================================
# 대시보드 KPI 계산
# ==================================================
def get_summary(df: pd.DataFrame) -> dict:
    """
    Streamlit '채용 현황' 페이지 상단에 표시할
    주요 KPI를 계산하여 dictionary 형태로 반환합니다.
    """

    # 전체 채용공고 수
    total_postings = len(df)

    # 중복 기업명을 제외한 채용 기업 수
    company_count = (
        df["company_name"].nunique()
        if "company_name" in df.columns
        else 0
    )

    # --------------------------------------------------
    # 평균 제시 연봉 계산
    # --------------------------------------------------
    # 최소/최대 연봉이 모두 존재하는 공고만 분석 대상으로 사용합니다.
    salary_df = df[
        (df["min_annual_salary"] > 0)
        & (df["max_annual_salary"] > 0)
    ].copy()

    if salary_df.empty:
        average_salary = None

    else:
        # 공고별 최소/최대 연봉의 중간값을 대표 연봉으로 사용
        salary_mid = (
            salary_df["min_annual_salary"]
            + salary_df["max_annual_salary"]
        ) / 2

        # 전체 공고의 대표 연봉 평균
        average_salary = round(
            float(salary_mid.mean()),
            1,
        )

    # --------------------------------------------------
    # 7일 이내 마감 공고 계산
    # --------------------------------------------------
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


# ==================================================
# 채용공고 검색 필터
# ==================================================
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
    Streamlit 검색 페이지에서 입력한 조건에 따라
    채용공고 DataFrame을 필터링합니다.
    """

    # 원본 DataFrame을 변경하지 않도록 복사본 생성
    filtered_df = df.copy()

    # --------------------------------------------------
    # 기업명 / 채용공고명 검색
    # --------------------------------------------------
    if keyword:
        keyword = keyword.strip()

        # 채용공고명에서 검색어 포함 여부 확인
        title_mask = (
            filtered_df["position_title"]
            .fillna("")
            .str.contains(
                keyword,
                case=False,
                regex=False,
            )
        )

        # 기업명에서 검색어 포함 여부 확인
        company_mask = (
            filtered_df["company_name"]
            .fillna("")
            .str.contains(
                keyword,
                case=False,
                regex=False,
            )
        )

        # 공고명 또는 기업명 중 하나라도 검색어를 포함하면 유지
        filtered_df = filtered_df[
            title_mask | company_mask
        ]

    # --------------------------------------------------
    # 정보제공처 필터
    # --------------------------------------------------
    if providers:
        filtered_df = filtered_df[
            filtered_df["recruit_provider"].isin(
                providers
            )
        ]

    # --------------------------------------------------
    # 경력 필터
    # --------------------------------------------------
    if careers:
        filtered_df = filtered_df[
            filtered_df["career"].isin(careers)
        ]

    # --------------------------------------------------
    # 학력 필터
    # --------------------------------------------------
    if educations:
        filtered_df = filtered_df[
            filtered_df["education"].isin(
                educations
            )
        ]

    # --------------------------------------------------
    # 연봉 범위 필터
    # --------------------------------------------------
    # 공고의 연봉 범위가 사용자가 선택한 범위와
    # 하나라도 겹치는 경우 검색 결과에 포함합니다.

    if min_salary is not None:
        filtered_df = filtered_df[
            filtered_df["max_annual_salary"]
            >= min_salary
        ]

    if max_salary is not None:
        filtered_df = filtered_df[
            filtered_df["min_annual_salary"]
            <= max_salary
        ]

    # --------------------------------------------------
    # 마감일 범위 필터
    # --------------------------------------------------
    if deadline_start is not None:
        deadline_start_ts = pd.Timestamp(
            deadline_start
        )

        filtered_df = filtered_df[
            filtered_df["deadline_date"]
            >= deadline_start_ts
        ]

    if deadline_end is not None:
        deadline_end_ts = pd.Timestamp(
            deadline_end
        )

        filtered_df = filtered_df[
            filtered_df["deadline_date"]
            <= deadline_end_ts
        ]

    # 필터링 후 index를 0부터 다시 부여
    return filtered_df.reset_index(drop=True)


# ==================================================
# 검색 필터 선택지 생성
# ==================================================
def get_filter_options(
    df: pd.DataFrame,
) -> dict:
    """
    Streamlit 검색 필터에서 사용할
    정보제공처·경력·학력 선택지 목록을 생성합니다.
    """

    def unique_values(
        column: str,
    ) -> list[str]:
        """
        지정한 컬럼에서 결측값과 빈 문자열을 제외한
        고유값을 정렬하여 반환합니다.
        """

        if column not in df.columns:
            return []

        return sorted(
            df[column]
            .dropna()
            .astype(str)
            .loc[
                lambda x: x.str.strip() != ""
            ]
            .unique()
            .tolist()
        )

    return {
        "providers": unique_values(
            "recruit_provider"
        ),
        "careers": unique_values(
            "career"
        ),
        "educations": unique_values(
            "education"
        ),
    }


# ==================================================
# 데이터 품질 리포트 조회
# ==================================================
def load_quality_report() -> dict:
    """
    전체 품질검증 결과가 저장된
    quality_report.json 파일을 불러옵니다.
    """

    report_path = (
        REPORT_DIR / "quality_report.json"
    )

    with open(
        report_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_quality_rule_summary() -> pd.DataFrame:
    """
    품질 규칙별 오류 건수를 저장한
    quality_rule_summary.csv를 불러옵니다.
    """

    report_path = (
        REPORT_DIR
        / "quality_rule_summary.csv"
    )

    return pd.read_csv(
        report_path,
        encoding="utf-8-sig",
    )


def load_missing_value_summary() -> pd.DataFrame:
    """
    컬럼별 결측치 현황을 저장한
    missing_value_summary.csv를 불러옵니다.
    """

    report_path = (
        REPORT_DIR
        / "missing_value_summary.csv"
    )

    return pd.read_csv(
        report_path,
        encoding="utf-8-sig",
    )


# ==================================================
# 경력 조건 그룹화
# ==================================================
def get_career_group_counts(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    원본 데이터의 세부 경력 조건을
    '경력무관', '신입', '신입/경력', '경력'
    중심의 대표 그룹으로 분류하여 공고 수를 계산합니다.

    채용시장 분석 페이지의 경력 조건 분포 차트에 사용됩니다.
    """

    def classify_career(
        value: object,
    ) -> str:
        """
        개별 경력 값을 대표 경력 그룹으로 변환합니다.
        """

        # 결측값 처리
        if pd.isna(value):
            return "미상"

        career = str(value).strip()

        # 빈 문자열 처리
        if not career:
            return "미상"

        # 경력무관
        if career == "경력무관":
            return "경력무관"

        # 신입
        if career == "신입":
            return "신입"

        # '신입/경력 1년 이상' 등의 값을 하나의 그룹으로 통합
        if career.startswith("신입/경력"):
            return "신입/경력"

        # '경력 1년 이상', '경력 3년 이상' 등을 하나의 그룹으로 통합
        if career.startswith("경력"):
            return "경력"

        # 예상하지 못한 값은 원본 값 그대로 유지
        return career

    # 각 공고의 경력 조건을 대표 그룹으로 변환
    career_group = df["career"].map(
        classify_career
    )

    # 그룹별 공고 수 계산
    return (
        career_group
        .value_counts()
        .rename_axis("경력")
        .reset_index(name="공고 수")
    )