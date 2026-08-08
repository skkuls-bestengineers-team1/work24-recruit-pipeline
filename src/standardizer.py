from __future__ import annotations

import ast
import re
from datetime import datetime

import pandas as pd


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y.%m.%d %H:%M",
]

TEXT_COLUMNS = [
    "company_name",
    "position_title",
    "recruit_provider",
    "company_category",
    "education",
    "career",
    "location",
    "working_condition",
    "annual_salary",
    "updated_by",
    "created_by",
]


def clean_text_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype("string")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def parse_mixed_datetime(value: str):
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return pd.NaT
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return pd.NaT


def normalize_company_category(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "[]"}:
        return ""

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return ", ".join(
                    str(item).strip() for item in parsed if str(item).strip()
                )
        except (SyntaxError, ValueError):
            pass

    return text


def parse_yearly_salary(value: str) -> dict[str, float | None]:
    text = str(value).strip()
    empty = {
        "min_annual_salary": None,
        "max_annual_salary": None,
        "annual_salary_avg": None,
    }

    if not text or text.lower() in {"nan", "none"}:
        return empty

    amounts = re.findall(r"([\d,]+)\s*만\s*원", text)
    if not amounts:
        return empty

    values = [float(item.replace(",", "")) for item in amounts]
    salary_min = values[0]
    salary_max = values[-1]
    return {
        "min_annual_salary": salary_min,
        "max_annual_salary": salary_max,
        "annual_salary_avg": (salary_min + salary_max) / 2,
    }


def standardize_jobs(
    raw_df: pd.DataFrame,
    references: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    references = references or {}
    dataframe = raw_df.copy()

    if "no" not in dataframe.columns:
        dataframe.insert(0, "no", range(1, len(dataframe) + 1))

    dataframe["source_row_number"] = range(1, len(dataframe) + 1)

    if "company_category" in dataframe.columns:
        dataframe["company_category"] = dataframe["company_category"].map(
            normalize_company_category
        )

    for column in TEXT_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = clean_text_series(dataframe[column])

    if "deadline_date" in dataframe.columns:
        dataframe["deadline_date"] = dataframe["deadline_date"].map(parse_mixed_datetime)
    if "registration_date" in dataframe.columns:
        dataframe["registration_date"] = dataframe["registration_date"].map(
            parse_mixed_datetime
        )

    if "annual_salary" in dataframe.columns:
        parsed = dataframe["annual_salary"].map(parse_yearly_salary)
        parsed_df = pd.DataFrame(list(parsed))

        for column in ["min_annual_salary", "max_annual_salary"]:
            if column not in dataframe.columns:
                dataframe[column] = parsed_df[column]
            else:
                existing = pd.to_numeric(dataframe[column], errors="coerce")
                dataframe[column] = existing.fillna(parsed_df[column])

        dataframe["annual_salary_avg"] = parsed_df["annual_salary_avg"]
    else:
        dataframe["annual_salary_avg"] = pd.NA

    min_salary = pd.to_numeric(dataframe.get("min_annual_salary"), errors="coerce")
    max_salary = pd.to_numeric(dataframe.get("max_annual_salary"), errors="coerce")
    dataframe["min_annual_salary"] = min_salary
    dataframe["max_annual_salary"] = max_salary
    computed_avg = (min_salary + max_salary) / 2
    dataframe["annual_salary_avg"] = dataframe["annual_salary_avg"].fillna(computed_avg)

    mappings = [
        ("company_category", "company_category", "raw_value"),
        ("education", "education", "raw_value"),
        ("career", "career", "raw_value"),
    ]
    for reference_name, left_column, right_column in mappings:
        if reference_name not in references or left_column not in dataframe.columns:
            continue
        dataframe = dataframe.merge(
            references[reference_name],
            how="left",
            left_on=left_column,
            right_on=right_column,
        ).drop(columns=[right_column], errors="ignore")

    for column in ["updated_at", "created_at"]:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")

    dataframe["standardized_at"] = pd.Timestamp.now().floor("s")
    return dataframe
