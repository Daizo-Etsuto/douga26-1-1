import streamlit as st
import pandas as pd

st.set_page_config(page_title="動画解説授業一覧", layout="wide")

# ====== 設定 ======
EXCEL_PATH = "sample26-1-1.xlsx"  # GitHubに置くなら例: "data/list.xlsx"
URL_COL_CANDIDATES = ["解説授業", "URL", "リンク", "動画URL", "動画リンク"]

GRADE_COL_CANDIDATES = ["学年", "年次", "grade", "Grade"]
UNIT_COL_CANDIDATES  = ["単元", "Unit", "unit", "章", "分野", "テーマ"]
GENRE_COL_CANDIDATES = ["ジャンル", "分野", "カテゴリー", "カテゴリ", "type", "Type"]

# ====== 共通PW（Secrets推奨）======
PASSWORD = st.secrets.get("PASSWORD", "1122")  # ローカル用の仮PW

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    st.title("ログイン")
    pw = st.text_input("パスワード", type="password")
    if st.button("入る"):
        if pw == PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    st.stop()

# ====== 読み込み ======
@st.cache_data
def load_excel(path: str) -> dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(path)
    return {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}

def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def find_url_col(df: pd.DataFrame) -> str | None:
    for c in URL_COL_CANDIDATES:
        if c in df.columns:
            return c
    for c in df.columns:
        s = df[c].astype(str)
        if s.str.startswith("http").any():
            return c
    return None

def safe_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).str
