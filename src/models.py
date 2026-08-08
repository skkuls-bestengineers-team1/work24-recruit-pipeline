from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PipelinePaths:
    site_dir: Path
    raw_html: Path
    raw_csv: Path
    collection_csv: Path
    collection_json: Path
    reference_dir: Path
    quality_rules: Path
    standardized_csv: Path
    quality_result_csv: Path
    valid_csv: Path
    invalid_csv: Path
    issue_csv: Path
    missing_csv: Path
    rule_csv: Path
    country_csv: Path
    inquiry_type_csv: Path
    quality_json: Path
    quality_html: Path
    execution_json: Path
    database_json: Path


@dataclass(frozen=True)
class CrawlResult:
    raw_df: pd.DataFrame
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    valid_df: pd.DataFrame
    invalid_df: pd.DataFrame
    issue_detail_df: pd.DataFrame
    row_result_df: pd.DataFrame


@dataclass(frozen=True)
class ReportResult:
    missing_summary: pd.DataFrame
    rule_summary: pd.DataFrame
    country_summary: pd.DataFrame
    inquiry_type_summary: pd.DataFrame
    payload: dict[str, Any]


@dataclass(frozen=True)
class PipelineResult:
    crawl: CrawlResult | None
    validation: ValidationResult
    report: ReportResult
    database_summary: dict[str, Any] | None
