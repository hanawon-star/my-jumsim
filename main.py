import datetime
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="경기도 학교 급식 칼로리 순위 비교",
    page_icon="🍱",
    layout="wide",
)

st.title("🍱 경기도 학교 급식 칼로리 순위 비교")
st.caption(
    "송탄고등학교와 비교 대상 학교들의 급식 칼로리를 조회하여 순위를 매깁니다."
)

BASE_URL = "https://open.neis.go.kr/hub"
GYEONGGI_CODE = "J10"  # 경기도교육청 코드


@st.cache_data(ttl=3600)
def search_gyeonggi_schools(school_name: str):
    """경기도 내 학교를 검색합니다."""
    url = f"{BASE_URL}/schoolInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 10,
        "ATPT_OFCDC_SC_CODE": GYEONGGI_CODE,
        "SCHUL_NM": school_name,
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "schoolInfo" in data:
            return data["schoolInfo"][1]["row"]
    except Exception as e:
        st.error(f"학교 정보 조회 중 오류: {e}")
    return []


@st.cache_data(ttl=3600)
def get_meal_info(schul_code: str, date_str: str):
    """특정 학교, 날짜의 급식 정보를 가져옵니다."""
    url = f"{BASE_URL}/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": GYEONGGI_CODE,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_YMD": date_str,
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
    except Exception as e:
        st.error(f"급식 정보 조회 중 오류: {e}")
    return []


def parse_calorie(cal_str: str) -> float:
    if not cal_str:
        return 0.0
    cleaned = cal_str.replace("Kcal", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# -------------------------------------------------------------------
# 사이드바 설정
# -------------------------------------------------------------------
st.sidebar.header("🗓️ 날짜 선택")
selected_date = st.sidebar.date_input("조회 날짜", datetime.date.today())
date_str = selected_date.strftime("%Y%m%d")

# 기준 학교 (송탄고)
songtan_list = search_gyeonggi_schools("송탄고등학교")
if not songtan_list:
    st.error("송탄고등학교 정보를 불러올 수 없습니다.")
    st.stop()
songtan_code = songtan_list[0]["SD_SCHUL_CODE"]

# -------------------------------------------------------------------
# 비교할 학교 선택
# -------------------------------------------------------------------
st.subheader("1. 비교할 경기도 내 학교 추가")
default_schools = ["평택고등학교", "신한고등학교", "비전고등학교", "경기외고"]

target_school_input = st.text_input(
    "추가할 학교 이름을 입력하세요", value="평택고등학교"
)
if target_school_input:
    results = search_gyeonggi_schools(target_school_input)
    if results:
        selected_school = st.selectbox(
            "학교 선택:", [f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})" for s in results]
        )
        # 선택한 학교 정보를 세션에 저장하는 로직을 확장해 다중 비교 가능

# -------------------------------------------------------------------
# 칼로리 비교 및 순위 표시
# -------------------------------------------------------------------
st.markdown("---")
st.subheader(f"2. 급식 칼로리 순위 ({selected_date.strftime('%Y-%m-%d')})")

# 예시용 주요 학교 목록과 송탄고 비교
comparison_targets = [
    ("송탄고등학교 (기준)", songtan_code),
]

# 사용자 입력 학교 추가
if target_school_input and results:
    selected_idx = [
        f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})" for s in results
    ].index(selected_school)
    target_info = results[selected_idx]
    if target_info["SD_SCHUL_CODE"] != songtan_code:
        comparison_targets.append(
            (target_info["SCHUL_NM"], target_info["SD_SCHUL_CODE"])
        )

meal_records = []
for name, code in comparison_targets:
    meals = get_meal_info(code, date_str)
    for m in meals:
        meal_records.append(
            {
                "학교": name,
                "식사구분": m.get("MMEAL_SC_NM", "급식"),
                "칼로리(Kcal)": parse_calorie(m.get("CAL_INFO", "")),
            }
        )

if meal_records:
    df = pd.DataFrame(meal_records)

    # 중식 기준 순위 정렬
    lunch_df = (
        df[df["식사구분"] == "중식"]
        .sort_values(by="칼로리(Kcal)", ascending=False)
        .reset_index(drop=True)
    )
    lunch_df["순위"] = lunch_df.index + 1

    st.write("### 🏆 중식 칼로리 순위")
    st.dataframe(lunch_df[["순위", "학교", "칼로리(Kcal)"]], use_container_width=True)

    fig = px.bar(
        lunch_df,
        x="학교",
        y="칼로리(Kcal)",
        color="학교",
        text="칼로리(Kcal)",
        title="중식 칼로리 순위 비교",
    )
    fig.update_traces(texttemplate="%{text:.1f} Kcal", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("해당 날짜에 급식 정보가 없습니다.")
