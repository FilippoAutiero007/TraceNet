from __future__ import annotations

from typing import Iterable

from app.models.schemas import PktAnalysisResponse


def _sanitize_pdf_text(value: str) -> str:
    replacements = {
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u2026": "...",
        "\t": "  ",
    }
    sanitized = value
    for src, dst in replacements.items():
        sanitized = sanitized.replace(src, dst)
    return sanitized


def _wrap_lines(text: str, max_chars: int = 92) -> list[str]:
    wrapped: list[str] = []
    for raw_line in text.splitlines():
        line = _sanitize_pdf_text(raw_line).strip()
        if not line:
            wrapped.append("")
            continue
        current = line
        while len(current) > max_chars:
            split_at = current.rfind(" ", 0, max_chars)
            if split_at <= 0:
                split_at = max_chars
            wrapped.append(current[:split_at].strip())
            current = current[split_at:].strip()
        wrapped.append(current)
    return wrapped


def _escape_pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _build_sections(analysis: PktAnalysisResponse) -> list[str]:
    lines: list[str] = [
        "TraceNet Packet Tracer Analysis Report",
        "",
        f"File: {analysis.filename or 'network.pkt'}",
        f"Summary: {analysis.summary or 'No summary available.'}",
        f"Devices: {analysis.device_count} | Links: {analysis.link_count} | Issues: {analysis.issue_count}",
        "",
    ]

    if analysis.exercise_text:
        lines.extend(["Exercise text:", *_wrap_lines(analysis.exercise_text), ""])

    if analysis.remediation_steps:
        lines.append("Recommended remediation steps:")
        for idx, step in enumerate(analysis.remediation_steps, start=1):
            lines.extend(_wrap_lines(f"{idx}. {step}"))
        lines.append("")

    if analysis.review:
        lines.append("AI review overview:")
        lines.extend(_wrap_lines(analysis.review.overview))
        lines.append("")
        if analysis.review.things_correct:
            lines.append("What is already correct:")
            for item in analysis.review.things_correct:
                lines.extend(_wrap_lines(f"- {item}"))
            lines.append("")
        if analysis.review.things_to_fix:
            lines.append("What to fix:")
            for item in analysis.review.things_to_fix:
                lines.extend(_wrap_lines(f"- {item}"))
            lines.append("")
        if analysis.review.alignment_with_exercise:
            lines.append("Alignment with exercise:")
            lines.extend(_wrap_lines(analysis.review.alignment_with_exercise))
            lines.append("")

    if analysis.issues:
        lines.append("Detected issues:")
        for idx, issue in enumerate(analysis.issues, start=1):
            target = " - ".join(part for part in [issue.device or "", issue.interface or ""] if part)
            header = f"{idx}. [{issue.severity.upper()}] {issue.title}"
            if target:
                header += f" ({target})"
            lines.extend(_wrap_lines(header))
            lines.extend(_wrap_lines(issue.message))
            if issue.suggestion:
                lines.extend(_wrap_lines(f"How to fix: {issue.suggestion}"))
            lines.append("")
    elif analysis.report:
        lines.append("Detailed report:")
        lines.extend(_wrap_lines(analysis.report))

    return lines


def build_analysis_pdf_bytes(analysis: PktAnalysisResponse) -> bytes:
    lines = _build_sections(analysis)
    lines_per_page = 46
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]

    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        data = content.encode("cp1252", errors="replace") if isinstance(content, str) else content
        objects.append(data)
        return len(objects)

    font_obj = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_lines in pages:
        text_commands = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        first = True
        for line in page_lines:
            escaped = _escape_pdf_text(line)
            if first:
                text_commands.append(f"({_escape_pdf_text(line)}) Tj")
                first = False
            else:
                text_commands.append("T*")
                text_commands.append(f"({escaped}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("cp1252", errors="replace")
        content_obj = add_object(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        content_ids.append(content_obj)
        page_ids.append(add_object(""))  # placeholder

    pages_obj_id = add_object("")
    catalog_obj_id = add_object(f"<< /Type /Catalog /Pages {pages_obj_id} 0 R >>")

    kids_refs = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_obj_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [ {kids_refs} ] >>".encode("cp1252")

    for idx, page_id in enumerate(page_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_obj_id} 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_ids[idx]} 0 R >>"
        ).encode("cp1252")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)
