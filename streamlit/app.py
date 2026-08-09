"""강남구 채용공고 Streamlit 대시보드.

PostgreSQL에 적재된 채용공고 데이터를 조회하여
채용 현황, 검색, 시장 분석, 데이터 품질 결과를 제공합니다.
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px

# ==================================================
# 차트 색상 팔레트
# ==================================================
SALARY_COLOR = "#6B8AC9"

CAREER_COLORS = [
    "#6E7FA6",
    "#7F91B8",
    "#91A3C8",
    "#A5B5D3",
]

EDUCATION_COLORS = [
    "#5F8F8A",
    "#6F9D98",
    "#81AAA5",
    "#94B7B2",
    "#A6C3BF",
    "#B9CFCC",
]

PROVIDER_COLORS = [
    "#8B7C98",
    "#9789A4",
    "#A396B0",
    "#AFA3BB",
    "#BBB0C6",
    "#C7BDD0",
]

def apply_chart_style(
    fig,
    height: int = 380,
    show_legend: bool = False,
):
    """Plotly 차트에 대시보드 공통 스타일을 적용한다."""
    fig.update_layout(
        height=height,

        # 배경 투명
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        # 전체 글자
        font=dict(
            color="#C7CEDA",
            size=13,
        ),

        # 범례
        showlegend=show_legend,

        # 그래프 여백
        margin=dict(
            l=35,
            r=35,
            t=25,
            b=40,
        ),

        # hover 박스
        hoverlabel=dict(
            bgcolor="#1B2230",
            font_color="#E5EAF2",
            bordercolor="#3A4454",
        ),
    )

    # x축
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.12)",
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.18)",
        tickfont=dict(
            color="#AAB3C2",
            size=12,
        ),
        title_font=dict(
            color="#B9C1CE",
            size=13,
        ),
    )

    # y축
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.12)",
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.18)",
        tickfont=dict(
            color="#AAB3C2",
            size=12,
        ),
        title_font=dict(
            color="#B9C1CE",
            size=13,
        ),
    )

    return fig

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

st.markdown(
    """
    <style>

    /* 전체 콘텐츠 */
    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* 제목 */
    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em;
        margin-bottom: 0.4rem !important;
    }

    h2 {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        margin-top: 1.8rem !important;
    }

    h3 {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
    width: 285px !important;
    min-width: 285px !important;
    border-right: 1px solid #262c36;
    }

    section[data-testid="stSidebar"] > div {
        width: 285px !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 2.5rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    /* 사이드바 메인 제목 */
    section[data-testid="stSidebar"] h2 {
        font-size: 1.65rem !important;
        font-weight: 750 !important;
        margin-bottom: 0.35rem !important;
    }

    /* 사이드바 설명 */
    section[data-testid="stSidebar"] .stCaption {
        font-size: 1rem !important;
        color: #9CA3AF !important;
        margin-bottom: 1.6rem;
    }

    /* ==================================================
    사이드바 메뉴 버튼
    ================================================== */

    section[data-testid="stSidebar"] .stButton {
        margin-bottom: 0.35rem;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        height: 48px;

        justify-content: flex-start;
        text-align: left;

        padding-left: 1rem;

        border-radius: 9px !important;

        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    /* 선택되지 않은 메뉴 */
    section[data-testid="stSidebar"]
    [data-testid="stBaseButton-secondary"] {
        background: transparent !important;
        border-color: transparent !important;
    }

    /* 선택되지 않은 메뉴 hover */
    section[data-testid="stSidebar"]
    [data-testid="stBaseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: transparent !important;
    }

    /* 선택된 메뉴 */
    section[data-testid="stSidebar"]
    [data-testid="stBaseButton-primary"] {
        font-weight: 700 !important;
    }

    /* KPI */
    [data-testid="stMetric"] {
        background: #151a23;
        border: 1px solid #29313d;
        border-radius: 12px;
        padding: 1rem 1.1rem;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        opacity: 0.75;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
    }

    /* 검색 조건 카드 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: #29313d !important;
    }

    /* 데이터 테이블 */
    [data-testid="stDataFrame"] {
        border: 1px solid #29313d;
        border-radius: 10px;
        overflow: hidden;
    }

    /* 버튼 */
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* 구분선 */
    hr {
        margin-top: 1.8rem !important;
        margin-bottom: 1.8rem !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def get_data():
    """DB 조회 결과를 5분간 캐시하여 반복 조회를 줄인다."""
    return load_data()


# ==================================================
# 공통 데이터 로드 및 요약값 준비
# ==================================================
df = get_data()
summary = get_summary(df)
filter_options = get_filter_options(df)


# ==================================================
# 사이드바 내비게이션
# ==================================================
st.sidebar.markdown("## 강남구 채용 분석")
st.sidebar.caption("고용24 채용공고 데이터 기반")

st.sidebar.divider()

# 최초 접속 시 기본 메뉴
if "menu" not in st.session_state:
    st.session_state["menu"] = "📊 채용 현황"


menu_items = [
    ("📊 채용 현황", "dashboard"),
    ("🔍 채용공고 검색", "search"),
    ("📈 채용시장 분석", "analysis"),
    ("✅ 데이터 품질", "quality"),
]


for label, key in menu_items:

    is_selected = st.session_state["menu"] == label

    if st.sidebar.button(
        label,
        key=f"nav_{key}",
        use_container_width=True,
        type="primary" if is_selected else "secondary",
    ):
        st.session_state["menu"] = label
        st.rerun()


menu = st.session_state["menu"]

# ==================================================
# 1. 채용 현황 페이지
# ==================================================
if menu == "📊 채용 현황":

    st.title("강남구 채용 현황")

    st.caption(
        "고용24 채용공고 데이터를 수집·표준화·품질검증하여 "
        "신뢰할 수 있는 채용 현황을 제공합니다."
    )

    with st.expander("데이터 수집 기준", expanded=False):

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.caption("지역")
            st.write("**서울특별시 강남구**")

        with col2:
            st.caption("연봉")
            st.write("**3,000만원 ~ 10,000만원**")

        with col3:
            st.caption("등록일")
            st.write("**2026.07.25 ~ 08.07**")

        with col4:
            st.caption("마감일")
            st.write("**2026.08.07 ~ 09.06**")

    st.subheader("채용 핵심 지표")

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
# 2. 채용공고 검색 페이지
# ==================================================
elif menu == "🔍 채용공고 검색":

    st.title("채용공고 검색")

    st.caption(
        "원하는 조건을 설정하여 강남구 채용공고를 탐색할 수 있습니다."
    )

    # 검색 필터에서 사용할 연봉 최소/최대값 계산
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

    # 검색 필터에서 사용할 마감일 최소/최대값 계산
    deadline_series = df["deadline_date"].dropna()

    deadline_min = deadline_series.min().date()
    deadline_max = deadline_series.max().date()

    # 검색 조건을 최초 상태로 되돌리는 콜백
    def reset_search_filters():
        """검색 필터를 기본값으로 초기화한다."""
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

    # 검색 조건 입력 영역
    with st.container(border=True):

        st.markdown("### 검색 조건")

        # 검색어
        keyword = st.text_input(
            "기업명 / 공고명",
            placeholder="예: 엔지니어, 마케팅, 데이터",
            key="search_keyword",
        )

        # 선택 필터
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

        # 연봉 범위
        selected_salary = st.slider(
            "연봉 범위 (만원)",
            min_value=salary_min,
            max_value=salary_max,
            value=(salary_min, salary_max),
            step=100,
            key="search_salary",
        )

        # 마감일 범위
        selected_deadline = st.date_input(
            "마감일 범위",
            value=(deadline_min, deadline_max),
            min_value=deadline_min,
            max_value=deadline_max,
            key="search_deadline",
        )

        # 필터 초기화 버튼 - 우측 정렬
        spacer, button_col = st.columns([7, 1])

        with button_col:
            st.button(
                "필터 초기화",
                on_click=reset_search_filters,
                use_container_width=True,
            )

    # date_input 결과를 시작일/종료일로 변환
    if len(selected_deadline) == 2:
        deadline_start = selected_deadline[0]
        deadline_end = selected_deadline[1]
    else:
        deadline_start = None
        deadline_end = None

    # 입력된 검색 조건을 실제 데이터에 적용
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

    st.markdown(
        f"### {len(result_df):,}개의 채용공고를 찾았습니다."
    )

    # 검색 결과 중 사용자에게 보여줄 컬럼만 정리
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

    # 현재 검색 결과를 CSV로 다운로드
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
# 3. 채용시장 분석 페이지
# ==================================================
elif menu == "📈 채용시장 분석":

    st.title("📈 채용시장 분석")

    st.caption(
        "품질검증을 통과한 채용공고를 기준으로 "
        "연봉·경력·학력·채용정보 제공처 분포를 분석합니다."
    )

    # 연봉 분석: 최소/최대 연봉의 중간값을 대표 연봉으로 사용
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
            color_discrete_sequence=[SALARY_COLOR],
        )

        salary_fig.update_layout(
            xaxis_title="대표 연봉 (만원)",
            yaxis_title="",
        )

        salary_fig = apply_chart_style(
            salary_fig,
            height=340,
        )

        salary_fig.update_yaxes(
            showgrid=False,
            showticklabels=False,
        )

        st.plotly_chart(
            salary_fig,
            use_container_width=True,
        )

        st.caption(
            "※ 대표 연봉은 공고별 최소 연봉과 최대 연봉의 평균값으로 계산했습니다."
        )

    st.divider()

    # 경력 및 학력 조건 분포
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💼 경력 조건 분포")

        career_counts = get_career_group_counts(df)

        career_fig = px.bar(
            career_counts,
            x="공고 수",
            y="경력",
            text="공고 수",
            orientation="h",
            color="경력",
            color_discrete_sequence=CAREER_COLORS,
        )

        career_fig.update_layout(
            xaxis_title="공고 수",
            yaxis_title="",
        )

        career_fig.update_traces(
            textposition="outside",
            textfont=dict(
                color="#D5DBE5",
                size=12,
            ),
        )

        career_fig = apply_chart_style(
            career_fig,
            height=380,
        )

        career_fig.update_yaxes(
            showgrid=False,
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
            color="학력",
            color_discrete_sequence=EDUCATION_COLORS,
        )

        education_fig.update_layout(
            xaxis_title="학력 조건",
            yaxis_title="공고 수",
        )

        education_fig.update_traces(
            textposition="outside",
            textfont=dict(
                color="#D5DBE5",
                size=12,
            ),
        )

        education_fig = apply_chart_style(
            education_fig,
            height=380,
        )

        education_fig.update_layout(
            margin=dict(
                l=35,
                r=35,
                t=25,
                b=80,
            )
        )
        st.plotly_chart(
            education_fig,
            use_container_width=True,
        )

    st.divider()

    # 채용정보 제공처별 공고 분포
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
        color="정보제공처",
        color_discrete_sequence=PROVIDER_COLORS,
    )

    provider_fig.update_layout(
        xaxis_title="정보제공처",
        yaxis_title="공고 수",
    )

    provider_fig.update_traces(
        textposition="outside",
        textfont=dict(
            color="#D5DBE5",
            size=12,
        ),
    )

    provider_fig = apply_chart_style(
        provider_fig,
        height=400,
    )

    st.plotly_chart(
        provider_fig,
        use_container_width=True,
    )


# ==================================================
# 4. 데이터 품질 페이지
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

    # 품질검증 핵심 지표
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

    # 품질 규칙별 오류 현황
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

    # 컬럼별 결측치 현황
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
