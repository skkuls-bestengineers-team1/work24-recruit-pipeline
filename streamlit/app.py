from __future__ import annotations

import streamlit as st
import plotly.express as px

from backend import (
    filter_jobs,
    get_career_group_counts,
    get_filter_options,
    get_summary,
    load_data,
    load_missing_value_summary,
    load_quality_report,
    load_quality_rule_summary,
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

    # --------------------------------------------------
    # 연봉 범위 기본값 계산
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 마감일 범위 기본값 계산
    # --------------------------------------------------
    deadline_series = df["deadline_date"].dropna()

    deadline_min = deadline_series.min().date()
    deadline_max = deadline_series.max().date()

    # --------------------------------------------------
    # 필터 초기화 함수
    # --------------------------------------------------
    def reset_search_filters():
        st.session_state["search_keyword"] = ""
        st.session_state["search_providers"] = []
        st.session_state["search_careers"] = []
        st.session_state["search_educations"] = []

        st.session_state["search_salary"] = (
            salary_min,
            salary_max,
        )

        st.session_state["search_deadline"] = (
            deadline_min,
            deadline_max,
        )

    # --------------------------------------------------
    # 검색어
    # --------------------------------------------------
    keyword = st.text_input(
        "기업명 / 공고명 검색",
        placeholder="예: 엔지니어, 마케팅, 데이터",
        key="search_keyword",
    )

    # --------------------------------------------------
    # 선택 필터
    # --------------------------------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_providers = st.multiselect(
            "정보제공처",
            options=filter_options["providers"],
            format_func=lambda x: x.replace(
                "정보제공처 ",
                "",
            ),
            key="search_providers",
        )

    with col2:
        selected_careers = st.multiselect(
            "경력",
            options=filter_options["careers"],
            key="search_careers",
        )

    with col3:
        selected_educations = st.multiselect(
            "학력",
            options=filter_options["educations"],
            key="search_educations",
        )

    # --------------------------------------------------
    # 연봉 범위
    # --------------------------------------------------
    selected_salary = st.slider(
        "연봉 범위 (만원)",
        min_value=salary_min,
        max_value=salary_max,
        value=(salary_min, salary_max),
        step=100,
        key="search_salary",
    )

    # --------------------------------------------------
    # 마감일 범위
    # --------------------------------------------------
    selected_deadline = st.date_input(
    "마감일 범위",
    value=(deadline_min, deadline_max),
    min_value=deadline_min,
    max_value=deadline_max,
    key="search_deadline",
    )

    if len(selected_deadline) == 2:
        deadline_start = selected_deadline[0]
        deadline_end = selected_deadline[1]
    else:
        deadline_start = None
        deadline_end = None

    # --------------------------------------------------
    # 필터 초기화 버튼
    # --------------------------------------------------
    spacer, button_col = st.columns([7, 1])

    with button_col:
        st.button(
            "🔄 필터 초기화",
            on_click=reset_search_filters,
            use_container_width=True,
        )

    # --------------------------------------------------
    # 필터 적용
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 화면 표시용 데이터
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 검색 결과 CSV 다운로드
    # --------------------------------------------------
    csv_data = display_df.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    st.download_button(
        label="📥 검색 결과 CSV 다운로드",
        data=csv_data,
        file_name="work24_job_search_result.csv",
        mime="text/csv",
    )


