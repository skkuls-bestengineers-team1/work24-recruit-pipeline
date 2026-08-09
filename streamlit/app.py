from __future__ import annotations

import streamlit as st

from backend import (
    filter_jobs,
    get_filter_options,
    get_summary,
    load_data,
)


st.set_page_config(
    page_title="강남구 채용 현황 대시보드",
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
filter_options = get_filter_options(df)


# --------------------------------------------------
# 사이드바 메뉴
# --------------------------------------------------
st.sidebar.title("💼 고용24 채용 분석")

menu = st.sidebar.radio(
    "메뉴",
    [
        "📊 채용 현황",
        "🔍 채용공고 검색",
        "📈 채용시장 분석",
        "✅ 데이터 품질",
    ],
)


# ==================================================
# 1. 채용 현황
# ==================================================
if menu == "📊 채용 현황":

    st.title("강남구 채용 현황 대시보드")

    st.caption(
        "고용24 채용공고 데이터를 수집·표준화·품질검증하여 "
        "정상 데이터만 분석한 결과입니다."
    )

    with st.expander("📌 데이터 수집 조건", expanded=True):
        st.write("- 지역: 서울특별시 강남구")
        st.write("- 연봉: 3,000만원 이상")
        st.write("- 등록일: 2026-07-25 ~ 2026-08-07")
        st.write("- 마감일: 2026-08-07 ~ 2026-09-06")

    st.subheader("채용 현황")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "전체 채용공고",
            f"{summary['total_postings']:,}건",
        )

    with col2:
        st.metric(
            "채용 기업",
            f"{summary['company_count']:,}개",
        )

    with col3:
        average_salary = summary["average_salary"]

        st.metric(
            "평균 제시 연봉",
            (
                f"{average_salary:,.0f}만원"
                if average_salary is not None
                else "-"
            ),
        )

    with col4:
        st.metric(
            "7일 이내 마감",
            f"{summary['deadline_soon_count']:,}건",
        )

    st.subheader("채용공고 미리보기")

    preview_df = df[
        [
            "company_name",
            "position_title",
            "career",
            "education",
            "annual_salary",
            "location",
            "deadline_date",
        ]
    ].copy()

    preview_df["deadline_date"] = (
        preview_df["deadline_date"]
        .dt.strftime("%Y-%m-%d")
    )

    preview_df = preview_df.rename(
        columns={
            "company_name": "기업명",
            "position_title": "채용공고",
            "career": "경력",
            "education": "학력",
            "annual_salary": "연봉",
            "location": "근무지역",
            "deadline_date": "마감일",
        }
    )

    st.dataframe(
        preview_df.head(20),
        use_container_width=True,
        hide_index=True,
    )


