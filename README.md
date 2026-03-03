# Apache Logs Monitoring Dashboard

An interactive dashboard for analyzing Apache server logs.

## 🚀 Project Overview
This project builds an ETL pipeline using Python to process Apache logs,
store structured results in SQLite, and visualize insights using Streamlit.

## 📊 Features
- Total requests & error rate calculation
- Error analysis (4xx / 5xx)
- Top IP addresses
- Top error paths
- Errors by hour
- Interactive dashboard (Light / Dark mode)

## 🛠 Tech Stack
- Python
- Pandas
- SQLite
- Streamlit
- Plotly

## 🌐 Live Demo
[View Dashboard](PUT_YOUR_STREAMLIT_LINK_HERE)

## 📁 How to Run Locally

```bash
pip install -r requirements.txt
python main.py
streamlit run dashboard.py
