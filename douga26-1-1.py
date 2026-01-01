import base64
import os
from pathlib import Path
import pandas as pd
import streamlit as st

APP_TITLE = "千葉進研 | 問題ダウンロード & 解説"
DATA_PATH = Path("data/index.xlsx")
ASSETS_DIR = Path("assets")

st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")

# --- Simple mobile-friendly CSS ---
st.markdown("""
<style>
/* keep content centered on wide screens */
.block-container {max-width: 1100px; padding-top: 1.2rem; padding-bottom: 3rem;}
/* make buttons fill width on mobile */
div.stDownloadButton > button, div.stLinkButton > a, div.stButton > button {width: 100%;}
/* nicer cards */
.problem-card {border: 1px solid rgba(49,51,63,0.2); border-radius: 14px; padding: 14px 14px; margin-bottom: 12px;}
.problem-meta {opacity: 0.8; font-size: 0.92rem; margin-top: 4px;}
.problem-title {font-weight: 700; font-size: 1.05rem;}
@media (max-width: 640px){
  .block-container {padding-left: 0.9rem; padding-right: 0.9rem;}
}
</style>
""", unsafe_allow_html=True)

def load_index(path: Path) -> dict[str, pd.DataFrame]:
    if not path.exists():
        st.error(f"Index file not found: {path}")
        st.stop()
    xls = pd.ExcelFile(path)
    sheets = {}
    for name in xls.sheet_names:
        df = xls.parse(name)
        # Normalize column names (Japanese variants)
        colmap = {
            "DL問題": "problem_file",
            "DL問題ファイル": "problem_file",
            "DL解答解説": "answer_file",
            "DL解答解説ファイル": "answer_file",
            "DL解答用紙": "sheet_file",
            "解答用紙ファイル": "sheet_file",
            "分類１": "c1",
            "分類２": "c2",
            "分類３": "c3",
            "分類４": "c4",
            "分類５": "c5",
        }
        df = df.rename(columns={k:v for k,v in colmap.items() if k in df.columns})
        # Add optional columns if missing
        for c in ["video_url", "explain_md"]:
            if c not in df.columns:
                df[c] = None
        sheets[name] = df
    return sheets

def file_bytes(p: Path) -> bytes | None:
    try:
        return p.read_bytes()
    except Exception:
        return None

def pdf_viewer(pdf_bytes: bytes, height: int = 700):
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    # inline PDF viewer
    html = f"""
    <iframe
      src="data:application/pdf;base64,{b64}"
      width="100%"
      height="{height}"
      style="border:none; border-radius: 12px;"
    ></iframe>
    """
    st.components.v1.html(html, height=height, scrolling=True)

sheets = load_index(DATA_PATH)

st.title("📘 問題ダウンロード & 解説")
st.caption("ブラウザで「問題→解説→動画」の順に学べます。スマホOK。")

with st.sidebar:
    st.header("絞り込み")
    sheet_name = st.selectbox("年度/シート", list(sheets.keys()), index=0)
    df = sheets[sheet_name].copy()

    # Parse date if present
    if "c2" in df.columns:
        df["date"] = pd.to_datetime(df["c2"], errors="coerce")
    else:
        df["date"] = pd.NaT

    # Filters
    keyword = st.text_input("キーワード（例：小問集合 / 図形）", "")
    c5_vals = sorted([x for x in df.get("c5", pd.Series(dtype=object)).dropna().unique().tolist() if str(x).strip() != ""])
    c5 = st.multiselect("分類５", c5_vals, default=[])

    show_only_available = st.toggle("ファイルがあるものだけ表示", value=True)

# Apply filters
fdf = df.copy()
if keyword.strip():
    key = keyword.strip().lower()
    fdf = fdf[fdf.astype(str).apply(lambda r: r.str.lower().str.contains(key, na=False)).any(axis=1)]
if c5:
    fdf = fdf[fdf["c5"].isin(c5)]
