import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_executive_summary(profile: dict, findings: dict) -> str:
    """Ask Claude to write a 3-sentence executive summary of the data."""
    
    context = json.dumps({
        "profile": profile,
        "findings": findings
    }, indent=2)
    
    prompt = f"""You are a senior data analyst. Below is a structured summary of a CSV file and any anomalies that were detected automatically.

Write a 3-sentence executive summary that a business stakeholder would find useful. Be specific — use real numbers and column names from the data. Mention the most important finding. Do not start with "This dataset..." or "The data...".

Data summary:
{context}

Respond with only the 3-sentence summary, no preamble."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()


def explain_findings(findings: dict) -> list:
    """Ask Claude to explain each anomaly in plain English."""
    
    if not any(findings.values()):
        return []
    
    prompt = f"""You are a senior data analyst. Below is a list of anomalies detected in a dataset. For each one, write a single short sentence (max 20 words) explaining why it might matter to a business user.

Return your answer as a JSON array of strings, in the same order as the findings. Do not include any other text.

Findings:
{json.dumps(findings, indent=2)}

Example response format:
["First explanation here.", "Second explanation here."]"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [text]


def suggest_charts(profile: dict) -> list:
    """Ask Claude to suggest 3 useful charts based on the columns."""
    
    columns_summary = [
        {"name": c["name"], "type": c["type"]}
        for c in profile["columns"]
    ]
    
    prompt = f"""You are a data visualization expert. Below are the columns of a CSV file. Suggest 3 useful charts a business analyst would want to see.

For each chart, return a JSON object with these fields:
- "title": short chart title
- "chart_type": one of "bar", "line", "pie", "scatter"
- "x_column": column name for x-axis
- "y_column": column name for y-axis (or null for pie charts)
- "reason": one sentence on why this chart is useful

Return only a JSON array of 3 chart objects, no other text.

Columns:
{json.dumps(columns_summary, indent=2)}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def suggest_followup_questions(profile: dict, findings: dict, summary: str) -> list:
    """Ask Claude to suggest 3 follow-up questions a business user should ask next."""
    
    context = json.dumps({
        "profile": profile,
        "findings": findings,
        "summary": summary
    }, indent=2)
    
    prompt = f"""You are a senior data analyst. Below is a summary of a dataset that was just analyzed. Suggest 3 specific follow-up questions a business user should ask to dig deeper into this data.

Rules for good questions:
- Each question must be specific to the actual data (mention real column names, time periods, or categories from the dataset)
- Each question should reveal a different angle (e.g., one about trends, one about segments, one about anomalies)
- Questions must be answerable from the data the user has
- Phrase them as a curious analyst would ask them, not as generic templates

Return your answer as a JSON array of 3 strings, no other text.

Example format:
["Why did revenue drop in March compared to February?", "Which product category has the highest profit margin?", "Are returns concentrated in a specific region?"]

Data context:
{context}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


if __name__ == "__main__":
    from profiler import profile_dataframe
    from detector import detect_all
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    revenue = np.random.normal(1000, 100, 100)
    revenue[50] = 5000
    
    test_df = pd.DataFrame({
        "date": dates,
        "revenue": revenue,
        "orders": (revenue / 50 + np.random.normal(0, 2, 100)).astype(int),
        "region": np.random.choice(["West", "East", "Central", "South"], 100)
    })
    
    print("Profiling data...")
    profile = profile_dataframe(test_df)
    
    print("Detecting anomalies...")
    findings = detect_all(test_df)
    
    print("\n" + "="*60)
    print("EXECUTIVE SUMMARY (from Claude)")
    print("="*60)
    summary = generate_executive_summary(profile, findings)
    print(summary)
    
    print("\n" + "="*60)
    print("ANOMALY EXPLANATIONS (from Claude)")
    print("="*60)
    explanations = explain_findings(findings)
    for i, exp in enumerate(explanations, 1):
        print(f"{i}. {exp}")
    
    print("\n" + "="*60)
    print("SUGGESTED CHARTS (from Claude)")
    print("="*60)
    charts = suggest_charts(profile)
    print(json.dumps(charts, indent=2))
    
    print("\n" + "="*60)
    print("SUGGESTED FOLLOW-UP QUESTIONS (from Claude)")
    print("="*60)
    questions = suggest_followup_questions(profile, findings, summary)
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")