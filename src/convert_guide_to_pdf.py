import os
import re
import subprocess
import sys


def markdown_to_html(md_text: str) -> str:
    """
    Simple custom Markdown to HTML converter for presentation guide rendering.
    """
    html_lines = []
    in_list = False
    in_table = False
    table_headers = []
    table_rows = []

    for line in md_text.split("\n"):
        line_str = line.strip()

        # Handle headings
        if line_str.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{line_str[2:]}</h1>")
            continue
        elif line_str.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{line_str[3:]}</h2>")
            continue
        elif line_str.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{line_str[4:]}</h3>")
            continue

        # Handle Blockquotes
        if line_str.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<blockquote>{line_str[2:]}</blockquote>")
            continue

        # Handle Tables
        if "|" in line_str and line_str.startswith("|"):
            if "---" in line_str:
                continue
            cells = [c.strip() for c in line_str.split("|")[1:-1]]
            if not in_table:
                in_table = True
                table_headers = cells
            else:
                table_rows.append(cells)
            continue
        else:
            if in_table:
                # Render accumulated table
                tbl_html = "<table><thead><tr>"
                for th in table_headers:
                    tbl_html += f"<th>{th}</th>"
                tbl_html += "</tr></thead><tbody>"
                for row in table_rows:
                    tbl_html += "<tr>"
                    for cell in row:
                        tbl_html += f"<td>{cell}</td>"
                    tbl_html += "</tr>"
                tbl_html += "</tbody></table>"
                html_lines.append(tbl_html)
                in_table = False
                table_headers = []
                table_rows = []

        # Handle Lists
        if line_str.startswith("- ") or line_str.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = line_str[2:]
            html_lines.append(f"<li>{content}</li>")
            continue
        else:
            if in_list and not line_str.startswith("- ") and not line_str.startswith("* "):
                html_lines.append("</ul>")
                in_list = False

        # Code block fences
        if line_str.startswith("```"):
            if "```" in line_str[3:]:
                pass
            continue

        # Paragraph
        if line_str:
            html_lines.append(f"<p>{line_str}</p>")

    if in_list:
        html_lines.append("</ul>")

    body_content = "\n".join(html_lines)

    # Inline formatting (bold, code, links)
    body_content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", body_content)
    body_content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", body_content)
    body_content = re.sub(r"`(.*?)`", r"<code>\1</code>", body_content)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Presentation Guide - SIH26158</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }}
        body {{
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            color: #24292e;
            line-height: 1.6;
            font-size: 13px;
            background: #fff;
            padding: 0;
            margin: 0;
        }}
        h1 {{
            color: #0366d6;
            font-size: 22px;
            border-bottom: 2px solid #eaecef;
            padding-bottom: 8px;
            margin-top: 0;
        }}
        h2 {{
            color: #1b1f23;
            font-size: 16px;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 5px;
            margin-top: 20px;
        }}
        h3 {{
            color: #24292e;
            font-size: 14px;
            margin-top: 15px;
        }}
        blockquote {{
            margin: 12px 0;
            padding: 10px 15px;
            color: #444;
            background-color: #f1f8ff;
            border-left: 4px solid #0366d6;
            border-radius: 4px;
            font-style: italic;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 12px;
        }}
        th, td {{
            border: 1px solid #d1d5da;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        code {{
            background-color: #f3f3f3;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            color: #d73a49;
        }}
        ul {{
            padding-left: 20px;
            margin: 8px 0;
        }}
        li {{
            margin-bottom: 4px;
        }}
        .footer-note {{
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #e1e4e8;
            font-size: 11px;
            color: #586069;
            text-align: center;
        }}
    </style>
</head>
<body>
    {body_content}
    <div class="footer-note">
        Single-Pass Drone Video to 3D Model Generation System — SIH26158 Prototype Presentation Document
    </div>
</body>
</html>
"""
    return full_html


def generate_pdf_document(
    md_file_path: str,
    output_pdf_path: str
):
    """
    Convert Markdown presentation guide into a styled PDF via headless Edge browser.
    """
    if not os.path.exists(md_file_path):
        raise FileNotFoundError(f"Markdown file not found: {md_file_path}")

    with open(md_file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown_to_html(md_content)
    temp_html_path = os.path.join(os.path.dirname(output_pdf_path), "temp_presentation.html")

    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={output_pdf_path}",
        temp_html_path
    ]

    print(f"[+] Rendering PDF using Microsoft Edge headless renderer...")
    subprocess.run(cmd, check=True)

    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)

    print(f"[SUCCESS] PDF generated successfully: '{output_pdf_path}'")


def main():
    md_path = r"C:\Users\shito\.gemini\antigravity\brain\1f6c915a-0caa-46be-840a-738018d735f1\presentation_guide.md"
    pdf_artifact_path = r"C:\Users\shito\.gemini\antigravity\brain\1f6c915a-0caa-46be-840a-738018d735f1\presentation_guide.pdf"
    pdf_project_path = r"C:\Users\shito\.gemini\antigravity\scratch\sih26158_drone_3d\presentation_guide.pdf"

    generate_pdf_document(md_path, pdf_project_path)
    
    # Also save copy in artifact folder
    import shutil
    shutil.copy(pdf_project_path, pdf_artifact_path)
    print(f"[SAVED] Artifact copy saved to: '{pdf_artifact_path}'")


if __name__ == "__main__":
    main()
