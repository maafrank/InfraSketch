"""
Diagram export utilities.
Handles conversion of diagrams to images and markdown to PDF.
"""
import base64
import io
import os
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


def generate_diagram_png(diagram: dict, output_path: Optional[str] = None) -> bytes:
    """
    Generate a PNG image of the diagram.

    For now, this creates a simple representation.
    In production, you might want to use a headless browser or
    server-side rendering of the React Flow diagram.

    Args:
        diagram: The diagram dict with nodes and edges
        output_path: Optional path to save the PNG file

    Returns:
        PNG image as bytes
    """
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])

    if not nodes:
        # Create empty diagram placeholder
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((300, 180), "No diagram available", fill='black')

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    # Calculate canvas size based on node positions
    max_x = max((n.get("position", {}).get("x", 0) for n in nodes), default=800)
    max_y = max((n.get("position", {}).get("y", 0) for n in nodes), default=600)

    width = int(max_x + 400)
    height = int(max_y + 400)

    # Create white canvas
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Define colors for node types
    node_colors = {
        "cache": "#FFA07A",
        "database": "#87CEEB",
        "api": "#98FB98",
        "server": "#DDA0DD",
        "loadbalancer": "#F0E68C",
        "queue": "#FFB6C1",
        "cdn": "#FFD700",
        "gateway": "#20B2AA",
        "storage": "#9370DB",
        "service": "#90EE90"
    }

    # Node ID to position mapping
    node_positions = {}

    # Draw edges first (so they appear behind nodes)
    for edge in edges:
        source_node = next((n for n in nodes if n["id"] == edge["source"]), None)
        target_node = next((n for n in nodes if n["id"] == edge["target"]), None)

        if source_node and target_node:
            x1 = source_node.get("position", {}).get("x", 0) + 100
            y1 = source_node.get("position", {}).get("y", 0) + 100
            x2 = target_node.get("position", {}).get("x", 0) + 100
            y2 = target_node.get("position", {}).get("y", 0) + 100

            # Draw arrow line
            draw.line([(x1, y1), (x2, y2)], fill='#888888', width=2)

            # Draw arrow head (simple triangle)
            # Calculate arrow direction
            import math
            angle = math.atan2(y2 - y1, x2 - x1)
            arrow_size = 10

            # Arrow head points
            arrow_p1 = (
                x2 - arrow_size * math.cos(angle - math.pi / 6),
                y2 - arrow_size * math.sin(angle - math.pi / 6)
            )
            arrow_p2 = (
                x2 - arrow_size * math.cos(angle + math.pi / 6),
                y2 - arrow_size * math.sin(angle + math.pi / 6)
            )

            draw.polygon([arrow_p1, (x2, y2), arrow_p2], fill='#888888')

    # Draw nodes
    for node in nodes:
        x = node.get("position", {}).get("x", 0) + 100
        y = node.get("position", {}).get("y", 0) + 100
        node_positions[node["id"]] = (x, y)

        node_type = node.get("type", "service")
        color = node_colors.get(node_type, "#E0E0E0")

        # Draw node rectangle
        node_width = 150
        node_height = 60
        draw.rectangle(
            [x - node_width/2, y - node_height/2, x + node_width/2, y + node_height/2],
            fill=color,
            outline='#333333',
            width=2
        )

        # Draw label
        label = node.get("label", "Node")
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), label, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        draw.text(
            (x - text_width/2, y - text_height/2),
            label,
            fill='#000000',
            font=title_font
        )

    # Save to buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()

    # Optionally save to file
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(png_bytes)

    return png_bytes


def convert_markdown_to_pdf(markdown_content: str, diagram_png_bytes: bytes, output_path: Optional[str] = None) -> bytes:
    """
    Convert markdown to PDF with embedded diagram image.

    Args:
        markdown_content: Markdown formatted content
        diagram_png_bytes: PNG image bytes of diagram
        output_path: Optional path to save PDF

    Returns:
        PDF as bytes
    """
    # Try WeasyPrint first (better formatting, but requires system libraries)
    try:
        return _convert_markdown_to_pdf_weasyprint(markdown_content, diagram_png_bytes, output_path)
    except (ImportError, OSError) as e:
        print(f"WeasyPrint not available ({e}), falling back to ReportLab...")
        return _convert_markdown_to_pdf_reportlab(markdown_content, diagram_png_bytes, output_path)


