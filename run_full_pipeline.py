from __future__ import annotations

import argparse
from pathlib import Path

from src.models import PipelinePaths
from src.pipeline import run_full_pipeline


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / "config" / ".env"

PATHS = PipelinePaths(
    site_dir=BASE_DIR / "site",
    raw_html=BASE_DIR / "data" / "raw" / "job_information_page.html",
    raw_csv=BASE_DIR / "data" / "raw" / "job_information.csv",
    collection_csv=BASE_DIR / "reports" / "collection_summary.csv",
    collection_json=BASE_DIR / "reports" / "collection_summary.json",
    reference_dir=BASE_DIR / "config" / "reference",
    quality_rules=BASE_DIR / "config" / "quality_rules.json",
    standardized_csv=(
        BASE_DIR / "output" / "standardized" / "job_information_standardized.csv"
    ),
    quality_result_csv=(
        BASE_DIR / "output" / "quality" / "job_information_quality_result.csv"
    ),
    valid_csv=BASE_DIR / "output" / "quality" / "job_information_valid.csv",
    invalid_csv=BASE_DIR / "output" / "quality" / "job_information_invalid.csv",
    issue_csv=BASE_DIR / "output" / "quality" / "quality_issue_detail.csv",
    missing_csv=BASE_DIR / "reports" / "missing_value_summary.csv",
    rule_csv=BASE_DIR / "reports" / "quality_rule_summary.csv",
    country_csv=BASE_DIR / "reports" / "quality_by_location.csv",
    inquiry_type_csv=BASE_DIR / "reports" / "quality_by_education.csv",
    quality_json=BASE_DIR / "reports" / "quality_report.json",
    quality_html=BASE_DIR / "reports" / "job_information_report.html",
    execution_json=BASE_DIR / "reports" / "pipeline_execution_summary.json",
    database_json=BASE_DIR / "reports" / "database_load_summary.json",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "고용24 채용공고 크롤링부터 표준화, 품질 검증, "
            "PostgreSQL 적재까지 실행합니다."
        )
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="크롤링을 생략하고 기존 data/raw/job_information.csv를 사용합니다.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    print("-" * 40)
    print("파이프라인 실행이 시작되었습니다.")
    print("-" * 40)

    result = run_full_pipeline(
        paths=PATHS,
        env_path=ENV_PATH,
        skip_crawl=arguments.skip_crawl,
    )
    print("-" * 40)
    print(result)
    print("-" * 40)


if __name__ == "__main__":
    main()
