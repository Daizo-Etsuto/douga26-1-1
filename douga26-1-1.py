Python 3.13.3 (tags/v3.13.3:6280bb5, Apr  8 2025, 14:47:33) [MSC v.1943 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> import streamlit as st
... import pandas as pd
... 
... st.set_page_config(page_title="動画解説授業一覧", layout="wide")
... 
... # ====== 設定 ======
... EXCEL_PATH = "sample26-1-1.xlsx"  # GitHubに置くなら例: "data/list.xlsx"
... URL_COL_CANDIDATES = ["解説授業", "URL", "リンク", "動画URL", "動画リンク"]
... 
... # 絞り込み列の候補（Excelの列名が違っても拾えるように）
... GRADE_COL_CANDIDATES = ["学年", "年次", "grade", "Grade"]
... UNIT_COL_CANDIDATES = ["単元", "Unit", "unit", "章", "分野", "テーマ"]
... GENRE_COL_CANDIDATES = ["ジャンル", "分野", "カテゴリー", "カテゴリ", "type", "Type"]
... 
... # ====== 共通PW（Streamlit Secrets推奨）======
... # Streamlit Cloud では、App → Settings → Secrets に
... # PASSWORD="xxxx"
... # を入れるのがおすすめです。
... PASSWORD = st.secrets.get("PASSWORD", "1122")  # ローカル用の仮PW
... 
... if "authed" not in st.session_state:
...     st.session_state.authed = False
... 
... if not st.session_state.authed:
...     st.title("ログイン")
...     pw = st.text_input("パスワード", type="password")
...     if st.button("入る"):
...         if pw == PASSWORD:
...             st.session_state.authed = True
...             st.rerun()
...         else:
...             st.error("パスワードが違います")
...     st.stop()
... 
... # ====== 読み込み ======
... @st.cache_data
... def load_excel(path: str) -> dict[str, pd.DataFrame]:
...     xls = pd.ExcelFile(path)
...     return {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
... 
... def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
...     for c in candidates:
...         if c in df.columns:
...             return c
...     return None
... 
... def find_url_col(df: pd.DataFrame) -> str | None:
...     # まず候補名
...     for c in URL_COL_CANDIDATES:
...         if c in df.columns:
...             return c
...     # 次にURLっぽい列を自動推定
...     for c in df.columns:
...         s = df[c].astype(str)
...         if s.str.startswith("http").any():
...             return c
...     return None
... 
... def safe_str(x) -> str:
...     if pd.isna(x):
...         return ""
...     return str(x).strip()
... 
... sheets = load_excel(EXCEL_PATH)
... sheet_names = list(sheets.keys())
... 
... st.title("動画解説授業一覧")
... 
... # ====== 前回見た「タブ（シート）」を記憶 ======
... if "active_sheet" not in st.session_state:
...     st.session_state.active_sheet = sheet_names[0] if sheet_names else ""
... 
... active = st.radio(
    "シート選択",
    sheet_names,
    index=sheet_names.index(st.session_state.active_sheet) if st.session_state.active_sheet in sheet_names else 0,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state.active_sheet = active

df0 = sheets[active].copy()

# ====== 絞り込みUI（学年・単元・ジャンルなど） ======
grade_col = find_col(df0, GRADE_COL_CANDIDATES)
unit_col  = find_col(df0, UNIT_COL_CANDIDATES)
genre_col = find_col(df0, GENRE_COL_CANDIDATES)
url_col   = find_url_col(df0)

# 上部にまとまって表示（スマホでも見やすい）
c1, c2, c3 = st.columns(3)

selected_grade = "すべて"
if grade_col:
    grades = sorted([g for g in df0[grade_col].dropna().astype(str).unique() if g.strip() != ""])
    with c1:
        selected_grade = st.selectbox("学年", ["すべて"] + grades)

selected_unit = "すべて"
if unit_col:
    units = sorted([u for u in df0[unit_col].dropna().astype(str).unique() if u.strip() != ""])
    with c2:
        selected_unit = st.selectbox("単元", ["すべて"] + units)

selected_genre = "すべて"
if genre_col:
    genres = sorted([g for g in df0[genre_col].dropna().astype(str).unique() if g.strip() != ""])
    with c3:
        selected_genre = st.selectbox("ジャンル", ["すべて"] + genres)

# 追加：フリーワード検索
q = st.text_input("検索（例：大問1 / 関数 / 2025-04 など）", value="", placeholder="キーワードを入力")

# ====== 絞り込み適用 ======
df = df0.copy()

if grade_col and selected_grade != "すべて":
    df = df[df[grade_col].astype(str).str.strip() == selected_grade]

if unit_col and selected_unit != "すべて":
    df = df[df[unit_col].astype(str).str.strip() == selected_unit]

if genre_col and selected_genre != "すべて":
    df = df[df[genre_col].astype(str).str.strip() == selected_genre]

if q.strip():
    mask = df.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False))
    df = df[mask.any(axis=1)].copy()

st.caption(f"表示件数：{len(df)}")

# ====== スマホ向けカード表示（URLはボタン） ======
def render_cards(df: pd.DataFrame, url_col: str | None):
    for i, row in df.iterrows():
        # 見出し：日付 / 大問 / 小問 を優先
        title_bits = []
        for key in ["日付", "大問", "小問"]:
            if key in df.columns:
                v = safe_str(row.get(key))
                if v:
                    title_bits.append(v)
        title = " / ".join(title_bits) if title_bits else f"項目 {i+1}"

        with st.container(border=True):
            st.markdown(f"**{title}**")

            # 学年・単元・ジャンルがあれば上に出す
            for key, label, icon in [
                (grade_col, "学年", "🎓"),
                (unit_col,  "単元", "📘"),
                (genre_col, "ジャンル", "🏷️"),
            ]:
                if key and key in df.columns:
                    v = safe_str(row.get(key))
                    if v:
                        st.write(f"{icon} {label}：{v}")

            # その他の列（URLは除外）
            for col in df.columns:
                if col == url_col:
                    continue
                if col in ["日付", "大問", "小問"]:
                    continue
                # すでに表示した絞り込み列は省略
                if col in [grade_col, unit_col, genre_col]:
                    continue

                v = safe_str(row.get(col))
                if v:
                    st.write(f"- {col}: {v}")

            # URL列は「ボタン」
            if url_col and url_col in df.columns:
                url = safe_str(row.get(url_col))
                if url.startswith("http"):
                    st.link_button("▶ 動画を見る", url)
                else:
                    st.caption("動画リンクなし")
            else:
                st.caption("URL列が見つかりません（URL列名を確認してください）")

render_cards(df, url_col)

st.divider()
st.caption("使い方：上で「学年・単元・ジャンル」を選ぶ → 必要なら検索 → 『▶ 動画を見る』")

