from __future__ import annotations

from typing import Any

import pandas as pd

from src.models import ValidationResult


def is_blank(value: Any) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def validate_jobs(
    standardized_df: pd.DataFrame,
    rules: dict[str, Any],
) -> ValidationResult:
    issues: list[dict[str, Any]] = []

    if "source_row_number" not in standardized_df.columns:
        working_df = standardized_df.copy()
        working_df["source_row_number"] = range(1, len(working_df) + 1)
    else:
        working_df = standardized_df

    duplicate_mask = working_df.duplicated(
        subset=["company_name", "position_title"],
        keep=False,
    )

    def add_issue(
        row: pd.Series,
        rule_code: str,
        column_name: str,
        invalid_value: Any,
        message: str,
    ) -> None:
        issues.append(
            {
                "source_row_number": int(row["source_row_number"]),
                "company_name": str(row.get("company_name", "")),
                "position_title": str(row.get("position_title", "")),
                "rule_code": rule_code,
                "column_name": column_name,
                "invalid_value": "" if pd.isna(invalid_value) else str(invalid_value),
                "error_message": message,
            }
        )

    for row_index, row in working_df.iterrows():
        for required_rule in rules.get("required_fields", []):
            column = required_rule["column"]
            if is_blank(row.get(column)):
                add_issue(
                    row,
                    required_rule["rule_code"],
                    column,
                    row.get(column),
                    required_rule["message"],
                )

        if bool(duplicate_mask.loc[row_index]):
            add_issue(
                row,
                "DUPLICATE_COMPANY_POSITION",
                "company_name",
                f"{row.get('company_name', '')} | {row.get('position_title', '')}",
                "동일한 회사명과 채용공고명이 중복되었습니다.",
            )

        min_salary = row.get("min_annual_salary")
        max_salary = row.get("max_annual_salary")
        if not is_blank(min_salary) and not is_blank(max_salary):
            try:
                if float(min_salary) > float(max_salary):
                    add_issue(
                        row,
                        "INVALID_SALARY_RANGE",
                        "annual_salary",
                        row.get("annual_salary"),
                        "최소 연봉이 최대 연봉보다 큽니다.",
                    )
            except (TypeError, ValueError):
                add_issue(
                    row,
                    "INVALID_SALARY_VALUE",
                    "annual_salary",
                    row.get("annual_salary"),
                    "연봉 숫자 변환에 실패했습니다.",
                )

    issue_df = pd.DataFrame(
        issues,
        columns=[
            "source_row_number",
            "company_name",
            "position_title",
            "rule_code",
            "column_name",
            "invalid_value",
            "error_message",
        ],
    )

    invalid_rows = (
        set(issue_df["source_row_number"].astype(int))
        if not issue_df.empty
        else set()
    )
    row_result_df = working_df.copy()
    row_result_df["quality_status"] = row_result_df["source_row_number"].map(
        lambda value: "INVALID" if int(value) in invalid_rows else "VALID"
    )

    issue_counts = (
        issue_df.groupby("source_row_number").size().to_dict()
        if not issue_df.empty
        else {}
    )
    row_result_df["quality_issue_count"] = row_result_df["source_row_number"].map(
        lambda value: int(issue_counts.get(int(value), 0))
    ).astype("Int64")

    valid_df = row_result_df[row_result_df["quality_status"].eq("VALID")].reset_index(
        drop=True
    )
    invalid_df = row_result_df[
        row_result_df["quality_status"].eq("INVALID")
    ].reset_index(drop=True)

    return ValidationResult(
        valid_df=valid_df,
        invalid_df=invalid_df,
        issue_detail_df=issue_df.sort_values(
            ["source_row_number", "rule_code"]
        ).reset_index(drop=True),
        row_result_df=row_result_df.reset_index(drop=True),
    )
