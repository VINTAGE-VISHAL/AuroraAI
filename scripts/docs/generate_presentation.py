import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to add running footers with total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        width, height = self._pagesize
        
        # Cover page vs inner slides (Footers & Headers drawn in second pass)
        if self._pageNumber > 1:
            # Header top accent line
            self.setFillColor(colors.HexColor("#0f172a"))
            self.rect(0, height - 48, width, 48, fill=True, stroke=False)
            self.setFillColor(colors.HexColor("#38bdf8"))
            self.rect(0, height - 52, width, 4, fill=True, stroke=False)
            
            # Running Header Text
            self.setFont("Helvetica-Bold", 11)
            self.setFillColor(colors.HexColor("#f8fafc"))
            self.drawString(36, height - 30, "AURORA ENGINE — ARCHITECTURE & SYSTEM FLOW PRESENTATION")
            
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.HexColor("#94a3b8"))
            self.drawRightString(width - 36, height - 30, "Technical Handover Deck")

            # Bottom Footer Bar
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(1)
            self.line(36, 36, width - 36, 36)
            
            self.setFont("Helvetica", 8.5)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(36, 22, "AuroraEngine Framework • Educational AI Architecture Handover")
            
            page_text = f"Slide {self._pageNumber} of {page_count}"
            self.drawRightString(width - 36, 22, page_text)
            
        self.restoreState()


