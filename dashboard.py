import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="Apache Logs Dashboard", layout="wide")

DB_PATH = "apache_logs.db"


# =========================
# Theme Toggle + Styling
# =========================
theme_mode = st.sidebar.radio("🎨 Theme Mode", ["Light", "Dark"], index=0)

if theme_mode == "Dark":
    st.markdown(
        """
        <style>
        .stApp { background-color: #0B1220; color: #E5E7EB; }
        .block-container { padding-top: 1.5rem; }
        [data-testid="stMetric"] {
            background: #111827;
            border: 1px solid rgba(59, 130, 246, 0.25);
            padding: 14px;
            border-radius: 16px;
        }
        [data-testid="stMetricLabel"] { color: #93C5FD; }
        [data-testid="stMetricValue"] { color: #E5E7EB; }
        [data-testid="stMetricDelta"] { color: #A7F3D0; }
        </style>
        """,
        unsafe_allow_html=True
    )
    chart_theme = "plotly_dark"
else:
    st.markdown(
        """
        <style>
        .stApp { background-color: #F6F9FF; color: #0F172A; }
        .block-container { padding-top: 1.5rem; }
        [data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid rgba(37, 99, 235, 0.18);
            padding: 14px;
            border-radius: 16px;
        }
        [data-testid="stMetricLabel"] { color: #1D4ED8; }
        [data-testid="stMetricValue"] { color: #0F172A; }
        </style>
        """,
        unsafe_allow_html=True
    )
    chart_theme = "plotly_white"


@st.cache_data
def load_tables():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    summary = pd.read_sql("SELECT * FROM summary", engine)
    raw = pd.read_sql("SELECT * FROM apache_logs_raw", engine)
    return summary, raw


# =========================
# Header
# =========================
st.title("📊 Apache Logs Monitoring Dashboard")
st.caption("White/Blue Theme • Filters • KPIs • Trends • Alerts")

# Load
try:
    summary, raw = load_tables()
except Exception as e:
    st.error(f"ما قدرت أفتح قاعدة البيانات: {e}")
    st.info("شغّلي أول: python main.py  عشان ينشأ apache_logs.db والجداول.")
    st.stop()