def _convert_markdown_to_pdf_weasyprint(markdown_content: str, diagram_png_bytes: bytes, output_path: Optional[str] = None) -> bytes:
    """Convert markdown to PDF using WeasyPrint (requires system libraries)."""
    import markdown2
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    # Convert markdown to HTML
    html_content = markdown2.markdown(markdown_content, extras=['tables', 'fenced-code-blocks'])

    # Embed diagram as base64 data URI
    diagram_base64 = base64.b64encode(diagram_png_bytes).decode('utf-8')
    diagram_data_uri = f"data:image/png;base64,{diagram_base64}"

    # Replace diagram.png reference with data URI
    html_content = html_content.replace('src="diagram.png"', f'src="{diagram_data_uri}"')

    # Create full HTML document with styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: letter;
                margin: 1in;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            h2 {{
                color: #34495e;
                border-bottom: 2px solid #bdc3c7;
                padding-bottom: 8px;
                margin-top: 25px;
            }}
            h3 {{
                color: #555;
                margin-top: 20px;
            }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }}
            ul, ol {{
                margin-left: 20px;
            }}
            li {{
                margin-bottom: 8px;
            }}
            strong {{
                color: #2c3e50;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Configure fonts
    font_config = FontConfiguration()

    # Convert HTML to PDF
    html_obj = HTML(string=full_html)
    pdf_bytes = html_obj.write_pdf(font_config=font_config)

    # Optionally save to file
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def _convert_markdown_to_pdf_reportlab(markdown_content: str, diagram_png_bytes: bytes, output_path: Optional[str] = None) -> bytes:
    """
    Convert markdown to PDF using ReportLab (simpler, no system dependencies).
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.colors import HexColor
    import re

    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           topMargin=1*inch, bottomMargin=1*inch,
                           leftMargin=1*inch, rightMargin=1*inch)

    # Container for PDF elements
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#2c3e50'),
        spaceAfter=30,
        spaceBefore=20,
    )

    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=20,
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#555'),
        spaceAfter=10,
        spaceBefore=15,
    )

    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=HexColor('#666'),
        spaceAfter=8,
        spaceBefore=12,
    )

    heading4_style = ParagraphStyle(
        'CustomHeading4',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=HexColor('#777'),
        fontWeight='bold',
        spaceAfter=6,
        spaceBefore=10,
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=16,
        spaceBefore=6,
        spaceAfter=6,
    )

    # Split markdown into lines
    lines = markdown_content.split('\n')

    for i, line in enumerate(lines):
        line = line.strip()

        if not line:
            story.append(Spacer(1, 0.2*inch))
            continue

        # Handle diagrams
        if '![' in line and 'diagram.png' in line:
            # Add the diagram image
            try:
                img_buffer = io.BytesIO(diagram_png_bytes)
                img = RLImage(img_buffer, width=5.5*inch, height=3.5*inch)
                story.append(img)
                story.append(Spacer(1, 0.3*inch))
            except Exception as e:
                print(f"Error adding image: {e}")
            continue

        # Handle headings (check longest patterns first)
        if line.startswith('##### '):
            text = line[6:].strip()
            story.append(Paragraph(text, heading4_style))  # H5 uses H4 style
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, heading4_style))
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, heading3_style))
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, heading1_style))
        elif line.startswith('# '):
            text = line[2:].strip()
            story.append(Paragraph(text, title_style))

        # Handle lists (both - and * bullets)
        elif line.startswith('- ') or line.startswith('* '):
            text = '• ' + line[2:].strip()
            # Remove markdown escape characters (backslashes before special chars)
            text = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', text)
            # Handle bold **text**
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(text, body_style))
        elif re.match(r'^\d+\.\s', line) or re.match(r'^\d+\\\.\s', line):  # Numbered lists (1. or 1\. )
            # Handle both "1. " and "1\. " formats
            if '\\.' in line:
                # Escaped period format: "1\. Item"
                text = line.split('\\.', 1)[1].strip()
            else:
                # Normal period format: "1. Item"
                text = line[line.index('.') + 1:].strip()
            # Remove markdown escape characters (backslashes before special chars)
            text = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', text)
            # Handle bold **text**
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(text, body_style))

        # Regular paragraphs
        else:
            # Remove markdown escape characters (backslashes before special chars)
            text = re.sub(r'\\([\\`*_{}\[\]()#+\-.!])', r'\1', line)
            # Handle bold **text**
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Handle italic *text*
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            story.append(Paragraph(text, body_style))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Optionally save to file
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
