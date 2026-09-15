import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="어제 박스오피스", layout="wide")

st.title("🎬 어제의 박스오피스 TOP 10")


# --- 1. 날짜 및 API 데이터 불러오기 함수 ---
def get_yesterday_korea():
    """한국 시간(KST) 기준으로 '어제' 날짜를 YYYYMMDD 형식으로 반환합니다."""
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.datetime.now(kst)
    yesterday = now_kst - datetime.timedelta(days=1)
    return yesterday.strftime("%Y%m%d")


def fetch_box_office():
    """KOBIS API를 호출하여 어제 박스오피스 데이터를 가져옵니다."""
    # Streamlit Secrets에서 API 키 불러오기
    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "🔑 API 키가 설정되지 않았습니다. Secrets에 'KOBIS_KEY'를 추가해 주세요."
        )
        return None

    api_key = st.secrets["KOBIS_KEY"]
    target_dt = get_yesterday_korea()

    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_dt}

    try:
        response = requests.get(url, params=params, timeout=10)
        # HTTP 요청 자체가 실패했을 때 예외 발생
        response.raise_for_status()
        data = response.json()

        # API 오류 상자(faultInfo) 체크
        if "faultInfo" in data:
            error_message = data["faultInfo"].get(
                "message", "알 수 없는 오류가 발생했습니다."
            )
            st.error(f"❌ KOBIS API 오류: {error_message}")
            st.warning(
                "💡 **확인해 보세요:** 발급받은 KOBIS API 키가 올바른지, Secrets 설정(KOBIS_KEY)을 다시 확인해 주세요."
            )
            return None

        # 박스오피스 목록 추출
        movie_list = (
            data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
        )

        # 데이터가 비어 있는 경우
        if not movie_list:
            st.warning(
                "⚠️ 조회된 박스오피스 데이터가 없습니다. 해당 날짜의 집계가 아직 완료되지 않았거나 일시적인 데이터 부재일 수 있습니다."
            )
            return None

        return movie_list

    except requests.exceptions.RequestException as e:
        st.error(f"❌ 네트워크 통신 오류가 발생했습니다: {e}")
        st.warning(
            "💡 **확인해 보세요:** 인터넷 연결 상태를 확인하거나 KOBIS 서버 일시 장애일 수 있으니 잠시 후 다시 시도해 주세요."
        )
        return None


# --- 2. 메인 화면 구성 ---
movies = fetch_box_office()

if movies:
    # API에서 넘어오는 문자열 데이터를 숫자형(int)으로 변환
    df = pd.DataFrame(movies)
    df["rank"] = df["rank"].astype(int)
    df["audiCnt"] = df["audiCnt"].astype(int)
    df["audiAcc"] = df["audiAcc"].astype(int)
    df["scrnCnt"] = df["scrnCnt"].astype(int)

    # 🥇 1위 영화 지표 카드 3개 표시
    top1 = df.iloc[0]
    st.subheader(f"🥇 1위 영화: {top1['movieNm']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("어제 관객수", f"{top1['audiCnt']:,} 명")
    col2.metric("누적 관객수", f"{top1['audiAcc']:,} 명")
    col3.metric("스크린수", f"{top1['scrnCnt']:,} 개")

    st.divider()

    # 📊 상위 5개 영화 관객수 막대그래프
    st.subheader("📊 상위 5개 영화 어제 관객수 비교")
    top5_df = df.head(5)[["movieNm", "audiCnt"]].set_index("movieNm")
    st.bar_chart(top5_df)

    st.divider()

    # 📋 전체 TOP 10 박스오피스 표
    st.subheader("📋 어제 박스오피스 전체 순위")

    # 표시할 컬럼 지정 및 이름 변경
    display_df = df[
        ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()
    display_df.columns = [
        "순위",
        "영화명",
        "개봉일",
        "어제 관객수",
        "누적 관객수",
        "스크린수",
    ]

    st.dataframe(display_df, hide_index=True, use_container_width=True)