# ==================================================
# 2. 채용공고 검색
# ==================================================
elif menu == "🔍 채용공고 검색":

    st.title("🔍 채용공고 검색")

    st.caption(
        "기업명이나 공고명을 검색하고 "
        "경력·학력·정보제공처 등의 조건으로 필터링할 수 있습니다."
    )

    # ----------------------------------------------
    # 키워드
    # ----------------------------------------------
    keyword = st.text_input(
        "기업명 / 공고명 검색",
        placeholder="예: 엔지니어, 마케팅, 데이터",
    )

    # ----------------------------------------------
    # 필터
    # ----------------------------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_providers = st.multiselect(
            "정보제공처",
            options=filter_options["providers"],
        )

    with col2:
        selected_careers = st.multiselect(
            "경력",
            options=filter_options["careers"],
        )

    with col3:
        selected_educations = st.multiselect(
            "학력",
            options=filter_options["educations"],
        )

    # ----------------------------------------------
    # 연봉 범위
    # ----------------------------------------------
    salary_df = df[
        (df["min_annual_salary"] > 0)
        & (df["max_annual_salary"] > 0)
    ]

    salary_min = int(
        salary_df["min_annual_salary"].min()
    )

    salary_max = int(
        salary_df["max_annual_salary"].max()
    )

    selected_salary = st.slider(
        "연봉 범위 (만원)",
        min_value=salary_min,
        max_value=salary_max,
        value=(salary_min, salary_max),
        step=100,
    )

    # ----------------------------------------------
    # 마감일 범위
    # ----------------------------------------------
    deadline_series = df["deadline_date"].dropna()

    deadline_min = deadline_series.min().date()
    deadline_max = deadline_series.max().date()

    selected_deadline = st.date_input(
        "마감일 범위",
        value=(deadline_min, deadline_max),
        min_value=deadline_min,
        max_value=deadline_max,
    )

    if len(selected_deadline) == 2:
        deadline_start = selected_deadline[0]
        deadline_end = selected_deadline[1]
    else:
        deadline_start = None
        deadline_end = None

    # ----------------------------------------------
    # 필터 실행
    # ----------------------------------------------
    result_df = filter_jobs(
        df=df,
        keyword=keyword,
        providers=selected_providers,
        careers=selected_careers,
        educations=selected_educations,
        min_salary=selected_salary[0],
        max_salary=selected_salary[1],
        deadline_start=deadline_start,
        deadline_end=deadline_end,
    )

    st.divider()

    st.subheader(
        f"검색 결과: {len(result_df):,}건"
    )

    # ----------------------------------------------
    # 화면 표시용 DataFrame
    # ----------------------------------------------
    display_df = result_df[
        [
            "company_name",
            "position_title",
            "career",
            "education",
            "annual_salary",
            "location",
            "working_condition",
            "deadline_date",
        ]
    ].copy()

    display_df["deadline_date"] = (
        display_df["deadline_date"]
        .dt.strftime("%Y-%m-%d")
    )

    display_df = display_df.rename(
        columns={
            "company_name": "기업명",
            "position_title": "채용공고",
            "career": "경력",
            "education": "학력",
            "annual_salary": "연봉",
            "location": "근무지역",
            "working_condition": "근무조건",
            "deadline_date": "마감일",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


# ==================================================
# 3. 채용시장 분석
# ==================================================
elif menu == "📈 채용시장 분석":

    st.title("📈 채용시장 분석")

    st.caption(
        "정상 채용공고 데이터를 기준으로 "
        "연봉·경력·학력 분포를 분석합니다."
    )

    # ----------------------------------------------
    # 연봉 데이터
    # ----------------------------------------------
    salary_df = df[
        (df["min_annual_salary"] > 0)
        & (df["max_annual_salary"] > 0)
    ].copy()

    salary_df["salary_mid"] = (
        salary_df["min_annual_salary"]
        + salary_df["max_annual_salary"]
    ) / 2

    st.subheader("💰 연봉 분포")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "평균 연봉",
            f"{salary_df['salary_mid'].mean():,.0f}만원",
        )

    with col2:
        st.metric(
            "중앙값 연봉",
            f"{salary_df['salary_mid'].median():,.0f}만원",
        )

    with col3:
        st.metric(
            "최고 제시 연봉",
            f"{salary_df['max_annual_salary'].max():,.0f}만원",
        )

    # Box Plot
    import plotly.express as px

    salary_fig = px.box(
        salary_df,
        x="salary_mid",
        points="outliers",
        labels={
            "salary_mid": "대표 연봉 (만원)"
        },
    )

    salary_fig.update_layout(
        xaxis_title="연봉 (만원)",
        yaxis_title=None,
        showlegend=False,
    )

    st.plotly_chart(
        salary_fig,
        use_container_width=True,
    )

    st.divider()

    # ----------------------------------------------
    # 경력 분포
    # ----------------------------------------------
    st.subheader("💼 경력 조건 분포")

    career_counts = (
        df["career"]
        .fillna("미상")
        .value_counts()
        .reset_index()
    )

    career_counts.columns = [
        "경력",
        "공고 수",
    ]

    career_fig = px.bar(
        career_counts,
        x="경력",
        y="공고 수",
        text="공고 수",
    )

    st.plotly_chart(
        career_fig,
        use_container_width=True,
    )

    st.divider()

    # ----------------------------------------------
    # 학력 분포
    # ----------------------------------------------
    st.subheader("🎓 학력 조건 분포")

    education_counts = (
        df["education"]
        .fillna("미상")
        .value_counts()
        .reset_index()
    )

    education_counts.columns = [
        "학력",
        "공고 수",
    ]

    education_fig = px.bar(
        education_counts,
        x="학력",
        y="공고 수",
        text="공고 수",
    )

    st.plotly_chart(
        education_fig,
        use_container_width=True,
    )


# ==================================================
# 4. 데이터 품질
# ==================================================
elif menu == "✅ 데이터 품질":

    st.title("✅ 데이터 품질")

    st.info(
        "다음 단계에서 품질검증 결과와 "
        "Reporting 데이터를 연결할 예정입니다."
    )