def draw_first_page_bg(canvas, doc):
    """Draw dark slide background on Page 1 before story elements are rendered."""
    canvas.saveState()
    width, height = doc.pagesize
    # Dark Cover Background
    canvas.setFillColor(colors.HexColor("#0f172a"))
    canvas.rect(0, 0, width, height, fill=True, stroke=False)
    
    # Subtle accent stripes
    canvas.setFillColor(colors.HexColor("#1e293b"))
    canvas.rect(0, height - 12, width, 12, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#38bdf8"))
    canvas.rect(0, height - 16, width * 0.45, 4, fill=True, stroke=False)
    
    canvas.setFillColor(colors.HexColor("#0284c7"))
    canvas.rect(0, 0, width, 10, fill=True, stroke=False)
    canvas.restoreState()


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def create_presentation_pdf(output_filename=None):
    if output_filename is None:
        output_filename = os.path.join(REPO_ROOT, "docs", "presentation", "PROJECT_ARCHITECTURE_PRESENTATION.pdf")
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    page_width, page_height = landscape(A4)
    margin = 36 # 0.5 inch margins
    
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=58, # Space below header bar
        bottomMargin=48, # Space above footer line
    )

    styles = getSampleStyleSheet()

    # Color Palette
    PRIMARY = colors.HexColor("#0f172a")
    SECONDARY = colors.HexColor("#0284c7")
    DARK_CARD = colors.HexColor("#1e293b")
    CARD_BG = colors.HexColor("#f1f5f9")
    TEXT_DARK = colors.HexColor("#1e293b")
    TEXT_MUTED = colors.HexColor("#475569")

    # Typography Styles
    styles.add(ParagraphStyle(
        name="TitleSlideHeader",
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=36,
        textColor=colors.HexColor("#f8fafc"),
        spaceAfter=10,
    ))
    
    styles.add(ParagraphStyle(
        name="TitleSlideSub",
        fontName="Helvetica",
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#38bdf8"),
        spaceAfter=20,
    ))
    
    styles.add(ParagraphStyle(
        name="TitleSlideMeta",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#cbd5e1"),
    ))

    styles.add(ParagraphStyle(
        name="SlideTitle",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=PRIMARY,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="SlideSubTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        name="SlideBody",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="CodeBox",
        fontName="Courier-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#e2e8f0"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=1,
        borderPadding=6,
        spaceAfter=6,
        borderRadius=4,
    ))

    styles.add(ParagraphStyle(
        name="CalloutText",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
    ))

    story = []

    # ==========================================
    # SLIDE 1: COVER / TITLE SLIDE
    # ==========================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("AURORA ENGINE", styles["TitleSlideHeader"]))
    story.append(Paragraph("Project Architecture & Technical Flow Handover Presentation", styles["TitleSlideSub"]))
    
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#38bdf8"), spaceAfter=20))
    
    overview_text = """
    <b>Target Audience:</b> Engineering Leads, Software Architects & Incoming Development Teams<br/>
    <b>Domain:</b> Research-Grade Modular Educational AI & QLoRA Subject Adaptation<br/>
    <b>Repository:</b> AuroraEngine (Clean Architecture Paradigm)<br/>
    <b>Status:</b> 100% Verified Suite • 130 Unit Tests Passing • Production Ready
    """
    story.append(Paragraph(overview_text, styles["TitleSlideMeta"]))
    
    story.append(Spacer(1, 25))
    
    badge_table_data = [
        [
            Paragraph("<b>6 CS Subject Domains</b><br/>DBMS • DSA • OOPS • OS • CNT • OOSE", ParagraphStyle("b1", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=colors.white)),
            Paragraph("<b>Qwen3-8B Foundation</b><br/>4-Bit NF4 QLoRA Adaptation", ParagraphStyle("b2", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=colors.white)),
            Paragraph("<b>FastAPI SSE Server</b><br/>OpenAI-Compatible Streaming", ParagraphStyle("b3", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=colors.white)),
            Paragraph("<b>Next.js 16 Web UI</b><br/>LaTeX Math & Code Support", ParagraphStyle("b4", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=colors.white)),
        ]
    ]
    t_badges = Table(badge_table_data, colWidths=[185, 185, 185, 185])
    t_badges.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1e293b")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#38bdf8")),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#334155")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_badges)
    story.append(PageBreak())

    # ==========================================
    # SLIDE 2: EXECUTIVE SUMMARY & PURPOSE
    # ==========================================
    story.append(Paragraph("1. Executive Overview & System Purpose", styles["SlideTitle"]))
    story.append(Paragraph("What AuroraEngine Is and How It Solves Educational LLM Trustworthiness", styles["SlideSubTitle"]))
    
    col1_text = """
    <b>Core Purpose:</b><br/>
    AuroraEngine is NOT a simple chatbot or naive RAG script. It is a research-grade educational AI framework that converts trusted educational textbooks and syllabi into domain-specialized language model adapters.<br/><br/>
    <b>Supported Computer Science Curricula:</b>
    <br/>• <b>DBMS:</b> Database Systems (SQL, Relational Algebra, Transactions)
    <br/>• <b>DSA:</b> Data Structures & Algorithms (Trees, Graphs, DP)
    <br/>• <b>OOPS:</b> Object-Oriented Programming (Design Patterns, SOLID)
    <br/>• <b>OS:</b> Operating Systems (Concurrency, Memory, Virtualization)
    <br/>• <b>CNT:</b> Computer Networks (TCP/IP, Routing, OSI Layers)
    <br/>• <b>OOSE:</b> Software Engineering (UML, Agile, System Requirements)
    """

    col2_text = """
    <b>Key Architecture Pillars:</b>
    <br/>1. <b>Clean Architecture:</b> Domain models and interfaces strictly separated from external infrastructure or web frameworks.
    <br/>2. <b>Interface-First Design:</b> Every pipeline stage is defined by abstract contracts before implementation.
    <br/>3. <b>QLoRA Fine-Tuning:</b> 4-bit NF4 quantized adaptation on 8B parameter models (`Qwen/Qwen3-8B`).
    <br/>4. <b>Domain Guardrails:</b> Non-CS queries (recipes, chit-chat) are rejected automatically at the API boundary.
    <br/>5. <b>Artifact Immutability:</b> Checksums and parent UUID lineage tracking preserve reproducibility.
    """
    
    t_summary = Table([[Paragraph(col1_text, styles["SlideBody"]), Paragraph(col2_text, styles["SlideBody"])]], colWidths=[370, 370])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), CARD_BG),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor("#f0f9ff")),
        ('BOX', (0,0), (0,0), 1, colors.HexColor("#cbd5e1")),
        ('BOX', (1,0), (1,0), 1, colors.HexColor("#7dd3fc")),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_summary)
    
    story.append(Spacer(1, 10))
    
    # Status Banner
    status_box = Paragraph(
        "<b>Framework Operational Status:</b> ✅ Core Pipeline, QLoRA Training Engine, FastAPI SSE Server, Next.js Frontend, Streamlit Lab, and 130 Pytest Verification Tests are 100% Implemented & Passing.",
        ParagraphStyle("stat", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=colors.HexColor("#15803d"))
    )
    t_stat = Table([[status_box]], colWidths=[748])
    t_stat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#dcfce7")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86efac")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_stat)
    story.append(PageBreak())

    # ==========================================
    # SLIDE 3: SYSTEM ARCHITECTURE DIAGRAM
    # ==========================================
    story.append(Paragraph("2. System Architecture Diagram", styles["SlideTitle"]))
    story.append(Paragraph("High-Level Layer Interactions Across Frontend, Backend, ML Subsystem, and Storage", styles["SlideSubTitle"]))

    # Draw Diagram via ReportLab Graphics
    d = Drawing(748, 250)
    
    # Background Canvas
    d.add(Rect(0, 0, 748, 250, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#e2e8f0"), strokeWidth=1, rx=6, ry=6))
    
    # Tier Boxes
    # 1. UI Layer
    d.add(Rect(20, 160, 210, 75, fillColor=colors.HexColor("#eff6ff"), strokeColor=colors.HexColor("#3b82f6"), strokeWidth=1.5, rx=4, ry=4))
    d.add(String(125, 218, "CLIENT / USER INTERFACES", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#1e40af")))
    d.add(String(125, 195, "• Next.js Web Client (frontend/)", textAnchor="middle", fontName="Helvetica", fontSize=8.5, fillColor=colors.HexColor("#1e293b")))
    d.add(String(125, 175, "• Streamlit Lab UI (src/aurora/ui)", textAnchor="middle", fontName="Helvetica", fontSize=8.5, fillColor=colors.HexColor("#1e293b")))

    # 2. API Server
    d.add(Rect(270, 160, 200, 75, fillColor=colors.HexColor("#f0fdf4"), strokeColor=colors.HexColor("#22c55e"), strokeWidth=1.5, rx=4, ry=4))
    d.add(String(370, 218, "FASTAPI API SERVER", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#166534")))
    d.add(String(370, 200, "aurora.deployment.api_server", textAnchor="middle", fontName="Helvetica-Oblique", fontSize=8, fillColor=colors.HexColor("#15803d")))
    d.add(String(370, 186, "• /v1/chat/completions (SSE)", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(370, 172, "• CS Subject Domain Guardrails", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))

    # 3. Inference Engine
    d.add(Rect(510, 160, 218, 75, fillColor=colors.HexColor("#faf5ff"), strokeColor=colors.HexColor("#a855f7"), strokeWidth=1.5, rx=4, ry=4))
    d.add(String(619, 218, "INFERENCE SUBSYSTEM", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#6b21a8")))
    d.add(String(619, 200, "InferenceEngine & AdapterManager", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(619, 186, "• Base Model: Qwen/Qwen3-8B", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(619, 172, "• Dynamic LoRA Adapter Hot-Swap", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))

    # Arrows Row 1
    d.add(Line(230, 197, 270, 197, strokeColor=colors.HexColor("#0284c7"), strokeWidth=2))
    d.add(String(250, 202, "HTTP / SSE", textAnchor="middle", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#0284c7")))
    
    d.add(Line(470, 197, 510, 197, strokeColor=colors.HexColor("#0284c7"), strokeWidth=2))
    d.add(String(490, 202, "Python Call", textAnchor="middle", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#0284c7")))

    # Bottom Tier: Pipeline & Storage
    d.add(Rect(20, 15, 450, 125, fillColor=colors.HexColor("#fff7ed"), strokeColor=colors.HexColor("#f97316"), strokeWidth=1.5, rx=4, ry=4))
    d.add(String(245, 123, "AURORA CORE PIPELINE (src/aurora/)", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#c2410c")))
    
    pipeline_boxes = [
        ("Ingestion", 35, 68, 75, 40),
        ("Preproc & Seg", 120, 68, 80, 40),
        ("Knowledge Graph", 210, 68, 85, 40),
        ("Dataset Eng", 305, 68, 75, 40),
        ("QLoRA Trainer", 390, 68, 70, 40),
    ]
    for name, x, y, w, h in pipeline_boxes:
        d.add(Rect(x, y, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#ea580c"), strokeWidth=1, rx=3, ry=3))
        d.add(String(x + w/2, y + h/2 - 3, name, textAnchor="middle", fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor("#9a3412")))

    # Arrows in Pipeline
    for i in range(len(pipeline_boxes)-1):
        x1 = pipeline_boxes[i][1] + pipeline_boxes[i][3]
        x2 = pipeline_boxes[i+1][1]
        y = pipeline_boxes[i][2] + pipeline_boxes[i][4]/2
        d.add(Line(x1, y, x2, y, strokeColor=colors.HexColor("#ea580c"), strokeWidth=1.5))

    d.add(String(245, 30, "Clean Architecture Contract-Driven Data Stages", textAnchor="middle", fontName="Helvetica-Oblique", fontSize=8, fillColor=colors.HexColor("#ea580c")))

    # Quality Gate & Storage
    d.add(Rect(510, 15, 218, 125, fillColor=colors.HexColor("#f1f5f9"), strokeColor=colors.HexColor("#475569"), strokeWidth=1.5, rx=4, ry=4))
    d.add(String(619, 123, "DATA & ARTIFACT STORAGE", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#334155")))
    d.add(String(619, 102, "• data/corpus/ (Subject .jsonl)", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(619, 85, "• data/output/ (LoRA .safetensors)", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(619, 68, "• data/logs/ (Daily execution JSONL)", textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#1e293b")))
    d.add(String(619, 42, "Evaluator Quality Gate Check", textAnchor="middle", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor("#16a34a")))

    # Arrow from Pipeline to Storage
    d.add(Line(470, 88, 510, 88, strokeColor=colors.HexColor("#475569"), strokeWidth=2))
    # Arrow from Storage to Inference Engine
    d.add(Line(619, 140, 619, 160, strokeColor=colors.HexColor("#a855f7"), strokeWidth=2))
    d.add(String(625, 148, "Load Weights", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#6b21a8")))

    story.append(d)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Figure 1:</b> Architectural interaction map showing decoupled clean boundaries between client web apps, the API server, inference subsystem, data pipeline, and LoRA artifact storage.", ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=TEXT_MUTED)))
    story.append(PageBreak())

    # ==========================================
    # SLIDE 4: END-TO-END EXECUTION FLOW
    # ==========================================
    story.append(Paragraph("3. End-to-End Request Execution Flow", styles["SlideTitle"]))
    story.append(Paragraph("Detailed Step-by-Step Trajectory from Student Prompt to Token Streaming", styles["SlideSubTitle"]))

    flow_table_data = [
        [Paragraph("<b>Step & Stage</b>", styles["SlideBody"]), Paragraph("<b>Execution Component</b>", styles["SlideBody"]), Paragraph("<b>Technical Operation & Logic</b>", styles["SlideBody"])],
        [
            Paragraph("<b>1. Subject Selection & Query</b>", styles["SlideBody"]),
            Paragraph("Next.js Frontend (`frontend/src/app/page.tsx`)", styles["SlideBody"]),
            Paragraph("User chooses CS domain context (e.g. Operating Systems `OS`) and enters query. Client calls `streamChatCompletion()` via Fetch API over HTTP POST to `/v1/chat/completions`.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>2. Domain Guardrail Check</b>", styles["SlideBody"]),
            Paragraph("FastAPI API Server (`src/aurora/deployment/api_server.py`)", styles["SlideBody"]),
            Paragraph("System prompt validates query scope. Non-CS topics (recipes, chit-chat) are rejected immediately with standardized educational boundary note.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>3. Adapter Resolution</b>", styles["SlideBody"]),
            Paragraph("Adapter Routing Map (`ADAPTER_MAP`)", styles["SlideBody"]),
            Paragraph("Maps model identifier (`aurora-os`) to adapter checkpoint directory `data/output/os_adapter/final_adapter`.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>4. Dynamic LoRA Mount</b>", styles["SlideBody"]),
            Paragraph("`AdapterManager` & `InferenceEngine`", styles["SlideBody"]),
            Paragraph("Hot-swaps target PEFT LoRA adapter weights on top of loaded `Qwen3-8B` base model in VRAM without reloading base weights.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>5. Streaming Generation</b>", styles["SlideBody"]),
            Paragraph("`Generator` & PyTorch CUDA Engine", styles["SlideBody"]),
            Paragraph("Executes token-by-token generation loop. Yields streaming text chunks back to FastAPI endpoint.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>6. SSE Event Delivery</b>", styles["SlideBody"]),
            Paragraph("FastAPI `StreamingResponse`", styles["SlideBody"]),
            Paragraph("Pushes `data: {\"choices\": [{\"delta\": {\"content\": \"...\"}}]}` event stream compliant with OpenAI API standard.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>7. UI Math & Markdown Render</b>", styles["SlideBody"]),
            Paragraph("React Client (`react-markdown` + `katex`)", styles["SlideBody"]),
            Paragraph("Renders live markdown formatting, syntax highlighted code blocks, and KaTeX mathematical equations for student.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>8. Interaction Logging</b>", styles["SlideBody"]),
            Paragraph("JSONL Interaction Logger", styles["SlideBody"]),
            Paragraph("Appends execution record (timestamp, prompt, adapter mode, latency, answer) to daily log file `data/logs/YYYY-MM-DD.jsonl`.", styles["SlideBody"])
        ]
    ]

    t_flow = Table(flow_table_data, colWidths=[140, 195, 413])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_flow)
    story.append(PageBreak())

    # ==========================================
    # SLIDE 5: CORE PIPELINE ARCHITECTURE
    # ==========================================
    story.append(Paragraph("4. Core Data & Training Pipeline", styles["SlideTitle"]))
    story.append(Paragraph("The Multi-Stage Ingestion, Curriculum Extraction, and Fine-Tuning Sequence", styles["SlideSubTitle"]))

    pipe_col1 = """
    <b>Pipeline Phase Responsibilities:</b><br/><br/>
    <b>1. Ingestion (`src/aurora/ingestion/`):</b>
    <br/>• Scans raw files (`FileScanner`), tracks checksums in `SourceRegistry`.
    <br/>• Reads PDF/TXT documents into `RawDocument` domain models.<br/><br/>
    <b>2. Preprocessing & Segmentation (`preprocessing/`, `segmentation/`):</b>
    <br/>• Normalizes reading order, strips layout noise.
    <br/>• Splits text into semantically cohesive `StructuredDocument` chunks.<br/><br/>
    <b>3. Curriculum Knowledge Extraction (`corpus/`, `knowledge/`):</b>
    <br/>• Extracts concept dependency graphs and syllabus taxonomies.
    <br/>• Builds curriculum knowledge representations.<br/><br/>
    <b>4. Educational Dataset Engineering (`dataset/`, `corpus/`):</b>
    <br/>• Generates synthetic QA instruction pairs across subject domains.
    <br/>• Exports validated `.jsonl` files to `data/corpus/`.
    """

    pipe_col2 = """
    <b>Training & Packaging Pipeline:</b><br/><br/>
    <b>5. QLoRA Training Engine (`src/aurora/training/`):</b>
    <br/>• `ModelPreparer`: Loads `Qwen/Qwen3-8B` with 4-bit NF4 double quantization (`bitsandbytes`).
    <br/>• Configures PEFT LoRA target projection modules (`q_proj`, `v_proj`, etc.).
    <br/>• `Trainer`: Executes PyTorch training loop over subject `.jsonl` corpora.<br/><br/>
    <b>6. Checkpoint Management (`checkpoint_manager.py`):</b>
    <br/>• Manages step checkpoints and saves adapter tensors.<br/><br/>
    <b>7. Quality Gate Evaluation (`evaluator.py`, `evaluation/`):</b>
    <br/>• `UnifiedSubjectEvaluator` validates final loss against quality threshold.
    <br/>• Pushes passed model to `AdapterPackager`.<br/><br/>
    <b>8. Deployment Packaging (`adapter_packager.py`):</b>
    <br/>• Exports finalized adapter weights to `data/output/<subject>_adapter/final_adapter`.
    """

    t_pipe = Table([[Paragraph(pipe_col1, styles["SlideBody"]), Paragraph(pipe_col2, styles["SlideBody"])]], colWidths=[370, 370])
    t_pipe.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor("#fff7ed")),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor("#f0fdf4")),
        ('BOX', (0,0), (0,0), 1, colors.HexColor("#ffedd5")),
        ('BOX', (1,0), (1,0), 1, colors.HexColor("#dcfce7")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_pipe)
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Clean Architecture Rule:</b> Pipeline stages communicate strictly through immutable Pydantic models with parent artifact lineage tracking, guaranteeing zero accidental state side effects.", styles["CalloutText"]))
    story.append(PageBreak())

    # ==========================================
    # SLIDE 6: QLORA FINE-TUNING SUBSYSTEM
    # ==========================================
    story.append(Paragraph("5. AI / QLoRA Fine-Tuning & Hardware Blueprint", styles["SlideTitle"]))
    story.append(Paragraph("Hyperparameters, Base Models, Quantization Modes, and Resource Specifications", styles["SlideSubTitle"]))

    ml_table_data = [
        [Paragraph("<b>Parameter Category</b>", styles["SlideBody"]), Paragraph("<b>Configured Value / Specification</b>", styles["SlideBody"]), Paragraph("<b>Engineering Rationale</b>", styles["SlideBody"])],
        [
            Paragraph("<b>Base Foundation LLM</b>", styles["SlideBody"]),
            Paragraph("`Qwen/Qwen3-8B` / `Qwen3-8B-Instruct`", styles["SlideBody"]),
            Paragraph("High reasoning baseline capability for complex Computer Science code and math.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>Quantization Precision</b>", styles["SlideBody"]),
            Paragraph("`4-bit NF4` (NormalFloat4) + Double Quantization", styles["SlideBody"]),
            Paragraph("Reduces VRAM consumption from ~16GB to ~5.5GB during fine-tuning.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>Compute DType</b>", styles["SlideBody"]),
            Paragraph("`bfloat16` (`bnb_compute_dtype=bfloat16`)", styles["SlideBody"]),
            Paragraph("Native speed preference for Ampere/Ada GPU architectures (e.g. NVIDIA RTX 4080).", styles["SlideBody"])
        ],
        [
            Paragraph("<b>LoRA Rank (`r`) & Alpha</b>", styles["SlideBody"]),
            Paragraph("Rank `r = 16`, `alpha = 32`, `dropout = 0.05`", styles["SlideBody"]),
            Paragraph("Optimal capacity-to-overfitting ratio for domain-specific educational adaptation.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>Target Modules</b>", styles["SlideBody"]),
            Paragraph("`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`", styles["SlideBody"]),
            Paragraph("Full attention & MLP projection adaptation for comprehensive knowledge retention.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>Training Batch Setup</b>", styles["SlideBody"]),
            Paragraph("Batch Size = 1 (or 4), Grad Accumulation Steps = 16", styles["SlideBody"]),
            Paragraph("Effective batch size of 16-64 without exceeding consumer GPU VRAM limits.", styles["SlideBody"])
        ],
        [
            Paragraph("<b>Learning Rate & Schedule</b>", styles["SlideBody"]),
            Paragraph("LR = `2e-4`, Warmup Ratio = `0.03`, Weight Decay = `0.01`", styles["SlideBody"]),
            Paragraph("Stable convergence with AdamW optimizer and linear warmup schedule.", styles["SlideBody"])
        ],
    ]

    t_ml = Table(ml_table_data, colWidths=[150, 240, 358])
    t_ml.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_ml)
    story.append(PageBreak())

    # ==========================================
    # SLIDE 7: FRONTEND & API ECOSYSTEM
    # ==========================================
    story.append(Paragraph("6. Frontend & API Ecosystem", styles["SlideTitle"]))
    story.append(Paragraph("Web Application Interface, Evaluation Lab, and API Server Specifications", styles["SlideSubTitle"]))

    app_col1 = """
    <b>1. Next.js 16 Web Application (`frontend/`):</b>
    <br/>• <b>Tech Stack:</b> React 19, TypeScript 5, Tailwind CSS 4, Lucide Icons.
    <br/>• <b>Math & Markdown:</b> Integrated `katex`, `react-markdown`, `remark-math`, and `rehype-highlight` for crisp formatting.
    <br/>• <b>Streaming Service (`src/services/api.ts`):</b> Consumes SSE chunks over `fetch()`. Automatically triggers offline fallback simulation if backend server is offline.
    <br/>• <b>Subject Context Selector:</b> Dynamically sets active subject domain badges (`DBMS`, `DSA`, `OOPS`, `OS`, `CNT`, `OOSE`).
    """

    app_col2 = """
    <b>2. Streamlit Evaluation Lab (`src/aurora/ui/app.py`):</b>
    <br/>• <b>Purpose:</b> Dark-mode lab environment for model evaluation and probing.
    <br/>• <b>Features:</b> Live model testing, generation parameter tweaking, interaction log viewer (`data/logs/`).<br/><br/>
    <b>3. FastAPI API Server (`src/aurora/deployment/api_server.py`):</b>
    <br/>• <b>`POST /v1/chat/completions`:</b> OpenAI-compatible SSE token streaming endpoint.
    <br/>• <b>`GET /v1/models`:</b> Lists all 7 trained Aurora domain models & adapters.
    <br/>• <b>CORS Middleware:</b> Configured for seamless cross-origin web integration.
    """

    t_app = Table([[Paragraph(app_col1, styles["SlideBody"]), Paragraph(app_col2, styles["SlideBody"])]], colWidths=[370, 370])
    t_app.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor("#f0f9ff")),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor("#faf5ff")),
        ('BOX', (0,0), (0,0), 1, colors.HexColor("#bae6fd")),
        ('BOX', (1,0), (1,0), 1, colors.HexColor("#e9d5ff")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_app)
    
    story.append(Spacer(1, 8))
    story.append(Paragraph("Code Snippet — FastAPI OpenAI SSE Response Setup:", styles["SlideSubTitle"]))
    code_text = """@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # Resolves target LoRA adapter (e.g. aurora-os -> data/output/os_adapter/final_adapter)
    adapter_path = resolve_adapter_path(model_id, messages)
    return StreamingResponse(event_generator(), media_type="text/event-stream")"""
    story.append(Paragraph(code_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), styles["CodeBox"]))
    story.append(PageBreak())

    # ==========================================
    # SLIDE 8: REPOSITORY MAP
    # ==========================================
    story.append(Paragraph("7. Repository Structure & Key Entry Points", styles["SlideTitle"]))
    story.append(Paragraph("Shortlist of Critical Files Every Developer Must Inspect First", styles["SlideSubTitle"]))

    repo_table_data = [
        [Paragraph("<b>File Path</b>", styles["SlideBody"]), Paragraph("<b>Responsibility & Role in System</b>", styles["SlideBody"]), Paragraph("<b>When to Modify</b>", styles["SlideBody"])],
        [
            Paragraph("[`src/aurora/deployment/api_server.py`](file:///c:/AuroraEngine/src/aurora/deployment/api_server.py)", styles["SlideBody"]),
            Paragraph("FastAPI API server router, domain guardrails, and SSE stream dispatcher.", styles["SlideBody"]),
            Paragraph("Adding endpoints, altering domain system prompts, modifying CORS.", styles["SlideBody"])
        ],
        [
            Paragraph("[`src/aurora/inference/inference_engine.py`](file:///c:/AuroraEngine/src/aurora/inference/inference_engine.py)", styles["SlideBody"]),
            Paragraph("Loads base model (`Qwen3-8B`), mounts active LoRA adapter, executes generation.", styles["SlideBody"]),
            Paragraph("Changing base LLM loading, tweaking generation parameters.", styles["SlideBody"])
        ],
        [
            Paragraph("[`src/aurora/training/trainer.py`](file:///c:/AuroraEngine/src/aurora/training/trainer.py)", styles["SlideBody"]),
            Paragraph("PyTorch QLoRA training engine using Hugging Face Transformers & PEFT.", styles["SlideBody"]),
            Paragraph("Modifying loss calculation, trainer callbacks, saving logic.", styles["SlideBody"])
        ],
        [
            Paragraph("[`frontend/src/app/page.tsx`](file:///c:/AuroraEngine/frontend/src/app/page.tsx)", styles["SlideBody"]),
            Paragraph("Next.js main web chat client entry point.", styles["SlideBody"]),
            Paragraph("Modifying chat UI layout, adding sidebar features.", styles["SlideBody"])
        ],
        [
            Paragraph("[`train_unified.py`](file:///c:/AuroraEngine/train_unified.py)", styles["SlideBody"]),
            Paragraph("Orchestrates multi-subject unified model training run across all 6 CS domains.", styles["SlideBody"]),
            Paragraph("Launching dataset-wide fine-tuning runs.", styles["SlideBody"])
        ],
        [
            Paragraph("[`run_config.json`](file:///c:/AuroraEngine/run_config.json)", styles["SlideBody"]),
            Paragraph("Central hyperparameter configuration file (epochs, LR, LoRA rank, batch size).", styles["SlideBody"]),
            Paragraph("Adjusting fine-tuning hyperparameters or target hardware.", styles["SlideBody"])
        ],
        [
            Paragraph("[`stage1_smoke_test.py`](file:///c:/AuroraEngine/stage1_smoke_test.py)", styles["SlideBody"]),
            Paragraph("Rapid pipeline validation and packaging test script.", styles["SlideBody"]),
            Paragraph("Verifying pipeline setup after major code changes.", styles["SlideBody"])
        ],
    ]

    t_repo = Table(repo_table_data, colWidths=[200, 310, 238])
    t_repo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_repo)
    story.append(PageBreak())

    # ==========================================
    # SLIDE 9: DEVELOPER HANDOVER & QUICK START
    # ==========================================
    story.append(Paragraph("8. Developer Handover & Quick Start Guide", styles["SlideTitle"]))
    story.append(Paragraph("Practical Instructions for the Incoming Development Team", styles["SlideSubTitle"]))

    handover_col1 = """
    <b>🚀 New Developer First-Day Commands:</b>
    """
    story.append(Paragraph(handover_col1, styles["SlideBody"]))
    
    cmd_box_text = """# 1. Activate environment and install framework
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".[dev]"

# 2. Run automated verification test suite
pytest

# 3. Start API backend server (Terminal 1)
python -m uvicorn aurora.deployment.api_server:app --reload --port 8000

# 4. Start Next.js Web Client (Terminal 2)
cd frontend && npm install && npm run dev"""
    story.append(Paragraph(cmd_box_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), styles["CodeBox"]))

    story.append(Spacer(1, 4))
    
    handover_col2 = """
    <b>Developer Workflow Checklist for New Features:</b>
    <br/>1. <b>Adding a New Subject Domain:</b> Add dataset in `data/corpus/<subject>_training.jsonl` -> Create `train_<subject>.py` -> Register in `frontend/src/config/api.ts` -> Add route in `api_server.py`.
    <br/>2. <b>Modifying Data Schemas:</b> Edit Pydantic models in `src/aurora/models/`. Ensure `frozen=True` is preserved to maintain immutability.
    <br/>3. <b>Pre-Commit Checks:</b> Always run `pytest`, `ruff check .`, and `mypy src/aurora` before creating pull requests.
    """
    story.append(Paragraph(handover_col2, styles["SlideBody"]))
    story.append(PageBreak())

    # ==========================================
    # SLIDE 10: ROADMAP
    # ==========================================
    story.append(Paragraph("9. Implementation Status & Future Roadmap", styles["SlideTitle"]))
    story.append(Paragraph("Current Feature Audit and Planned Architecture Extension Points", styles["SlideSubTitle"]))

    status_table_data = [
        [Paragraph("<b>Feature / Module</b>", styles["SlideBody"]), Paragraph("<b>Current Status</b>", styles["SlideBody"]), Paragraph("<b>Evidence / Location</b>", styles["SlideBody"]), Paragraph("<b>Notes for New Team</b>", styles["SlideBody"])],
        [
            Paragraph("Clean Architecture Core", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`src/aurora/core/`, `models/`", styles["SlideBody"]),
            Paragraph("Strict Pydantic v2 domain isolation.", styles["SlideBody"])
        ],
        [
            Paragraph("QLoRA Fine-Tuning Engine", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`src/aurora/training/`", styles["SlideBody"]),
            Paragraph("4-bit NF4 adaptation on Qwen3-8B.", styles["SlideBody"])
        ],
        [
            Paragraph("Multi-Subject Adapters", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`data/output/`", styles["SlideBody"]),
            Paragraph("Adapters for all 6 CS subjects + Unified model.", styles["SlideBody"])
        ],
        [
            Paragraph("FastAPI SSE API Server", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`aurora/deployment/api_server.py`", styles["SlideBody"]),
            Paragraph("OpenAI SSE stream protocol.", styles["SlideBody"])
        ],
        [
            Paragraph("Next.js Student Web UI", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`frontend/`", styles["SlideBody"]),
            Paragraph("LaTeX math, markdown, subject selection.", styles["SlideBody"])
        ],
        [
            Paragraph("Streamlit Evaluation Lab", styles["SlideBody"]),
            Paragraph("✅ Implemented", styles["SlideBody"]),
            Paragraph("`src/aurora/ui/app.py`", styles["SlideBody"]),
            Paragraph("Model testing & daily log inspector.", styles["SlideBody"])
        ],
        [
            Paragraph("API Token Authentication", styles["SlideBody"]),
            Paragraph("🔴 Not Implemented", styles["SlideBody"]),
            Paragraph("`api_server.py`", styles["SlideBody"]),
            Paragraph("`🔮 Potential Extension`: Add OAuth2/JWT.", styles["SlideBody"])
        ],
        [
            Paragraph("Vector DB Retrieval (RAG)", styles["SlideBody"]),
            Paragraph("🟡 Partial", styles["SlideBody"]),
            Paragraph("`src/aurora/storage/`", styles["SlideBody"]),
            Paragraph("`🔮 Potential Extension`: Integrate FAISS/Chroma.", styles["SlideBody"])
        ],
    ]

    t_stat = Table(status_table_data, colWidths=[150, 110, 190, 298])
    t_stat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_stat)
    
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Summary:</b> AuroraEngine provides a research-grade, production-tested foundation for educational AI models. The incoming development team can immediately start building custom adapters or extending storage backends.", styles["CalloutText"]))

    # Build PDF with custom first page background handler
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=draw_first_page_bg)
    print(f"Presentation PDF successfully created: {output_filename}")

if __name__ == "__main__":
    create_presentation_pdf()
