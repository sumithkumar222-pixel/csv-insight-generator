import streamlit as st
import pandas as pd
import plotly.express as px
import json

from profiler import profile_dataframe
from detector import detect_all
from ai import generate_executive_summary, explain_findings, suggest_charts

st.set_page_config(
    page_title="CSV Insight Generator",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 1rem 0 2rem 0;
}
.main-header h1 {
    font-size: 2.5rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.main-header p {
    color: #666;
    font-size: 1.1rem;
}
.insight-box {
    background-color: #f0f7ff;
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #1e88e5;
    margin: 1rem 0;
}
.anomaly-box {
    background-color: #fff8e1;
    padding: 1rem 1.25rem;
    border-radius: 8px;
    border-left: 4px solid #f9a825;
    margin: 0.5rem 0;
}
.footer {
    text-align: center;
    padding: 2rem 0 1rem 0;
    color: #888;
    font-size: 0.9rem;
    border-top: 1px solid #eee;
    margin-top: 3rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📊 CSV Insight Generator</h1>
    <p>Drop a CSV file. Get instant AI-powered insights.</p>
</div>
""", unsafe_allow_html=True)


MAX_FILE_SIZE_MB = 50
MAX_ROWS_FOR_ANALYSIS = 10000


def load_csv_safely(uploaded_file):
    """Try multiple encodings to read the CSV. Returns DataFrame or raises clear error."""
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File is too large ({file_size_mb:.1f} MB). "
            f"Please upload files under {MAX_FILE_SIZE_MB} MB."
        )
    
    for encoding in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=encoding)
            return df
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise ValueError("This CSV file is empty. Please upload a file with data.")
        except pd.errors.ParserError as e:
            raise ValueError(f"Could not parse this file as CSV. Error: {str(e)[:100]}")
    
    raise ValueError(
        "Could not read this file. Try saving it as UTF-8 in Excel or Google Sheets first."
    )


def validate_dataframe(df):
    """Check that the DataFrame is usable for analysis."""
    if df.empty:
        raise ValueError("This CSV has no rows. Please upload a file with data.")
    
    if len(df.columns) == 0:
        raise ValueError("This CSV has no columns. Please check the file format.")
    
    if len(df.columns) == 1:
        st.warning(
            "⚠️ Your CSV only has 1 column. Insights will be limited. "
            "Try a file with more columns for richer analysis."
        )
    
    return df


def auto_detect_dates(df):
    """Try to convert object columns that look like dates to datetime."""
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isna().all():
            continue
        try:
            sample = df[col].dropna().head(50)
            converted = pd.to_datetime(sample, errors='coerce')
            if converted.notna().sum() / len(sample) > 0.8:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        except Exception:
            continue
    return df


def sample_if_large(df):
    """Sample down to MAX_ROWS_FOR_ANALYSIS for speed."""
    if len(df) > MAX_ROWS_FOR_ANALYSIS:
        st.info(
            f"📦 File has {len(df):,} rows. Sampling {MAX_ROWS_FOR_ANALYSIS:,} rows "
            f"randomly for faster analysis."
        )
        return df.sample(n=MAX_ROWS_FOR_ANALYSIS, random_state=42).reset_index(drop=True)
    return df


uploaded_file = st.file_uploader(
    "Upload your CSV file",
    type=["csv"],
    help=f"Drag and drop a CSV file (max {MAX_FILE_SIZE_MB} MB)"
)

if uploaded_file is None and not st.session_state.get("use_sample"):
    st.info("👆 Upload any CSV file to see automatic insights, anomaly detection, and chart suggestions powered by AI.")
    st.markdown("**Try with sample data:**")
    if st.button("📥 Use sample sales data"):
        st.session_state["use_sample"] = True
        st.rerun()

if uploaded_file is not None or st.session_state.get("use_sample"):
    
    try:
        if uploaded_file is not None:
            df = load_csv_safely(uploaded_file)
            file_label = uploaded_file.name
            st.session_state["use_sample"] = False
        else:
            import numpy as np
            np.random.seed(42)
            dates = pd.date_range("2024-01-01", periods=100, freq="D")
            revenue = np.random.normal(1000, 100, 100)
            revenue[50] = 5000
            df = pd.DataFrame({
                "date": dates,
                "revenue": revenue,
                "orders": (revenue / 50 + np.random.normal(0, 2, 100)).astype(int),
                "region": np.random.choice(["West", "East", "Central", "South"], 100)
            })
            file_label = "sample_sales_data.csv"
        
        df = validate_dataframe(df)
        df = auto_detect_dates(df)
        df = sample_if_large(df)
        
        st.success(f"✅ Loaded **{file_label}** — {df.shape[0]:,} rows × {df.shape[1]} columns")
        
        with st.spinner("Analyzing your data..."):
            profile = profile_dataframe(df)
            findings = detect_all(df)
        
        with st.spinner("Generating AI insights (this takes ~20 seconds)..."):
            try:
                summary = generate_executive_summary(profile, findings)
            except Exception as e:
                summary = f"Could not generate summary. Error: {str(e)[:200]}"
            
            try:
                explanations = explain_findings(findings)
            except Exception:
                explanations = []
            
            try:
                chart_suggestions = suggest_charts(profile)
            except Exception:
                chart_suggestions = []
        
        st.markdown("### 📝 Executive summary")
        st.markdown(f'<div class="insight-box">{summary}</div>', unsafe_allow_html=True)
        
        st.markdown("### 📐 Key metrics")
        cols = st.columns(4)
        cols[0].metric("Rows", f"{df.shape[0]:,}")
        cols[1].metric("Columns", df.shape[1])
        
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) > 0:
            cols[2].metric(f"Total {numeric_cols[0]}", f"{df[numeric_cols[0]].sum():,.0f}")
        else:
            cols[2].metric("Numeric columns", 0)
        if len(numeric_cols) > 1:
            cols[3].metric(f"Avg {numeric_cols[1]}", f"{df[numeric_cols[1]].mean():,.1f}")
        else:
            text_cols = df.select_dtypes(include='object').columns
            if len(text_cols) > 0:
                cols[3].metric(f"Unique {text_cols[0]}", df[text_cols[0]].nunique())
        
        if explanations:
            st.markdown("### 🔍 Anomalies detected")
            for exp in explanations:
                st.markdown(f'<div class="anomaly-box">⚠️ {exp}</div>', unsafe_allow_html=True)
        else:
            st.markdown("### 🔍 Anomalies detected")
            st.info("No significant anomalies detected — your data looks clean!")
        
        if chart_suggestions:
            st.markdown("### 📊 Suggested charts")
            for chart in chart_suggestions:
                try:
                    if chart["x_column"] not in df.columns:
                        continue
                    if chart.get("y_column") and chart["y_column"] not in df.columns:
                        continue
                    
                    st.markdown(f"**{chart['title']}** — _{chart['reason']}_")
                    
                    if chart["chart_type"] == "bar":
                        if chart.get("y_column"):
                            agg = df.groupby(chart["x_column"])[chart["y_column"]].sum().reset_index()
                            fig = px.bar(agg, x=chart["x_column"], y=chart["y_column"])
                        else:
                            agg = df[chart["x_column"]].value_counts().reset_index()
                            agg.columns = [chart["x_column"], "count"]
                            fig = px.bar(agg, x=chart["x_column"], y="count")
                    
                    elif chart["chart_type"] == "line":
                        fig = px.line(df, x=chart["x_column"], y=chart["y_column"])
                    
                    elif chart["chart_type"] == "scatter":
                        fig = px.scatter(df, x=chart["x_column"], y=chart["y_column"])
                    
                    elif chart["chart_type"] == "pie":
                        counts = df[chart["x_column"]].value_counts().head(10).reset_index()
                        counts.columns = [chart["x_column"], "count"]
                        fig = px.pie(counts, names=chart["x_column"], values="count")
                    
                    else:
                        continue
                    
                    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
                    st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"Could not render chart '{chart.get('title', 'Untitled')}': {str(e)[:100]}")
        
        with st.expander("🔧 View raw data profile (for technical users)"):
            st.json(profile)
        
        with st.expander("📋 View first 10 rows"):
            st.dataframe(df.head(10), use_container_width=True)
    
    except ValueError as e:
        st.error(f"❌ {str(e)}")
        st.info("Try a different CSV file, or click 'Use sample sales data' to see how the tool works.")
    
    except Exception as e:
        st.error(f"❌ Something unexpected went wrong: {str(e)[:200]}")
        st.info("Please try a different CSV file. If the problem continues, the file may be corrupted.")

st.markdown("""
<div class="footer">
    Built by <strong>Sumith Kurapati</strong>
</div>
""", unsafe_allow_html=True)