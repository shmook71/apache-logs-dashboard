import re
import pandas as pd
from sqlalchemy import create_engine

import sys
LOG_PATH = sys.argv[1] if len(sys.argv) > 1 else "logs/app.log"


LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<proto>[^"]+)" (?P<status>\d{3}) (?P<size>\S+)$'
)

def extract_apache_logs(path: str) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            m = LOG_RE.match(line)
            if not m:
                print(f"⚠️ سطر غير مطابق (line {line_no}): {line}")
                continue

            d = m.groupdict()
            d["size"] = int(d["size"]) if d["size"].isdigit() else 0
            d["status"] = int(d["status"])
            rows.append(d)

    return pd.DataFrame(rows)

def transform_apache_logs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("❌ ما انقرأ ولا سطر. تأكدي أن app.log بصيغة Apache.")

    df["timestamp"] = pd.to_datetime(df["ts"], format="%d/%b/%Y:%H:%M:%S %z", errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df["hour"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:00:00")
    df["status_class"] = (df["status"] // 100).astype(int)
    df["is_error"] = df["status"] >= 400

    return df[["timestamp", "ip", "method", "path", "proto", "status", "status_class", "size", "hour", "is_error"]]

def build_kpis(df: pd.DataFrame):
    total_requests = len(df)
    errors_4xx = (df["status_class"] == 4).sum()
    errors_5xx = (df["status_class"] == 5).sum()

    errors = df[df["is_error"]].copy()

    errors_by_path = (
        errors.groupby("path").size()
        .reset_index(name="error_count")
        .sort_values("error_count", ascending=False)
    )

    errors_by_ip = (
        errors.groupby("ip").size()
        .reset_index(name="error_count")
        .sort_values("error_count", ascending=False)
    )

    errors_by_hour = (
        errors.groupby("hour").size()
        .reset_index(name="error_count")
        .sort_values("hour")
    )

    summary = pd.DataFrame([{
        "total_requests": int(total_requests),
        "errors_4xx": int(errors_4xx),
        "errors_5xx": int(errors_5xx),
        "error_rate_pct": round((len(errors) / total_requests) * 100, 2) if total_requests else 0.0
    }])

    return summary, errors_by_path, errors_by_ip, errors_by_hour

def load_and_export(df, summary, errors_by_path, errors_by_ip, errors_by_hour):
    engine = create_engine("sqlite:///apache_logs.db")

    df.to_sql("apache_logs_raw", engine, if_exists="replace", index=False)
    summary.to_sql("summary", engine, if_exists="replace", index=False)
    errors_by_path.to_sql("errors_by_path", engine, if_exists="replace", index=False)
    errors_by_ip.to_sql("errors_by_ip", engine, if_exists="replace", index=False)
    errors_by_hour.to_sql("errors_by_hour", engine, if_exists="replace", index=False)

    summary.to_csv("summary.csv", index=False)
    errors_by_path.to_csv("errors_by_path.csv", index=False)
    errors_by_ip.to_csv("errors_by_ip.csv", index=False)
    errors_by_hour.to_csv("errors_by_hour.csv", index=False)

def run_pipeline():
    df = extract_apache_logs(LOG_PATH)
    df = transform_apache_logs(df)

    summary, errors_by_path, errors_by_ip, errors_by_hour = build_kpis(df)
    load_and_export(df, summary, errors_by_path, errors_by_ip, errors_by_hour)

    print("✅ تم تشغيل Apache Log Pipeline بنجاح")
    print("📄 تم إنشاء: summary.csv و apache_logs.db")

if __name__ == "__main__":
    run_pipeline()
