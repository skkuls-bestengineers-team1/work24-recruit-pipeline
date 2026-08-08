from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response


BASE_URL = "https://m.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do"

BASE_DIR = Path(__file__).resolve().parent.parent
SAVE_PATH = BASE_DIR / "data" / "raw"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

PARAMS = {
    "basicSetupYn": "",
    "careerTo": "",
    "keywordJobCd": "",
    "occupation": "",
    "seqNo": "",
    "cloDateEndtParam": "20260906",
    "payGbn": "Y",
    "minPay": "3000",
    "maxPay": "100000",
    "codeDepth1Info": "11000",
    "codeDepth2Info": "11000",
    "region": "11680",
    "regionParam": "11680",
    "resultCnt": "10",
    "sortField": "DATE",
    "sortOrderBy": "DESC",
    "searchMode": "Y",
    "regDateStdtParam": "20260725",
    "regDateEndtParam": "20260807",
    "cloDateStdtParam": "20260807",
    "termSearchGbn": "W-2",
    "academicGbnoEdu": "noEdu",
    "siteClcd": "all",
    "pageIndex": 1,
    "currentPageNo": 1,
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_page(page: int) -> Response:
    params = PARAMS.copy()
    params["pageIndex"] = page

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response


def parse_page(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def extract_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs = []
    titles = soup.select("a.t3_sb")

    for title in titles:
        job = {}
        job["position_title"] = clean_text(title.get_text())

        row = title.find_parent("tr")
        if not row:
            continue

        company = row.select_one("a.cp_name")
        if company:
            job["company_name"] = clean_text(company.get_text())

        labels = row.select(".tbl_label")
        job["company_category"] = [
            clean_text(label.get_text()) for label in labels
        ]

        provider_img = row.select_one("img")
        job["recruit_provider"] = (
            provider_img.get("alt")
            if provider_img and provider_img.get("alt")
            else None
        )

        info = row.select_one("ul.emp_info_dtl")
        if info:
            details = [
                clean_text(li.get_text(" "))
                for li in info.select("li")
            ]

            job["annual_salary"] = details[0] if len(details) > 0 else None

            if len(details) > 1:
                career_edu = details[1].split(maxsplit=1)
                job["career"] = career_edu[0]
                job["education"] = career_edu[1] if len(career_edu) > 1 else None
            else:
                job["career"] = None
                job["education"] = None

            job["working_condition"] = details[2] if len(details) > 2 else None
            job["location"] = details[3] if len(details) > 3 else None

        date_info = row.select("p.s1_r")
        if len(date_info) >= 2:
            job["deadline_date"] = clean_text(
                date_info[0].get_text()
            ).replace("마감일 :", "").strip()
            job["registration_date"] = clean_text(
                date_info[1].get_text()
            ).replace("등록일 :", "").strip()

        jobs.append(job)

    return jobs


def save_raw(dataframe: pd.DataFrame, save_path: Path | None = None) -> Path:
    target_dir = SAVE_PATH if save_path is None else Path(save_path).parent
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = (
        SAVE_PATH / "job_information.csv"
        if save_path is None
        else Path(save_path)
    )
    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"저장 완료 : {output_path}")
    return output_path


def crawl(start_page: int = 1, end_page: int = 27) -> pd.DataFrame:
    all_jobs = []

    for page in range(start_page, end_page + 1):
        response = get_page(page)
        soup = parse_page(response.text)
        jobs = extract_jobs(soup)
        all_jobs.extend(jobs)
        print(f"{page}페이지 완료")

    return pd.DataFrame(all_jobs)


def crawl_jobs(save: bool = True, save_path: Path | None = None) -> pd.DataFrame:
    job_info_df = crawl()
    if save:
        save_raw(job_info_df, save_path=save_path)
    return job_info_df
