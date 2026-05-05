import pandas as pd
import numpy as np


def detect_outliers(df: pd.DataFrame) -> list:
    """Find values that are way outside the normal range using IQR method."""
    findings = []
    
    for col in df.select_dtypes(include=[np.number]).columns:
        col_data = df[col].dropna()
        if len(col_data) < 10:
            continue
        
        q1 = col_data.quantile(0.25)
        q3 = col_data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
        
        if len(outliers) > 0:
            findings.append({
                "type": "outlier",
                "column": col,
                "outlier_count": int(len(outliers)),
                "outlier_percent": round(float(len(outliers) / len(col_data) * 100), 2),
                "min_outlier": float(outliers.min()),
                "max_outlier": float(outliers.max()),
                "normal_range": [round(float(lower_bound), 2), round(float(upper_bound), 2)]
            })
    
    return findings


def detect_time_shifts(df: pd.DataFrame) -> list:
    """Find sudden spikes or drops in time-based data."""
    findings = []
    
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) == 0:
        for col in df.columns:
            try:
                pd.to_datetime(df[col], errors='raise')
                date_cols = [col]
                df[col] = pd.to_datetime(df[col])
                break
            except (ValueError, TypeError):
                continue
    
    if len(date_cols) == 0:
        return findings
    
    date_col = date_cols[0]
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        try:
            ts = df.set_index(date_col)[col].resample('W').sum()
            if len(ts) < 4:
                continue
            
            rolling_mean = ts.rolling(window=4, min_periods=2).mean()
            rolling_std = ts.rolling(window=4, min_periods=2).std()
            z_scores = (ts - rolling_mean) / rolling_std
            
            spikes = z_scores[z_scores.abs() > 2].dropna()
            
            if len(spikes) > 0:
                biggest = spikes.abs().idxmax()
                findings.append({
                    "type": "time_shift",
                    "column": col,
                    "date": str(biggest)[:10],
                    "value_at_spike": round(float(ts[biggest]), 2),
                    "expected_value": round(float(rolling_mean[biggest]), 2),
                    "direction": "spike" if z_scores[biggest] > 0 else "drop"
                })
        except Exception:
            continue
    
    return findings


def detect_correlations(df: pd.DataFrame) -> list:
    """Find strong correlations between numeric columns."""
    findings = []
    
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return findings
    
    corr_matrix = numeric_df.corr()
    seen_pairs = set()
    
    for col1 in corr_matrix.columns:
        for col2 in corr_matrix.columns:
            if col1 == col2:
                continue
            pair = tuple(sorted([col1, col2]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            corr_value = corr_matrix.loc[col1, col2]
            if abs(corr_value) >= 0.5:
                findings.append({
                    "type": "correlation",
                    "column_1": col1,
                    "column_2": col2,
                    "strength": round(float(corr_value), 3),
                    "direction": "positive" if corr_value > 0 else "negative"
                })
    
    findings.sort(key=lambda x: abs(x["strength"]), reverse=True)
    return findings[:3]


def detect_all(df: pd.DataFrame) -> dict:
    """Run all detection methods and return combined findings."""
    return {
        "outliers": detect_outliers(df),
        "time_shifts": detect_time_shifts(df),
        "correlations": detect_correlations(df)
    }


if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    revenue = np.random.normal(1000, 100, 100)
    revenue[50] = 5000
    
    test_df = pd.DataFrame({
        "date": dates,
        "revenue": revenue,
        "orders": revenue / 50 + np.random.normal(0, 2, 100),
        "returns": np.random.normal(50, 10, 100)
    })
    
    findings = detect_all(test_df)
    
    import json
    print(json.dumps(findings, indent=2))