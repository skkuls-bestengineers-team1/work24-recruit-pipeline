from __future__ import annotations

import streamlit as st

from backend import (
    get_summary,
    load_data,
)


st.set_page_config(
    page_title="고용24 강남구 채용 대시보드",
    page_icon="💼",
    layout="wide",
)


@st.cache_data(ttl=300)
def get_data():
    return load_data()


# --------------------------------------------------
# 데이터 로드
# --------------------------------------------------
df = get_data()
summary = get_summary(df)


# --------------------------------------------------
# 제목
# --------------------------------------------------
st.title("💼 고용24 강남구 채용 대시보드")

st.caption(
    "고용24 채용공고 데이터를 수집·표준화·품질검증하여 "
    "정상 데이터만 분석한 결과입니다."
)


# --------------------------------------------------
# 수집 조건
# --------------------------------------------------
with st.expander("📌 데이터 수집 조건", expanded=True):
    st.write("- 지역: 서울특별시 강남구")
    st.write("- 연봉: 3,000만원 이상")
    st.write("- 등록일: 2026-07-25 ~ 2026-08-07")
    st.write("- 마감일: 2026-08-07 ~ 2026-09-06")


# --------------------------------------------------
# KPI
# --------------------------------------------------
st.subheader("채용 현황")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="전체 채용공고",
        value=f"{summary['total_postings']:,}건",
    )

with col2:
    st.metric(
        label="채용 기업",
        value=f"{summary['company_count']:,}개",
    )

with col3:
    average_salary = summary["average_salary"]

    st.metric(
        label="평균 제시 연봉",
        value=(
            f"{average_salary:,.0f}만원"
            if average_salary is not None
            else "-"
        ),
    )

with col4:
    st.metric(
        label="7일 이내 마감",
        value=f"{summary['deadline_soon_count']:,}건",
    )


# --------------------------------------------------
# 데이터 미리보기
# --------------------------------------------------
st.subheader("채용공고 미리보기")

display_columns = [
    "company_name",
    "position_title",
    "career",
    "education",
    "annual_salary",
    "location",
    "deadline_date",
]

st.dataframe(
    df[display_columns].head(20),
    use_container_width=True,
    hide_index=True,
)