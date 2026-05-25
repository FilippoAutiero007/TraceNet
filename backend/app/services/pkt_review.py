from __future__ import annotations

import json
import logging

from mistralai import Mistral
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.models.schemas import PktAnalysisResponse, PktReviewResult
from app.services.rag_knowledge import PKT_REVIEW_DOCUMENTS, retrieve_relevant_documents

logger = logging.getLogger(__name__)


class PktReviewSchema(BaseModel):
    overview: str
    things_correct: list[str] = Field(default_factory=list)
    things_to_fix: list[str] = Field(default_factory=list)
    alignment_with_exercise: str | None = None


SYSTEM_PROMPT = """You are a network reviewer for Cisco Packet Tracer projects.
You must return exactly one JSON object with this schema:
{
  "overview": "short paragraph",
  "things_correct": ["bullet", "bullet"],
  "things_to_fix": ["bullet", "bullet"],
  "alignment_with_exercise": "short paragraph or null"
}
Rules:
- Be concrete and technically specific.
- Use the analyzer findings as primary evidence.
- If exercise_text exists, compare the imported file against it.
- Mention both strengths and corrections.
- Never return markdown. JSON only.
"""


def _fallback_review(analysis: PktAnalysisResponse, exercise_text: str | None) -> PktReviewResult:
    good_points: list[str] = []
    fix_points: list[str] = []

    if analysis.device_count > 0:
        good_points.append(f"La topologia contiene {analysis.device_count} dispositivi analizzabili.")
    if analysis.link_count > 0:
        good_points.append(f"Sono presenti {analysis.link_count} collegamenti nel file importato.")
    if analysis.issue_count == 0:
        good_points.append("Non sono emersi errori strutturali evidenti dal controllo automatico.")

    for issue in analysis.issues:
        target = " ".join(part for part in [issue.device, issue.interface] if part)
        prefix = f"{target}: " if target else ""
        fix_points.append(f"{prefix}{issue.message}")

    if not good_points:
        good_points.append("Il file .pkt è stato letto correttamente e può essere confrontato con i requisiti.")
    if not fix_points:
        fix_points.append("Non sono state rilevate correzioni obbligatorie dal controllo automatico.")

    alignment = None
    if exercise_text:
        alignment = (
            "Confronta i punti sopra con il testo dell'esercizio: il controllo automatico conferma lo stato "
            "tecnico del file, ma i requisiti funzionali vanno verificati rispetto alla consegna fornita."
        )

    return PktReviewResult(
        source="fallback",
        exercise_context_provided=bool(exercise_text and exercise_text.strip()),
        overview=analysis.summary or "Revisione tecnica del file Packet Tracer completata.",
        things_correct=good_points[:6],
        things_to_fix=fix_points[:8],
        alignment_with_exercise=alignment,
    )


def review_pkt_analysis(analysis: PktAnalysisResponse, exercise_text: str | None) -> PktReviewResult:
    api_key = settings.mistral_api_key.get_secret_value() if settings.mistral_api_key else None
    if not api_key:
        return _fallback_review(analysis, exercise_text)

    retrieved_docs = retrieve_relevant_documents(
        [
            exercise_text or "",
            analysis.summary or "",
            analysis.report or "",
            " ".join(issue.code for issue in analysis.issues),
        ],
        PKT_REVIEW_DOCUMENTS,
        limit=3,
    )

    payload = {
        "exercise_text": exercise_text,
        "analysis_summary": analysis.summary,
        "analysis_report": analysis.report,
        "issues": [issue.model_dump() for issue in analysis.issues],
        "device_count": analysis.device_count,
        "link_count": analysis.link_count,
        "knowledge_base": retrieved_docs,
    }

    client = Mistral(api_key=api_key)
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        validated = PktReviewSchema.model_validate(json.loads(raw_content))
        return PktReviewResult(
            source="mistral",
            exercise_context_provided=bool(exercise_text and exercise_text.strip()),
            overview=validated.overview,
            things_correct=validated.things_correct,
            things_to_fix=validated.things_to_fix,
            alignment_with_exercise=validated.alignment_with_exercise,
        )
    except (json.JSONDecodeError, ValidationError, Exception) as exc:  # noqa: BLE001
        logger.error("Pro pkt review failed: %s", exc, exc_info=True)
        return _fallback_review(analysis, exercise_text)
