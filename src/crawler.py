import pandas as pd
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re

from requests import Response

BASE_URL = "https://m.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do"

BASE_DIR = Path(__file__).resolve().parent
SAVE_PATH = BASE_DIR / 'data'

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
    "minPay": "3000", #최저 연봉
    "maxPay": "100000", #최고 연봉
    "codeDepth1Info": "11000",
    "codeDepth2Info": "11000",
    "region": "11680",
    "regionParam": "11680",
    "resultCnt": "10",
    "sortField": "DATE",
    "sortOrderBy": "DESC",
    "searchMode": "Y",
    "regDateStdtParam": "20260725", #기준 일자
    "regDateEndtParam": "20260807", #마감 일자 - 최대
    "cloDateStdtParam": "20260807", #등록 일자 - 최소
    "termSearchGbn": "W-2",
    "academicGbnoEdu": "noEdu",
    "siteClcd": "all",
    "pageIndex": 1,
    "currentPageNo": 1, #내비게이터 기준 pageno (!= pageIndex) -> pageIndex 기준으로 작동해서 무시됨
}

def clean_text(text: str) -> str:
    # 연봉에서 /t/t/t/r/r/t/t/r/n 추출되는 것 정제
    return re.sub(r"\s+", " ", text).strip()

def get_page(page: int) -> Response:
    """한 페이지 요청"""

    params = PARAMS.copy()
    params["pageIndex"] = page

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS
    )

    response.raise_for_status()

    return response

def parse_page(html: str) -> BeautifulSoup:
    """BeautifulSoup로 HTML 파싱"""
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    return soup

def extract_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs = []

    titles = soup.select("a.t3_sb")

    for title in titles:
        job = {}

        job["position_title"] = clean_text(title.get_text()) #공고 제목

        row = title.find_parent("tr") #리스트 한 행 접근

        if not row:
            continue

        company = row.select_one("a.cp_name")
        #회사명
        if company:
            job["company_name"] = clean_text(company.get_text())

        # 기업 뱃지
        labels = row.select(".tbl_label")

        job["company_category"] = [
            clean_text(label.get_text())
            for label in labels
        ]

        # 정보제공처
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
            ] #지원자격 / 근무조건 리스트

            job["annual_salary"] = details[0] if len(details) > 0 else None

            # 경력 / 학력 분리
            if len(details) > 1:
                career_edu = details[1].split(maxsplit=1)

                job["career"] = career_edu[0]

                job["education"] = (
                    career_edu[1]
                    if len(career_edu) > 1 else None
                )
            else:
                job["career"] = None
                job["education"] = None

            job["working_condition"] = details[2] if len(details) > 2 else None
            job["location"] = details[3] if len(details) > 3 else None

        # 마감일 / 등록일
        date_info = row.select("p.s1_r")

        if len(date_info) >= 2:
            job["deadline_date"] = clean_text(
                date_info[0].get_text()
            ).replace("마감일 :", "").strip()

            job["registration_date"] = clean_text(
                date_info[1].get_text()
            ).replace("등록일 :", "").strip()

        jobs.append(job)

    print(jobs)

    return jobs

def save_raw(dataframe: pd.DataFrame) -> None:
    """CSV 저장"""
    Path(SAVE_PATH).mkdir(parents=True, exist_ok=True)

    save_path = Path(SAVE_PATH) / "job_information.csv"

    dataframe.to_csv(save_path, index=False, encoding="utf-8-sig")

    print(f"저장 완료 : {SAVE_PATH}")

def crawl()-> pd.DataFrame:
    """전체 페이지 순회 (1-27)"""
    all_jobs = []

    for page in range(1, 28):
        response = get_page(page)
        soup = parse_page(response.text)

        jobs = extract_jobs(soup)

        all_jobs.extend(jobs)

        print(f"{page}페이지 완료")

    job_info_df = pd.DataFrame(all_jobs)

    return job_info_df

def main():

    job_info_df = crawl()
    save_raw(job_info_df)
    # print(job_info_df.columns)
    # print(job_info_df.head(5))

if __name__ == "__main__":
    main()
