from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.models import (
    PipelinePaths,
    ReportResult,
    ValidationResult,
)


# ==================================================
# 전체 품질 요약
# ==================================================
def build_quality_summary(
    validation: ValidationResult,
) -> dict[str, Any]:
    """
    품질검증 결과를 기준으로 전체 데이터 품질 지표를 계산합니다.

    반환값
    ------
    dict
        - total_count: 전체 데이터 수
        - valid_count: 품질검증 통과 데이터 수
        - invalid_count: 하나 이상의 오류가 있는 데이터 수
        - issue_count: 전체 품질 오류 발생 건수
        - quality_rate: 정상 데이터 비율(%)
    """

    # 품질검증 대상 전체 행 수
    total_count = len(validation.row_result_df)

    # 모든 품질 규칙을 통과한 행 수
    valid_count = len(validation.valid_df)

    # 하나 이상의 품질 오류가 발생한 행 수
    invalid_count = len(validation.invalid_df)

    # 행 단위가 아닌 전체 오류 발생 건수
    # 하나의 행에서 여러 규칙을 위반하면 여러 건으로 집계될 수 있음
    issue_count = len(validation.issue_detail_df)

    # 전체 데이터 대비 정상 데이터 비율
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


# ==================================================
# 품질 규칙별 오류 집계
# ==================================================
def build_rule_summary(
    validation: ValidationResult,
) -> pd.DataFrame:
    """
    품질 규칙(rule_code)별 오류 발생 현황을 집계합니다.

    주요 컬럼
    ----------
    issue_count
        해당 품질 규칙에서 발생한 전체 오류 건수

    affected_row_count
        해당 품질 규칙의 영향을 받은 고유 데이터 행 수
    """

    # 품질검증 과정에서 생성된 상세 오류 데이터
    issue_df = validation.issue_detail_df

    # 오류가 없는 경우에도 동일한 컬럼 구조를 유지하여 반환
    if issue_df.empty:
        return pd.DataFrame(
            columns=[
                "rule_code",
                "issue_count",
                "affected_row_count",
            ]
        )

    # 품질 규칙별 전체 오류 건수와 영향을 받은 행 수 집계
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


