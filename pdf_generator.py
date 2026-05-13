"""
PDF report generator for the CSV Insight Generator.
Builds a professional PDF report with summary, anomalies, and metrics.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_pdf_report(
    file_label: str,
    df_rows: int,
    df_cols: int,
    summary: str,
    explanations: list,
    profile: dict,
    chart_suggestions: list,
    followup_questions: list,
    author_name: str = "Sumith Kurapati"
) -> bytes:
    """Generate a polished PDF report from the analysis results. Returns bytes."""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=22,
        spaceAfter=8,
        textColor=HexColor("#1e88e5"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=20,
        textColor=HexColor("#666666"),
        alignment=TA_CENTER,
    )
    
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=14,
        textColor=HexColor("#1e88e5"),
        fontName="Helvetica-Bold",
    )
    
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=10,
        textColor=black,
    )
    
    anomaly_style = ParagraphStyle(
        "Anomaly",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=6,
        textColor=HexColor("#5d4037"),
    )
    
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=HexColor("#999999"),
        alignment=TA_CENTER,
        spaceBefore=20,
    )
    
    story = []
    
    story.append(Paragraph("📊 CSV Insight Report", title_style))
    
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(
        f"<b>Dataset:</b> {file_label}  •  <b>Generated:</b> {timestamp}",
        subtitle_style
    ))
    
    story.append(Paragraph("Executive Summary", section_heading))
    story.append(Paragraph(summary, body_style))
    
    story.append(Paragraph("Key Metrics", section_heading))
    
    metrics_data = [
        ["Metric", "Value"],
        ["Total Rows", f"{df_rows:,}"],
        ["Total Columns", str(df_cols)],
        ["Numeric Columns", str(sum(1 for c in profile["columns"] if c["type"] == "numeric"))],
        ["Categorical Columns", str(sum(1 for c in profile["columns"] if c["type"] == "categorical"))],
        ["Date Columns", str(sum(1 for c in profile["columns"] if c["type"] == "datetime"))],
    ]
    
    metrics_table = Table(metrics_data, colWidths=[2.5 * inch, 2.5 * inch])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e88e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f9f9f9")]),
    ]))
    story.append(metrics_table)
    
    if explanations:
        story.append(Paragraph("Anomalies Detected", section_heading))
        for i, exp in enumerate(explanations, 1):
            story.append(Paragraph(f"<b>{i}.</b> ⚠️ {exp}", anomaly_style))
    else:
        story.append(Paragraph("Anomalies Detected", section_heading))
        story.append(Paragraph("No significant anomalies detected — your data looks clean.", body_style))
    
    if chart_suggestions:
        story.append(Paragraph("Suggested Visualizations", section_heading))
        for chart in chart_suggestions:
            chart_text = f"<b>{chart.get('title', 'Chart')}</b> ({chart.get('chart_type', 'chart')}): {chart.get('reason', '')}"
            story.append(Paragraph(chart_text, body_style))
    
    if followup_questions:
        story.append(Paragraph("Questions to Explore Next", section_heading))
        for i, q in enumerate(followup_questions, 1):
            story.append(Paragraph(f"<b>{i}.</b> {q}", body_style))
    
    story.append(Paragraph("Column Profile", section_heading))
    
    profile_data = [["Column Name", "Type", "Null Count", "Unique Values"]]
    for col in profile["columns"][:25]:
        profile_data.append([
            col["name"][:30],
            col["type"],
            str(col.get("null_count", 0)),
            str(col.get("unique_count", "N/A")),
        ])
    
    profile_table = Table(profile_data, colWidths=[2.2 * inch, 1.2 * inch, 1.0 * inch, 1.2 * inch])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e88e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f9f9f9")]),
    ]))
    story.append(profile_table)
    
    if len(profile["columns"]) > 25:
        story.append(Paragraph(
            f"<i>Showing first 25 of {len(profile['columns'])} columns.</i>",
            ParagraphStyle("Note", parent=body_style, fontSize=8, textColor=HexColor("#999999"))
        ))
    
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        f"Generated by CSV Insight Generator • Built by {author_name}",
        footer_style
    ))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


if __name__ == "__main__":
    test_profile = {
        "columns": [
            {"name": "date", "type": "datetime", "null_count": 0, "unique_count": 100},
            {"name": "revenue", "type": "numeric", "null_count": 2, "unique_count": 95},
            {"name": "region", "type": "categorical", "null_count": 0, "unique_count": 4},
        ]
    }
    
    pdf_bytes = generate_pdf_report(
        file_label="test_data.csv",
        df_rows=100,
        df_cols=3,
        summary="This is a test summary. The data shows a clear trend with revenue averaging $1,025 across regions.",
        explanations=["One outlier detected on day 50 with $5,000 revenue (5x normal)"],
        profile=test_profile,
        chart_suggestions=[
            {"title": "Revenue by Region", "chart_type": "bar", "reason": "Compare regional performance"},
        ],
        followup_questions=[
            "What caused the spike on day 50?",
            "Which region has the highest average revenue?",
        ]
    )
    
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    
    print("✅ Test PDF generated: test_report.pdf")
    print(f"📦 Size: {len(pdf_bytes):,} bytes")