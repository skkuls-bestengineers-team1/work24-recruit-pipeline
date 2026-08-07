from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

@dataclass(frozen=True)
class ValidationResult:
    valid_df: pd.DataFrame
    invalid_df: pd.DataFrame
    issue_detail_df: pd.DataFrame
    row_result_df: pd.DataFrame