if show_only_available:
    # keep rows where at least one file name is present
    def has_any(row):
        for c in ["problem_file","answer_file","sheet_file"]:
            v = row.get(c)
            if isinstance(v, str) and v.strip() and v.strip().lower() != "なし":
                return True
        return False
    fdf = fdf[fdf.apply(has_any, axis=1)]

# Sort: newest first, then numbers if present
if "date" in fdf.columns:
    fdf = fdf.sort_values(["date","c3","c4"], ascending=[False, True, True], na_position="last")

st.write(f"表示件数：**{len(fdf)}**")

# Helper to build expected asset path
def resolve_asset(year_folder: str, filename: str) -> Path:
    return ASSETS_DIR / year_folder / filename

year_guess = "2025" if "2025" in sheet_name else ("2024" if "2024" in sheet_name else sheet_name)

for i, row in fdf.reset_index(drop=True).iterrows():
    c1 = row.get("c1", "")
    date = row.get("date")
    no1 = row.get("c3", "")
    no2 = row.get("c4", "")
    title = row.get("c5", "") or "問題"

    problem_name = row.get("problem_file")
    answer_name = row.get("answer_file")
    sheet_name_file = row.get("sheet_file")

    st.markdown('<div class="problem-card">', unsafe_allow_html=True)

    left, right = st.columns([2.2, 1.0], vertical_alignment="top")

    with left:
        st.markdown(f'<div class="problem-title">{title}</div>', unsafe_allow_html=True)
        meta_parts = []
        if isinstance(c1, str) and c1.strip():
            meta_parts.append(str(c1))
        if pd.notna(date):
            meta_parts.append(date.strftime("%Y-%m-%d"))
        if str(no1).strip() or str(no2).strip():
            meta_parts.append(f"No.{no1}-{no2}")
        st.markdown(f'<div class="problem-meta">{" / ".join(meta_parts)}</div>', unsafe_allow_html=True)

        # Optional Markdown explanation
        explain_md = row.get("explain_md")
        if isinstance(explain_md, str) and explain_md.strip():
            with st.expander("解説（テキスト）"):
                st.markdown(explain_md)

        # Video
        video_url = row.get("video_url")
        if isinstance(video_url, str) and video_url.strip():
            with st.expander("解説動画を見る"):
                st.video(video_url)
                st.link_button("動画を別タブで開く", video_url, use_container_width=True)

    with right:
        st.markdown("**ダウンロード**")
        def dl_button(label: str, fname: str | None, subdir: str = year_guess):
            if not isinstance(fname, str) or not fname.strip() or fname.strip().lower() == "なし":
                st.button(f"{label}（なし）", disabled=True)
                return
            p = resolve_asset(subdir, fname.strip())
            data = file_bytes(p)
            if data is None:
                st.button(f"{label}（未配置）", disabled=True)
                return
            st.download_button(label, data=data, file_name=fname.strip(), use_container_width=True)

        dl_button("問題PDFをDL", problem_name)
        dl_button("解答・解説PDFをDL", answer_name)
        dl_button("解答用紙をDL", sheet_name_file)

        st.markdown("---")
        st.markdown("**ブラウザで読む**")
        # Render answer/explanation PDF in-app if present
        def view_pdf(label: str, fname: str | None, subdir: str = year_guess):
            if not isinstance(fname, str) or not fname.strip() or fname.strip().lower() == "なし":
                st.button(f"{label}（なし）", disabled=True)
                return
            p = resolve_asset(subdir, fname.strip())
            data = file_bytes(p)
            if data is None:
                st.button(f"{label}（未配置）", disabled=True)
                return
            with st.expander(label):
                pdf_viewer(data, height=650)

        view_pdf("解答・解説PDFを表示", answer_name)

    st.markdown("</div>", unsafe_allow_html=True)

st.info("運用メモ：assets/<年度>/ にPDFを置くと自動でボタンが有効になります。index.xlsx に video_url / explain_md 列を追加すると、動画とテキスト解説も表示できます。")