# ==================================================
# 3. 채용시장 분석
# ==================================================
elif menu == "📈 채용시장 분석":

    st.title("📈 채용시장 분석")

    st.caption(
        "품질검증을 통과한 채용공고를 기준으로 "
        "연봉·경력·학력·채용정보 제공처 분포를 분석합니다."
    )

    # --------------------------------------------------
    # 연봉 분석
    # --------------------------------------------------
    salary_df = df[
        (df["min_annual_salary"] > 0)
        & (df["max_annual_salary"] > 0)
    ].copy()

    salary_df["salary_mid"] = (
        salary_df["min_annual_salary"]
        + salary_df["max_annual_salary"]
    ) / 2

    st.subheader("💰 연봉 분석")

    if salary_df.empty:
        st.warning("분석 가능한 연봉 데이터가 없습니다.")

    else:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "평균 제시 연봉",
                f"{salary_df['salary_mid'].mean():,.0f}만원",
            )

        with col2:
            st.metric(
                "중앙값 연봉",
                f"{salary_df['salary_mid'].median():,.0f}만원",
            )

        with col3:
            st.metric(
                "최저 제시 연봉",
                f"{salary_df['min_annual_salary'].min():,.0f}만원",
            )

        with col4:
            st.metric(
                "최고 제시 연봉",
                f"{salary_df['max_annual_salary'].max():,.0f}만원",
            )

        salary_fig = px.box(
            salary_df,
            x="salary_mid",
            points="outliers",
            labels={
                "salary_mid": "대표 연봉 (만원)",
            },
        )

        salary_fig.update_layout(
            xaxis_title="대표 연봉 (만원)",
            yaxis_title="",
            showlegend=False,
        )

        st.plotly_chart(
            salary_fig,
            use_container_width=True,
        )

        st.caption(
            "※ 대표 연봉은 공고별 최소 연봉과 최대 연봉의 평균값으로 계산했습니다."
        )

    st.divider()

    # --------------------------------------------------
    # 경력 / 학력
    # --------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💼 경력 조건 분포")

        career_counts = get_career_group_counts(df)

        career_fig = px.bar(
            career_counts,
            x="경력",
            y="공고 수",
            text="공고 수",
        )

        career_fig = px.bar(
        career_counts,
        x="공고 수",
        y="경력",
        text="공고 수",
        orientation="h",
        )

        career_fig.update_layout(
            xaxis_title="공고 수",
            yaxis_title="경력 조건",
        )

        career_fig.update_traces(
            textposition="outside",
        )

        st.plotly_chart(
            career_fig,
            use_container_width=True,
        )

    with col2:
        st.subheader("🎓 학력 조건 분포")

        education_counts = (
            df["education"]
            .fillna("미상")
            .replace("", "미상")
            .value_counts()
            .rename_axis("학력")
            .reset_index(name="공고 수")
        )

        education_fig = px.bar(
            education_counts,
            x="학력",
            y="공고 수",
            text="공고 수",
        )

        education_fig.update_layout(
            xaxis_title="학력 조건",
            yaxis_title="공고 수",
        )

        education_fig.update_traces(
            textposition="outside",
        )

        st.plotly_chart(
            education_fig,
            use_container_width=True,
        )

    st.divider()

    # --------------------------------------------------
    # 정보제공처
    # --------------------------------------------------
    st.subheader("🏢 채용정보 제공처 분포")

    provider_series = (
        df["recruit_provider"]
        .fillna("미상")
        .astype(str)
        .str.replace(
            "정보제공처 ",
            "",
            regex=False,
        )
    )

    provider_counts = (
        provider_series
        .value_counts()
        .rename_axis("정보제공처")
        .reset_index(name="공고 수")
    )

    provider_fig = px.bar(
        provider_counts,
        x="정보제공처",
        y="공고 수",
        text="공고 수",
    )

    provider_fig.update_layout(
        xaxis_title="정보제공처",
        yaxis_title="공고 수",
    )

    provider_fig.update_traces(
        textposition="outside",
    )

    st.plotly_chart(
        provider_fig,
        use_container_width=True,
    )


# ==================================================
# 4. 데이터 품질
# ==================================================
elif menu == "✅ 데이터 품질":

    st.title("✅ 데이터 품질")

    st.caption(
        "수집된 채용공고에 품질 규칙을 적용하여 "
        "정상·오류 데이터를 검증한 결과입니다."
    )

    quality_report = load_quality_report()
    rule_summary_df = load_quality_rule_summary()
    missing_summary_df = load_missing_value_summary()

    summary = quality_report["summary"]

    # ----------------------------------------------
    # 품질 KPI
    # ----------------------------------------------
    st.subheader("품질검증 결과")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "전체 데이터",
            f"{summary['total_count']:,}건",
        )

    with col2:
        st.metric(
            "정상 데이터",
            f"{summary['valid_count']:,}건",
        )

    with col3:
        st.metric(
            "오류 데이터",
            f"{summary['invalid_count']:,}건",
        )

    with col4:
        st.metric(
            "품질률",
            f"{summary['quality_rate']:.1f}%",
        )

    st.divider()

    # ----------------------------------------------
    # 품질 규칙 오류
    # ----------------------------------------------
    st.subheader("품질 규칙별 오류")

    if rule_summary_df.empty:
        st.success(
            "현재 발견된 품질 오류가 없습니다. "
            "모든 데이터가 품질검증을 통과했습니다."
        )

    else:
        display_rule_df = rule_summary_df.rename(
            columns={
                "rule_code": "품질 규칙",
                "issue_count": "오류 건수",
                "affected_row_count": "영향 데이터 수",
            }
        )

        st.dataframe(
            display_rule_df,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ----------------------------------------------
    # 결측치 현황
    # ----------------------------------------------
    st.subheader("컬럼별 결측치 현황")

    display_missing_df = missing_summary_df.rename(
        columns={
            "column_name": "컬럼",
            "missing_count": "결측 건수",
            "missing_rate": "결측률 (%)",
        }
    )

    st.dataframe(
        display_missing_df,
        use_container_width=True,
        hide_index=True,
    )