import datetime
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="다른 학교와의 칼로리 비교", page_icon="🍱", layout="wide"
)

st.title("🍱 다른 학교와의 칼로리 비교")
st.caption(
    "송탄고등학교의 급식 칼로리를 기준으로 다른 학교의 급식 칼로리를 비교합니다."
)

# -------------------------------------------------------------------
# 1. API 기본 설정 및 함수 정의
# -------------------------------------------------------------------
BASE_URL = "https://open.neis.go.kr/hub"


@st.cache_data(ttl=3600)
def search_school(school_name: str):
    """학교이름으로 학교 기본정보(SD_SCHUL_CODE, ATPT_OFCDC_SC_CODE)를 검색합니다."""
    url = f"{BASE_URL}/schoolInfo"
    params = {"Type": "json", "pIndex": 1, "pSize": 10, "SCHUL_NM": school_name}
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "schoolInfo" in data:
            return data["schoolInfo"][1]["row"]
    except Exception as e:
        st.error(f"학교 정보 조회 중 오류가 발생했습니다: {e}")
    return []


@st.cache_data(ttl=3600)
def get_meal_info(atpt_code: str, schul_code: str, date_str: str):
    """특정 학교, 날짜의 급식 정보를 가져옵니다."""
    url = f"{BASE_URL}/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_YMD": date_str,
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
    except Exception as e:
        st.error(f"급식 정보 조회 중 오류가 발생했습니다: {e}")
    return []


def parse_calorie(cal_str: str) -> float:
    """'650.5 Kcal' 형식의 문자열에서 숫자만 추출합니다."""
    if not cal_str:
        return 0.0
    cleaned = cal_str.replace("Kcal", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# -------------------------------------------------------------------
# 2. 사이드바 - 기준 학교(송탄고등학교) 및 조회 설정
# -------------------------------------------------------------------
st.sidebar.header("🔍 검색 및 조회 설정")

# 조회 날짜 선택 (기본값: 오늘)
selected_date = st.sidebar.date_input("조회 날짜 선택", datetime.date.today())
date_str = selected_date.strftime("%Y%m%d")

# 기준 학교 설정 (송탄고등학교 자동 조회)
songtan_list = search_school("송탄고등학교")
if not songtan_list:
    st.error("송탄고등학교 정보를 찾을 수 없습니다.")
    st.stop()

songtan_info = songtan_list[0]
songtan_atpt = songtan_info["ATPT_OFCDC_SC_CODE"]
songtan_code = songtan_info["SD_SCHUL_CODE"]

# -------------------------------------------------------------------
# 3. 메인 화면 - 비교 대상 학교 검색
# -------------------------------------------------------------------
st.subheader("1. 비교할 학교 검색")

target_school_name = st.text_input(
    "비교하고 싶은 학교 이름을 입력하세요", value="평택고등학교"
)

target_info = None
if target_school_name:
    search_results = search_school(target_school_name)
    if search_results:
        options = {
            f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})": s for s in search_results
        }
        selected_option = st.selectbox(
            "검색 결과 중 비교할 학교를 선택하세요:", list(options.keys())
        )
        target_info = options[selected_option]
    else:
        st.warning(f"'{target_school_name}'에 대한 검색 결과가 없습니다.")

# -------------------------------------------------------------------
# 4. 급식 데이터 조회 및 비교 Graph 생성
# -------------------------------------------------------------------
if target_info:
    # 송탄고 급식 조회
    songtan_meals = get_meal_info(songtan_atpt, songtan_code, date_str)
    # 비교 학교 급식 조회
    target_meals = get_meal_info(
        target_info["ATPT_OFCDC_SC_CODE"],
        target_info["SD_SCHUL_CODE"],
        date_str,
    )

    st.markdown("---")
    st.subheader(
        f"2. 급식 칼로리 비교 ({selected_date.strftime('%Y년 %m월 %d일')})"
    )

    if not songtan_meals and not target_meals:
        st.info("선택한 날짜에 두 학교 모두 급식 정보가 없습니다.")
    else:
        # 데이터 정리를 위한 리스트
        comparison_data = []

        # 송탄고 데이터 처리
        for m in songtan_meals:
            comparison_data.append(
                {
                    "학교": "송탄고등학교 (기준)",
                    "식사구분": m.get("MMEAL_SC_NM", "급식"),
                    "칼로리(Kcal)": parse_calorie(m.get("CAL_INFO", "")),
                    "메뉴": m.get("DDISH_NM", "").replace("<br/>", "\n"),
                }
            )

        # 비교 학교 데이터 처리
        target_name = target_info["SCHUL_NM"]
        for m in target_meals:
            comparison_data.append(
                {
                    "학교": target_name,
                    "식사구분": m.get("MMEAL_SC_NM", "급식"),
                    "칼로리(Kcal)": parse_calorie(m.get("CAL_INFO", "")),
                    "메뉴": m.get("DDISH_NM", "").replace("<br/>", "\n"),
                }
            )

        df = pd.DataFrame(comparison_data)

        if not df.empty:
            # 막대그래프 그리기
            fig = px.bar(
                df,
                x="식사구분",
                y="칼로리(Kcal)",
                color="학교",
                barmode="group",
                text="칼로리(Kcal)",
                title=f"송탄고등학교 vs {target_name} 칼로리 비교",
                color_discrete_map={
                    "송탄고등학교 (기준)": "#1f77b4",
                    target_name: "#ff7f0e",
                },
            )
            fig.update_traces(texttemplate="%{text:.1f} Kcal", textposition="outside")
            fig.update_layout(yaxis_range=[0, df["칼로리(Kcal)"].max() * 1.2])

            st.plotly_chart(fig, use_container_width=True)

            # 상세 정보 레이아웃 (2개 컬럼)
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🏫 송탄고등학교")
                s_df = df[df["학교"] == "송탄고등학교 (기준)"]
                if not s_df.empty:
                    for _, row in s_df.iterrows():
                        st.metric(
                            label=f"{row['식사구분']} 칼로리",
                            value=f"{row['칼로리(Kcal)']} Kcal",
                        )
                        with st.expander("식단 메뉴 보기"):
                            st.text(row["메뉴"])
                else:
                    st.write("해당 날짜의 급식 정보가 없습니다.")

            with col2:
                st.markdown(f"### 🏫 {target_name}")
                t_df = df[df["학교"] == target_name]
                if not t_df.empty:
                    for _, row in t_df.iterrows():
                        st.metric(
                            label=f"{row['식사구분']} 칼로리",
                            value=f"{row['칼로리(Kcal)']} Kcal",
                        )
                        with st.expander("식단 메뉴 보기"):
                            st.text(row["메뉴"])
                else:
                    st.write("해당 날짜의 급식 정보가 없습니다.")
        else:
            st.warning("표시할 급식 칼로리 데이터가 없습니다.")
