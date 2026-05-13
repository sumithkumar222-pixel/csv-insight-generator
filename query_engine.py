"""
Query engine for answering natural language questions about a pandas DataFrame.
Uses Claude to generate Pandas code, then runs it safely in a sandbox.
"""

import os
import re
import json
import io
import pandas as pd
import numpy as np
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


FORBIDDEN_PATTERNS = [
    "__import__", "exec(", "eval(", "compile(", "open(", "file(",
    "input(", "globals(", "locals(", "vars(", "getattr(", "setattr(",
    "delattr(", "subprocess", "os.system", "os.popen", "os.remove",
    "os.rmdir", "shutil", "socket", "urllib", "requests", "urlopen",
    "http", "ftplib", "smtplib", "pickle", "marshal", "dill",
    "ctypes", "platform", "sys.exit", "quit(", "exit(",
    "delete", "drop_duplicates(inplace=True)",
    "to_csv(", "to_excel(", "to_pickle(", "to_sql(",
]


def is_safe_code(code: str) -> tuple[bool, str]:
    """Check if the code is safe to execute. Returns (is_safe, reason)."""
    code_lower = code.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in code_lower:
            return False, f"Code contains forbidden pattern: '{pattern}'"
    
    if len(code) > 5000:
        return False, "Code is too long (max 5000 characters)"
    
    return True, ""


def generate_pandas_code(question: str, profile: dict, conversation_history: list) -> dict:
    """Ask Claude to generate Pandas code that answers the user's question."""
    
    columns_info = []
    for col in profile["columns"]:
        info = {"name": col["name"], "type": col["type"]}
        if col["type"] == "numeric":
            info["range"] = f"{col.get('min', 'N/A')} to {col.get('max', 'N/A')}"
        elif col["type"] == "categorical":
            info["sample_values"] = list(col.get("top_values", {}).keys())[:5]
        elif col["type"] == "datetime":
            info["range"] = f"{col.get('min', 'N/A')} to {col.get('max', 'N/A')}"
        columns_info.append(info)
    
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation context:\n"
        for msg in conversation_history[-4:]:
            history_text += f"- {msg['role'].upper()}: {msg['content'][:200]}\n"
    
    prompt = f"""You are a data analyst writing Pandas code to answer a user's question about a dataset.

Dataset columns:
{json.dumps(columns_info, indent=2)}

The DataFrame is already loaded as a variable called `df`. Write Pandas code that answers the user's question.
{history_text}

User's current question: "{question}"

Rules:
1. The DataFrame is named `df`. Do not redefine it.
2. Store your final answer in a variable called `result`.
3. `result` should be a pandas DataFrame, Series, or scalar value (number, string).
4. Keep code under 20 lines.
5. Use only pandas, numpy, and basic Python. No imports, no file I/O, no network calls.
6. If the question is unclear or unanswerable from the data, set `result = "Cannot answer this from the available data"`.
7. Also suggest a chart type for visualizing the result. Options: "bar", "line", "scatter", "pie", "table", "none".

Respond with a JSON object exactly like this (no markdown, no extra text):
{{
  "code": "the pandas code as a single string with \\n for newlines",
  "chart_type": "bar",
  "explanation": "one sentence describing what the code does"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("```").strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"code": "result = 'Could not parse the generated code'", "chart_type": "none", "explanation": ""}


def execute_pandas_code(code: str, df: pd.DataFrame) -> tuple[bool, any, str]:
    """Run Pandas code in a sandbox. Returns (success, result, error_msg)."""
    
    is_safe, reason = is_safe_code(code)
    if not is_safe:
        return False, None, reason
    
    safe_globals = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
    }
    safe_locals = {}
    
    try:
        exec(code, safe_globals, safe_locals)
        result = safe_locals.get("result")
        if result is None:
            return False, None, "Code ran but no 'result' variable was set"
        return True, result, ""
    except Exception as e:
        return False, None, f"Code execution error: {str(e)[:200]}"


def explain_result(question: str, code: str, result: any) -> str:
    """Ask Claude to write a plain-English answer based on the result."""
    
    if isinstance(result, (pd.DataFrame, pd.Series)):
        result_text = result.head(20).to_string()
    else:
        result_text = str(result)
    
    if len(result_text) > 2000:
        result_text = result_text[:2000] + "\n...[truncated]"
    
    prompt = f"""You are a helpful data analyst explaining results to a business user.

The user asked: "{question}"

The following Pandas code was run:
```python
{code}
```

The result was:Write a 2-4 sentence answer that:
- Directly answers the question
- References the specific numbers/values from the result
- Is in plain English (no jargon, no code)
- Sounds like a senior analyst explaining to a stakeholder

Respond with only the answer, no preamble."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()


def answer_question(question: str, df: pd.DataFrame, profile: dict, conversation_history: list = None) -> dict:
    """Main pipeline: question → code → result → explanation."""
    
    if conversation_history is None:
        conversation_history = []
    
    code_response = generate_pandas_code(question, profile, conversation_history)
    code = code_response.get("code", "")
    chart_type = code_response.get("chart_type", "none")
    
    success, result, error = execute_pandas_code(code, df)
    
    if not success:
        return {
            "success": False,
            "answer": f"❌ I had trouble answering that question. {error}\n\nTry rephrasing or asking something more specific.",
            "code": code,
            "result": None,
            "chart_type": "none"
        }
    
    try:
        answer = explain_result(question, code, result)
    except Exception as e:
        answer = f"Here's the result, but I couldn't generate an explanation. Error: {str(e)[:100]}"
    
    return {
        "success": True,
        "answer": answer,
        "code": code,
        "result": result,
        "chart_type": chart_type
    }


if __name__ == "__main__":
    np.random.seed(42)
    test_df = pd.DataFrame({
        "region": np.random.choice(["West", "East", "Central", "South"], 100),
        "revenue": np.random.normal(1000, 200, 100),
        "orders": np.random.randint(1, 50, 100),
        "date": pd.date_range("2024-01-01", periods=100, freq="D")
    })
    
    from profiler import profile_dataframe
    profile = profile_dataframe(test_df)
    
    test_questions = [
        "What's the total revenue by region?",
        "Which region has the highest average order count?",
        "Show me the revenue trend over time"
    ]
    
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"QUESTION: {q}")
        print('='*60)
        response = answer_question(q, test_df, profile)
        print(f"✅ Success: {response['success']}")
        print(f"📝 Answer: {response['answer']}")
        print(f"💻 Code: {response['code']}")
        print(f"📊 Chart: {response['chart_type']}")