# Make sure types
raw["status"] = raw["status"].astype(int)
raw["status_class"] = (raw["status"] // 100).astype(int)
raw["is_error"] = raw["status"] >= 400

# =========================
# Sidebar Filters
# =========================
st.sidebar.header("🔎 Filters")

status_options = ["All"] + sorted(raw["status"].unique().tolist())
selected_status = st.sidebar.selectbox("Status Code", status_options, index=0)

path_options = ["All"] + sorted(raw["path"].unique().tolist())
selected_path = st.sidebar.selectbox("Path", path_options, index=0)

ip_options = ["All"] + sorted(raw["ip"].unique().tolist())
selected_ip = st.sidebar.selectbox("IP", ip_options, index=0)

top_n = st.sidebar.slider("Top N", min_value=3, max_value=20, value=10)

# Apply filters
df = raw.copy()
if selected_status != "All":
    df = df[df["status"] == int(selected_status)]
if selected_path != "All":
    df = df[df["path"] == selected_path]
if selected_ip != "All":
    df = df[df["ip"] == selected_ip]

# =========================
# KPIs (filtered)
# =========================
total_requests = len(df)
errors_4xx = (df["status_class"] == 4).sum()
errors_5xx = (df["status_class"] == 5).sum()
total_errors = (df["status"] >= 400).sum()

error_rate = (total_errors / total_requests * 100) if total_requests else 0.0
success_rate = 100 - error_rate
most_common_status = int(df["status"].mode().iloc[0]) if total_requests else 0

# Alerts
if errors_5xx >= 3:
    st.error(f"🚨 High Server Errors Detected! 5xx = {errors_5xx}")
elif total_errors >= 3:
    st.warning(f"⚠️ Elevated Errors Detected! Total Errors = {total_errors}")
else:
    st.success("✅ System looks stable for the current filters")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Requests", total_requests)
c2.metric("4xx Errors", int(errors_4xx))
c3.metric("5xx Errors", int(errors_5xx))
c4.metric("Error Rate (%)", round(error_rate, 2))
c5.metric("Success Rate (%)", round(success_rate, 2))

st.caption(f"Most Common Status: **{most_common_status}**")

st.divider()

# =========================
# Status Distribution Pie
# =========================
left, right = st.columns([1, 1])

with left:
    st.subheader("🥧 Status Distribution (2xx / 4xx / 5xx)")
    if total_requests:
        status_dist = df["status_class"].value_counts().reset_index()
        status_dist.columns = ["status_class", "count"]
        status_dist["status_class"] = status_dist["status_class"].astype(str) + "xx"

        fig_pie = px.pie(
            status_dist,
            names="status_class",
            values="count",
            template=chart_theme,
            color_discrete_sequence=["#2563EB", "#93C5FD", "#1E3A8A"]
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("لا توجد بيانات بعد تطبيق الفلاتر.")

with right:
    st.subheader("⏱️ Requests vs Errors by Hour")
    if total_requests:
        by_hour = df.copy()
        by_hour["hour"] = by_hour["hour"].astype(str)

        req_by_hour = by_hour.groupby("hour").size().reset_index(name="requests")
        err_by_hour = by_hour[by_hour["status"] >= 400].groupby("hour").size().reset_index(name="errors")
        merged = pd.merge(req_by_hour, err_by_hour, on="hour", how="left").fillna(0)
        merged = merged.sort_values("hour")

        fig_line = px.line(
            merged,
            x="hour",
            y=["requests", "errors"],
            template=chart_theme
        )
        # ألوان أبيض/أزرق + أحمر للأخطاء
        fig_line.update_traces(line=dict(width=3))
        fig_line.data[0].name = "requests"
        fig_line.data[1].name = "errors"
        # plotly لا يضمن ترتيب الألوان دائماً، لكن هذا غالباً كافي
        st.plotly_chart(fig_line, use_container_width=True)

        st.dataframe(merged, use_container_width=True)
    else:
        st.info("لا توجد بيانات بعد تطبيق الفلاتر.")

st.divider()

# =========================
# Top Error Paths / IPs
# =========================
err_df = df[df["status"] >= 400].copy()

colA, colB = st.columns(2)

with colA:
    st.subheader("🚨 Top Error Paths")
    if len(err_df):
        top_paths = (
            err_df.groupby("path").size()
            .reset_index(name="error_count")
            .sort_values("error_count", ascending=False)
        )
        st.dataframe(top_paths.head(top_n), use_container_width=True)

        fig_bar_paths = px.bar(
            top_paths.head(top_n),
            x="path",
            y="error_count",
            template=chart_theme,
            title=None
        )
        fig_bar_paths.update_traces(marker_color="#2563EB")
        st.plotly_chart(fig_bar_paths, use_container_width=True)
    else:
        st.info("لا توجد أخطاء (4xx/5xx) مع الفلاتر الحالية.")

with colB:
    st.subheader("🧑‍💻 Top Error IPs")
    if len(err_df):
        top_ips = (
            err_df.groupby("ip").size()
            .reset_index(name="error_count")
            .sort_values("error_count", ascending=False)
        )
        st.dataframe(top_ips.head(top_n), use_container_width=True)

        fig_bar_ips = px.bar(
            top_ips.head(top_n),
            x="ip",
            y="error_count",
            template=chart_theme,
            title=None
        )
        fig_bar_ips.update_traces(marker_color="#93C5FD")
        st.plotly_chart(fig_bar_ips, use_container_width=True)
    else:
        st.info("لا توجد أخطاء (4xx/5xx) مع الفلاتر الحالية.")

st.divider()

# =========================
# Raw Logs Preview
# =========================
st.subheader("📄 Raw Logs Preview (Filtered)")
st.dataframe(df.head(30), use_container_width=True)

st.markdown("---")
st.caption("Built with Streamlit + SQLite | Apache Log Monitoring Dashboard")
