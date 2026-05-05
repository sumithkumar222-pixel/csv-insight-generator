import pandas as pd
import numpy as np


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Take a pandas DataFrame and return a structured summary."""
    
    profile = {
        "shape": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1])
        },
        "columns": []
    }
    
    for col in df.columns:
        col_data = df[col]
        col_info = {
            "name": col,
            "dtype": str(col_data.dtype),
            "null_count": int(col_data.isnull().sum()),
            "null_percent": round(float(col_data.isnull().sum() / len(df) * 100), 2),
            "unique_count": int(col_data.nunique())
        }
        
        if pd.api.types.is_numeric_dtype(col_data):
            col_info["type"] = "numeric"
            col_info["min"] = float(col_data.min()) if pd.notna(col_data.min()) else None
            col_info["max"] = float(col_data.max()) if pd.notna(col_data.max()) else None
            col_info["mean"] = round(float(col_data.mean()), 2) if pd.notna(col_data.mean()) else None
            col_info["median"] = float(col_data.median()) if pd.notna(col_data.median()) else None
            col_info["std"] = round(float(col_data.std()), 2) if pd.notna(col_data.std()) else None
        
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            col_info["type"] = "datetime"
            col_info["min"] = str(col_data.min())
            col_info["max"] = str(col_data.max())
        
        else:
            col_info["type"] = "categorical"
            top_values = col_data.value_counts().head(5).to_dict()
            col_info["top_values"] = {str(k): int(v) for k, v in top_values.items()}
        
        profile["columns"].append(col_info)
    
    return profile


if __name__ == "__main__":
    test_df = pd.DataFrame({
        "product": ["Pen", "Notebook", "Pen", "Eraser", "Pen", "Notebook"],
        "price": [2.50, 5.00, 2.50, 1.00, 2.50, 5.00],
        "quantity": [10, 5, 20, 30, 15, 8]
    })
    
    result = profile_dataframe(test_df)
    
    import json
    print(json.dumps(result, indent=2))
