from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from google import genai
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
import json
import tempfile
from datetime import datetime

load_dotenv()

app = FastAPI(title="DocuAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Store last extraction in memory
last_extraction = {}

@app.get("/")
def root():
    return {"message": "DocuAgent is running"}


@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    global last_extraction

    contents = await file.read()

    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        mime_type = "application/pdf"
    elif filename.endswith(".png"):
        mime_type = "image/png"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        mime_type = "image/jpeg"
    else:
        return {"error": "Unsupported file type. Use PDF, PNG, or JPG."}

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": contents
                        }
                    },
                    {
                        "text": """Analyze this document and extract the following in JSON format:
                        {
                            "document_type": "invoice/report/form/letter/other",
                            "summary": "brief summary of the document",
                            "key_fields": {
                                "extracted key-value pairs relevant to document type"
                            },
                            "anomalies": ["any unusual or missing fields"],
                            "confidence": "high/medium/low"
                        }
                        Return only valid JSON, nothing else."""
                    }
                ]
            }
        ]
    )

    try:
        raw = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw)
    except:
        result = {"raw_response": response.text}

    # Save to memory for export
    last_extraction = {
        "filename": file.filename,
        "extracted_at": datetime.now().isoformat(),
        "extraction": result
    }

    return last_extraction


@app.get("/export/json")
def export_json():
    if not last_extraction:
        return JSONResponse(
            status_code=404,
            content={"error": "No extraction found. Please extract a document first."}
        )
    return JSONResponse(content=last_extraction)


@app.get("/export/pdf")
def export_pdf():
    if not last_extraction:
        return JSONResponse(
            status_code=404,
            content={"error": "No extraction found. Please extract a document first."}
        )

    # Create temp PDF file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()

    doc = SimpleDocTemplate(
        tmp_path,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── Brand colors
    PURPLE = colors.HexColor("#6c63ff")
    DARK   = colors.HexColor("#1a1d27")
    GRAY   = colors.HexColor("#888888")
    WHITE  = colors.white
    RED    = colors.HexColor("#ff6b6b")

    # ── Custom styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"],
        fontSize=24, textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=GRAY,
        alignment=TA_CENTER, spaceAfter=2
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=13, textColor=WHITE,
        fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#cccccc"),
        leading=16, spaceAfter=8
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=9, textColor=GRAY,
        fontName="Helvetica"
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontSize=9, textColor=WHITE,
        fontName="Helvetica"
    )

    data      = last_extraction
    extracted = data.get("extraction", {})
    doc_type  = extracted.get("document_type", "unknown").upper()
    confidence= extracted.get("confidence", "medium").upper()
    timestamp = data.get("extracted_at", "")[:19].replace("T", " ")

    # ── Header block
    header_data = [[
        Paragraph("📄 DocuAgent", title_style),
    ]]
    header_table = Table(header_data, colWidths=[6.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), DARK),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",   (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 18),
        ("LEFTPADDING",  (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("AI-Powered Document Extraction Report", sub_style))
    elements.append(Spacer(1, 14))

    # ── Meta row (filename | type | confidence | date)
    meta_data = [[
        Paragraph(f"<b>File:</b> {data.get('filename','')}", label_style),
        Paragraph(f"<b>Type:</b> {doc_type}", label_style),
        Paragraph(f"<b>Confidence:</b> {confidence}", label_style),
        Paragraph(f"<b>Date:</b> {timestamp}", label_style),
    ]]
    meta_table = Table(meta_data, colWidths=[1.8*inch, 1.3*inch, 1.4*inch, 2.0*inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), DARK),
        ("TEXTCOLOR",    (0, 0), (-1, -1), GRAY),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#2a2d3e")),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # ── Summary
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor("#2a2d3e")))
    elements.append(Paragraph("📋  Summary", section_style))
    elements.append(Paragraph(extracted.get("summary", "No summary available."), body_style))
    elements.append(Spacer(1, 10))

    # ── Key Fields
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor("#2a2d3e")))
    elements.append(Paragraph("🔑  Key Fields", section_style))

    key_fields = extracted.get("key_fields", {})
    if key_fields:
        table_data = [[
            Paragraph("<b>Field</b>", label_style),
            Paragraph("<b>Value</b>", label_style)
        ]]
        def flatten(obj, prefix=""):
            rows = []
            for k, v in obj.items():
                label = (prefix + k).replace("_", " ").title()
                if isinstance(v, dict):
                    rows.extend(flatten(v, prefix=label + " › "))
                elif isinstance(v, list):
                    rows.append((label, ", ".join(str(i) for i in v)))
                else:
                    rows.append((label, str(v)))
            return rows

        for label, value in flatten(key_fields):
            table_data.append([
                Paragraph(label, label_style),
                Paragraph(value, value_style)
            ])

        kf_table = Table(table_data, colWidths=[2.2 * inch, 4.3 * inch])
        kf_table.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#2a2d3e")),
            ("BACKGROUND",   (0, 1), (-1, -1), DARK),
            ("TEXTCOLOR",    (0, 0), (-1, -1), WHITE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),
             [DARK, colors.HexColor("#1e2133")]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#2a2d3e")),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(kf_table)

    elements.append(Spacer(1, 16))

    # ── Anomalies
    anomalies = extracted.get("anomalies", [])
    if anomalies:
        elements.append(HRFlowable(width="100%", thickness=1, color=RED))
        elements.append(Paragraph("⚠️  Anomalies", ParagraphStyle(
            "Anom", parent=section_style, textColor=RED
        )))
        for a in anomalies:
            elements.append(Paragraph(f"• {a}", ParagraphStyle(
                "AnomBody", parent=body_style,
                textColor=colors.HexColor("#ff9999")
            )))
        elements.append(Spacer(1, 10))

    # ── Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor("#2a2d3e")))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Generated by DocuAgent  •  {timestamp}  •  Powered by Google Gemini",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    # ── Build
    doc.build(elements)

    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename=f"DocuAgent_{data.get('filename','report')}.pdf",
        background=None
    )