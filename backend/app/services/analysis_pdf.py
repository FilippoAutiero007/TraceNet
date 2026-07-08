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


def _wrap_lines(text: str, max_chars: int = 88) -> list[str]:
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
        "=" * 60,
        "  TraceNet - Report Analisi File Packet Tracer",
        "=" * 60,
        "",
        f"  File: {analysis.filename or 'network.pkt'}",
        f"  Dispositivi: {analysis.device_count}  |  Link: {analysis.link_count}  |  Problemi: {analysis.issue_count}",
        "",
    ]

    if analysis.exercise_text:
        lines.extend([
            "-" * 60,
            "  TESTO DELL'ESERCIZIO",
            "-" * 60,
            "",
            *_wrap_lines(analysis.exercise_text),
            "",
        ])

    errors = [i for i in analysis.issues if i.severity == "error"]
    warnings_ = [i for i in analysis.issues if i.severity == "warning"]
    infos = [i for i in analysis.issues if i.severity == "info"]

    lines.extend([
        "-" * 60,
        "  RIEPILOGO",
        "-" * 60,
        "",
        f"  Errori: {len(errors)}",
        f"  Avvisi: {len(warnings_)}",
        f"  Info:   {len(infos)}",
        "",
    ])

    if analysis.review:
        lines.extend([
            "-" * 60,
            "  REVISIONE AI",
            "-" * 60,
            "",
        ])
        if analysis.review.overview:
            lines.append("  Panoramica:")
            for wrap_line in _wrap_lines(analysis.review.overview):
                lines.append(f"    {wrap_line}")
            lines.append("")
        if analysis.review.things_correct:
            lines.append("  Cosa funziona gia':")
            for item in analysis.review.things_correct:
                for wrap_line in _wrap_lines(f"  - {item}"):
                    lines.append(f"    {wrap_line[2:]}" if wrap_line.startswith("  ") else f"    {wrap_line}")
            lines.append("")
        if analysis.review.things_to_fix:
            lines.extend([
                "  Cosa correggere:",
            ])
            for item in analysis.review.things_to_fix:
                for wrap_line in _wrap_lines(f"  - {item}"):
                    lines.append(f"    {wrap_line[2:]}" if wrap_line.startswith("  ") else f"    {wrap_line}")
            lines.append("")

    if errors:
        lines.extend([
            "-" * 60,
            "  ERRORI (da correggere obbligatoriamente)",
            "-" * 60,
            "",
        ])
        for idx, issue in enumerate(errors, start=1):
            target_parts = [issue.device or "", issue.interface or ""]
            target = " - ".join(p for p in target_parts if p)
            header = f"  {idx}. {issue.title}"
            if target:
                header += f"  [{target}]"
            lines.append(header)
            lines.append("")
            for wrap_line in _wrap_lines(issue.message):
                lines.append(f"     {wrap_line}")
            lines.append("")
            if issue.suggestion:
                lines.append("     COME RISOLVERE:")
                for wrap_line in _wrap_lines(issue.suggestion):
                    lines.append(f"     > {wrap_line}")
            lines.append("")

    if warnings_:
        lines.extend([
            "-" * 60,
            "  AVVISI (da verificare)",
            "-" * 60,
            "",
        ])
        for idx, issue in enumerate(warnings_, start=1):
            target_parts = [issue.device or "", issue.interface or ""]
            target = " - ".join(p for p in target_parts if p)
            header = f"  {idx}. {issue.title}"
            if target:
                header += f"  [{target}]"
            lines.append(header)
            if issue.message:
                for wrap_line in _wrap_lines(issue.message):
                    lines.append(f"     {wrap_line}")
            if issue.suggestion:
                lines.append("     Suggerimento:")
                for wrap_line in _wrap_lines(issue.suggestion):
                    lines.append(f"     > {wrap_line}")
            lines.append("")

    if infos:
        lines.extend([
            "-" * 60,
            "  INFO (consigli e best practice)",
            "-" * 60,
            "",
        ])
        for idx, issue in enumerate(infos, start=1):
            target_parts = [issue.device or "", issue.interface or ""]
            target = " - ".join(p for p in target_parts if p)
            header = f"  {idx}. {issue.title}"
            if target:
                header += f"  [{target}]"
            lines.append(header)
            if issue.suggestion:
                for wrap_line in _wrap_lines(issue.suggestion):
                    lines.append(f"     {wrap_line}")
            lines.append("")

    if analysis.remediation_steps:
        lines.extend([
            "-" * 60,
            "  PIANO DI CORREZIONE PASSO-PASSO",
            "-" * 60,
            "",
        ])
        for idx, step in enumerate(analysis.remediation_steps, start=1):
            for wrap_line in _wrap_lines(f"{idx}. {step}"):
                lines.append(f"  {wrap_line}")
            lines.append("")

    lines.extend([
        "-" * 60,
        "  GENERATO DA TRACENET",
        "-" * 60,
        "",
        "  Apri il file .pkt in Cisco Packet Tracer,",
        "  segui le correzioni suggerite e riesegui l'analisi.",
        "  Per una revisione dettagliata, fornisci il testo",
        "  dell'esercizio nell'analisi.",
        "",
    ])

    return lines


def build_analysis_pdf_bytes(analysis: PktAnalysisResponse) -> bytes:
    lines = _build_sections(analysis)
    lines_per_page = 44
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]

    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        data = content.encode("cp1252", errors="replace") if isinstance(content, str) else content
        objects.append(data)
        return len(objects)

    font_obj = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    bold_font = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_lines in pages:
        text_commands = ["BT", "/F1 9 Tf", "30 790 Td", "13 TL"]
        first = True
        for line in page_lines:
            escaped = _escape_pdf_text(line)
            if first:
                text_commands.append(f"({escaped}) Tj")
                first = False
            else:
                text_commands.append("T*")
                text_commands.append(f"({escaped}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("cp1252", errors="replace")
        content_obj = add_object(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        content_ids.append(content_obj)
        page_ids.append(add_object(""))

    pages_obj_id = add_object("")
    catalog_obj_id = add_object(f"<< /Type /Catalog /Pages {pages_obj_id} 0 R >>")

    kids_refs = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_obj_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [ {kids_refs} ] >>".encode("cp1252")

    for idx, page_id in enumerate(page_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_obj_id} 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 {font_obj} 0 R /F2 {bold_font} 0 R >> >> /Contents {content_ids[idx]} 0 R >>"
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
