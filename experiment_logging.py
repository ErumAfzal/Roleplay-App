from __future__ import annotations

import hashlib
import json
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCAL_LOG_PATH = Path("logs/experiment_runs.jsonl")


def utc_now_iso() -> str:
    """Return a timezone-aware ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def create_run_id() -> str:
    """Create a globally unique identifier for one conversation run."""
    return str(uuid.uuid4())


def hash_text(text: str) -> str:
    """Return a SHA-256 hash for reproducibility checks."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_run_metadata(
    *,
    scenario_id: int,
    scenario_code: str,
    scenario_title_en: str,
    scenario_title_de: str,
    communication_type: str,
    user_social_role: str,
    partner_social_role: str,
    conversation_intention: str,
    content_goal: str,
    relationship_goal: str,
    maxim_behavior: dict[str, str],
    self_disclosure: str,
    context: dict[str, Any],
    language: str,
    student_id: str,
    batch_step: str,
    condition_id: str,
    application_version: str,
    prompt_version: str,
    roleplay_data_version: str,
    model_provider: str,
    model_name: str,
    generation_config: dict[str, Any],
    system_prompt: str,
    is_test_run: bool = False,
    trajectory_id: str | None = None,
    repetition_id: int | None = None,
) -> dict[str, Any]:
    """Build a complete metadata record at the start of one run."""
    return {
        "run_id": create_run_id(),
        "timestamp_started_utc": utc_now_iso(),
        "timestamp_completed_utc": None,
        "condition_id": condition_id,
        "application_version": application_version,
        "prompt_version": prompt_version,
        "roleplay_data_version": roleplay_data_version,
        "scenario_id": scenario_id,
        "scenario_code": scenario_code,
        "scenario_title_en": scenario_title_en,
        "scenario_title_de": scenario_title_de,
        "communication_type": communication_type,
        "user_social_role": user_social_role,
        "partner_social_role": partner_social_role,
        "conversation_intention": conversation_intention,
        "content_goal": content_goal,
        "relationship_goal": relationship_goal,
        "maxim_behavior": maxim_behavior,
        "self_disclosure": self_disclosure,
        "context": context,
        "language": language,
        "student_id": student_id,
        "batch_step": batch_step,
        "trajectory_id": trajectory_id,
        "repetition_id": repetition_id,
        "is_test_run": is_test_run,
        "model_provider": model_provider,
        "model_name": model_name,
        "generation_config": generation_config,
        "temperature": generation_config.get("temperature"),
        "top_p": generation_config.get("top_p"),
        "frequency_penalty": generation_config.get("frequency_penalty"),
        "presence_penalty": generation_config.get("presence_penalty"),
        "max_completion_tokens": generation_config.get("max_completion_tokens"),
        "system_prompt": system_prompt,
        "system_prompt_sha256": hash_text(system_prompt),
        "ontology_version": None,
        "reasoner_name": None,
        "reasoner_version": None,
        "python_version": sys.version,
        "platform": platform.platform(),
        "turn_metrics": [],
        "number_of_model_calls": 0,
        "cumulative_prompt_tokens": 0,
        "cumulative_completion_tokens": 0,
        "cumulative_total_tokens": 0,
        "total_latency_seconds": 0.0,
        "last_turn_prompt_tokens": None,
        "last_turn_completion_tokens": None,
        "last_turn_total_tokens": None,
        "last_turn_latency_seconds": None,
        "last_error_type": None,
        "last_error_message": None,
    }


def save_local_run(record: dict[str, Any]) -> None:
    """Append one complete experimental run to a JSONL file."""
    LOCAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
