from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.models import (
    PipelinePaths,
    ReportResult,
    ValidationResult,
)



def build_quality_summary(
    validation: ValidationResult,
) -> dict[str, Any]:
    """
    품질 검증 결과의 전체 요약 정보를 생성합니다.

    Returns
    -------
    dict
        전체 행 수, 정상 행 수, 오류 행 수,
        전체 오류 발생 건수, 정상률을 포함합니다.
    """

    total_count = len(validation.row_result_df)
    valid_count = len(validation.valid_df)

    # 하나 이상의 오류가 있는 채용공고 수
    invalid_count = len(validation.invalid_df)

    # 발생한 전체 오류 건수
    issue_count = len(validation.issue_detail_df)

    quality_rate = (
        valid_count / total_count * 100
        if total_count > 0
        else 0.0
    )

    return {
        "total_count": total_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "issue_count": issue_count,
        "quality_rate": round(quality_rate, 2),
    }


def build_rule_summary(
    validation: ValidationResult,
) -> pd.DataFrame:
    """
    품질 규칙(rule_code)별 오류 발생 현황을 집계합니다.

    issue_count
        해당 규칙으로 발생한 전체 오류 건수

    affected_row_count
        해당 규칙의 영향을 받은 데이터 행 수
    """

    issue_df = validation.issue_detail_df

    if issue_df.empty:
        return pd.DataFrame(
            columns=[
                "rule_code",
                "issue_count",
                "affected_row_count",
            ]
        )

    rule_summary_df = (
        issue_df
        .groupby("rule_code")
        .agg(
            issue_count=(
                "rule_code",
                "size",
            ),
            affected_row_count=(
                "source_row_number",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            "issue_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return rule_summary_df


def build_missing_value_summary(
    standardized_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    표준화 데이터의 컬럼별 결측값 현황을 계산합니다.

    NaN뿐 아니라 빈 문자열과 공백 문자열도
    결측값으로 처리합니다.
    """
    if standardized_df.empty:
        return pd.DataFrame(
            columns=[
                "column_name",
                "missing_count",
                "missing_rate",
            ]
        )

    total_count = len(standardized_df)

    summary_rows: list[dict[str, Any]] = []

    for column in standardized_df.columns:
        series = standardized_df[column]

        missing_mask = (
            series.isna()
            | series.astype("string").str.strip().eq("")
        )

        missing_count = int(missing_mask.sum())

        missing_rate = (
            missing_count / total_count * 100
            if total_count > 0
            else 0.0
        )

        summary_rows.append(
            {
                "column_name": column,
                "missing_count": missing_count,
                "missing_rate": round(
                    missing_rate,
                    2,
                ),
            }
        )

    return (
        pd.DataFrame(summary_rows)
        .sort_values(
            "missing_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def build_group_quality_summary(
    validation: ValidationResult,
    group_column: str,
) -> pd.DataFrame:
    """
    지정한 컬럼을 기준으로 품질 현황을 집계합니다.

    예
    ----
    group_column="location"
    group_column="education"
    """

    row_result_df = validation.row_result_df.copy()

    if group_column not in row_result_df.columns:
        raise ValueError(
            f"'{group_column}' 컬럼이 데이터에 없습니다."
        )

    # NaN 또는 공백값을 '(결측)'으로 표시
    group_series = (
        row_result_df[group_column]
        .astype("string")
        .str.strip()
    )

    row_result_df[group_column] = group_series.mask(
        group_series.isna() | group_series.eq(""),
        "(결측)",
    )

    grouped_df = (
        row_result_df
        .groupby(
            group_column,
            dropna=False,
        )
        .agg(
            total_count=(
                "source_row_number",
                "size",
            ),
            valid_count=(
                "quality_status",
                lambda series: int(
                    series.eq("VALID").sum()
                ),
            ),
            invalid_count=(
                "quality_status",
                lambda series: int(
                    series.eq("INVALID").sum()
                ),
            ),
            issue_count=(
                "quality_issue_count",
                "sum",
            ),
        )
        .reset_index()
    )

    grouped_df["quality_rate"] = (
        grouped_df["valid_count"]
        / grouped_df["total_count"]
        * 100
    ).round(2)

    return (
        grouped_df
        .sort_values(
            "total_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def generate_reports(
    standardized_df: pd.DataFrame,
    validation: ValidationResult,
    paths: PipelinePaths,
) -> ReportResult:
    """
    표준화 데이터와 품질 검증 결과를 이용하여
    데이터 품질 리포트를 생성하고 파일로 저장합니다.
    """

    # --------------------------------------------------
    # 1. 전체 품질 요약
    # --------------------------------------------------
    quality_summary = build_quality_summary(
        validation
    )

    # --------------------------------------------------
    # 2. 품질 규칙별 오류 요약
    # --------------------------------------------------
    rule_summary_df = build_rule_summary(
        validation
    )

    # --------------------------------------------------
    # 3. 컬럼별 결측값 요약
    # --------------------------------------------------
    missing_summary_df = build_missing_value_summary(
        standardized_df
    )

    # --------------------------------------------------
    # 4. 지역별 품질 요약
    # --------------------------------------------------
    location_summary_df = build_group_quality_summary(
        validation,
        "location",
    )

    # --------------------------------------------------
    # 5. 학력별 품질 요약
    # --------------------------------------------------
    education_summary_df = build_group_quality_summary(
        validation,
        "education",
    )

    # --------------------------------------------------
    # 6. 저장 폴더 생성
    # --------------------------------------------------
    for path in [
        paths.missing_csv,
        paths.rule_csv,
        paths.country_csv,
        paths.inquiry_type_csv,
        paths.quality_json,
    ]:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------
    # 7. CSV 저장
    # --------------------------------------------------
    missing_summary_df.to_csv(
        paths.missing_csv,
        index=False,
        encoding="utf-8-sig",
    )

    rule_summary_df.to_csv(
        paths.rule_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # 현재 models.py에 예전 프로젝트 변수명이 남아 있으므로
    # country_csv 경로에 지역별 품질 요약을 저장합니다.
    location_summary_df.to_csv(
        paths.country_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # inquiry_type_csv 경로에 학력별 품질 요약을 저장합니다.
    education_summary_df.to_csv(
        paths.inquiry_type_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------
    # 8. JSON 리포트 생성
    # --------------------------------------------------
    payload = {
        "summary": quality_summary,
        "rule_summary": json.loads(
            rule_summary_df.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
        "missing_value_summary": json.loads(
            missing_summary_df.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
        "location_summary": json.loads(
            location_summary_df.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
        "education_summary": json.loads(
            education_summary_df.to_json(
                orient="records",
                force_ascii=False,
            )
        ),
    }

    with paths.quality_json.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("-" * 40)
    print("품질 리포트가 정상적으로 생성되었습니다.")
    print("-" * 40)

    # --------------------------------------------------
    # 9. 결과 객체 반환
    # --------------------------------------------------
    return ReportResult(
        missing_summary=missing_summary_df,
        rule_summary=rule_summary_df,
        country_summary=location_summary_df,
        inquiry_type_summary=education_summary_df,
        payload=payload,
    )