# ==================================================
# 컬럼별 결측값 집계
# ==================================================
def build_missing_value_summary(
    standardized_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    표준화 데이터의 컬럼별 결측값 현황을 계산합니다.

    NaN뿐 아니라 빈 문자열("")과
    공백만 존재하는 문자열도 결측값으로 처리합니다.
    """

    # 데이터가 비어 있어도 리포트 구조를 유지
    if standardized_df.empty:
        return pd.DataFrame(
            columns=[
                "column_name",
                "missing_count",
                "missing_rate",
            ]
        )

    total_count = len(standardized_df)

    # 각 컬럼의 결측 현황을 저장할 목록
    summary_rows: list[dict[str, Any]] = []

    for column in standardized_df.columns:
        series = standardized_df[column]

        # NaN, 빈 문자열, 공백 문자열을 모두 결측값으로 판정
        missing_mask = (
            series.isna()
            | series.astype("string").str.strip().eq("")
        )

        missing_count = int(missing_mask.sum())

        # 해당 컬럼의 전체 행 대비 결측 비율
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

    # 결측 건수가 많은 컬럼부터 정렬
    return (
        pd.DataFrame(summary_rows)
        .sort_values(
            "missing_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ==================================================
# 그룹별 품질 현황 집계
# ==================================================
def build_group_quality_summary(
    validation: ValidationResult,
    group_column: str,
) -> pd.DataFrame:
    """
    지정한 컬럼을 기준으로 데이터 품질 현황을 집계합니다.

    예
    --
    group_column="location"
        지역별 품질 현황 집계

    group_column="education"
        학력별 품질 현황 집계
    """

    # 행별 품질검증 결과를 복사하여 집계에 사용
    row_result_df = validation.row_result_df.copy()

    # 잘못된 그룹 컬럼명이 전달된 경우 즉시 오류 발생
    if group_column not in row_result_df.columns:
        raise ValueError(
            f"'{group_column}' 컬럼이 데이터에 없습니다."
        )

    # --------------------------------------------------
    # 그룹 컬럼 결측값 처리
    # --------------------------------------------------
    # NaN과 빈 문자열을 동일하게 '(결측)'으로 표시하여
    # groupby 결과에서 누락되지 않도록 처리
    group_series = (
        row_result_df[group_column]
        .astype("string")
        .str.strip()
    )

    row_result_df[group_column] = group_series.mask(
        group_series.isna()
        | group_series.eq(""),
        "(결측)",
    )

    # --------------------------------------------------
    # 그룹별 품질 지표 집계
    # --------------------------------------------------
    grouped_df = (
        row_result_df
        .groupby(
            group_column,
            dropna=False,
        )
        .agg(
            # 그룹에 포함된 전체 데이터 수
            total_count=(
                "source_row_number",
                "size",
            ),

            # 품질검증 통과 데이터 수
            valid_count=(
                "quality_status",
                lambda series: int(
                    series.eq("VALID").sum()
                ),
            ),

            # 품질검증 실패 데이터 수
            invalid_count=(
                "quality_status",
                lambda series: int(
                    series.eq("INVALID").sum()
                ),
            ),

            # 해당 그룹에서 발생한 전체 품질 오류 수
            issue_count=(
                "quality_issue_count",
                "sum",
            ),
        )
        .reset_index()
    )

    # 그룹별 정상 데이터 비율 계산
    grouped_df["quality_rate"] = (
        grouped_df["valid_count"]
        / grouped_df["total_count"]
        * 100
    ).round(2)

    # 데이터 수가 많은 그룹부터 정렬
    return (
        grouped_df
        .sort_values(
            "total_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ==================================================
# 품질 리포트 생성 및 저장
# ==================================================
def generate_reports(
    standardized_df: pd.DataFrame,
    validation: ValidationResult,
    paths: PipelinePaths,
) -> ReportResult:
    """
    표준화 데이터와 품질검증 결과를 이용하여
    데이터 품질 리포트를 생성하고 파일로 저장합니다.

    생성되는 리포트
    ----------------
    - 전체 품질 요약
    - 품질 규칙별 오류 요약
    - 컬럼별 결측값 요약
    - 지역별 품질 요약
    - 학력별 품질 요약
    - 전체 내용을 포함한 JSON 리포트
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
    missing_summary_df = (
        build_missing_value_summary(
            standardized_df
        )
    )

    # --------------------------------------------------
    # 4. 지역별 품질 요약
    # --------------------------------------------------
    location_summary_df = (
        build_group_quality_summary(
            validation,
            "location",
        )
    )

    # --------------------------------------------------
    # 5. 학력별 품질 요약
    # --------------------------------------------------
    education_summary_df = (
        build_group_quality_summary(
            validation,
            "education",
        )
    )

    # --------------------------------------------------
    # 6. 리포트 저장 디렉토리 생성
    # --------------------------------------------------
    # 저장 대상 파일의 상위 디렉토리가 없는 경우 자동 생성
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
    # 7. CSV 리포트 저장
    # --------------------------------------------------

    # 컬럼별 결측값 요약
    missing_summary_df.to_csv(
        paths.missing_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # 품질 규칙별 오류 요약
    rule_summary_df.to_csv(
        paths.rule_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # 현재 PipelinePaths에 이전 프로젝트의 변수명이 남아 있어
    # country_csv 경로를 지역별 품질 리포트 저장 경로로 사용
    location_summary_df.to_csv(
        paths.country_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # inquiry_type_csv 경로를 학력별 품질 리포트 저장 경로로 사용
    education_summary_df.to_csv(
        paths.inquiry_type_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------
    # 8. 통합 JSON 리포트 생성
    # --------------------------------------------------
    # 각 DataFrame을 JSON 직렬화 가능한 list[dict] 형태로 변환
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

    # JSON 파일 저장
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
    print(
        "품질 리포트가 정상적으로 생성되었습니다."
    )
    print("-" * 40)

    # --------------------------------------------------
    # 9. 생성 결과 반환
    # --------------------------------------------------
    # 저장된 리포트와 동일한 데이터를 객체로 반환하여
    # 이후 파이프라인 단계에서도 재사용할 수 있도록 함
    return ReportResult(
        missing_summary=missing_summary_df,
        rule_summary=rule_summary_df,
        country_summary=location_summary_df,
        inquiry_type_summary=education_summary_df,
        payload=payload,
    )