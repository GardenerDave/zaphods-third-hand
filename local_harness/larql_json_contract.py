from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError, JSONDecoder
from typing import Any, Mapping


@dataclass(frozen=True)
class LarqlJsonContract:
    contract_id: str
    required_keys: tuple[str, ...]
    exact_values: Mapping[str, object]
    false_values: tuple[str, ...]
    required_list_items: Mapping[str, tuple[str, ...]]
    required_prompt_phrases: tuple[str, ...]
    banned_prompt_phrases: tuple[str, ...]
    banned_response_phrases: tuple[str, ...]
    authorization_drift_phrases: tuple[str, ...] = ()


def _phrase_key(phrase: str) -> str:
    key = phrase.lower()
    for ch in " .,:;()[]{}\"'`/\n\t":
        key = key.replace(ch, "_")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


def parse_exact_json_object(raw_response: str) -> tuple[dict[str, Any] | None, dict[str, bool]]:
    text = raw_response.strip()
    checks = {
        "raw_response_is_json_object": False,
        "no_markdown_fence": "```" not in text,
        "no_prose_outside_json": False,
    }
    if not text or "```" in text:
        return None, checks
    try:
        obj, end = JSONDecoder().raw_decode(text)
    except JSONDecodeError:
        return None, checks
    if not isinstance(obj, dict):
        return None, checks
    if text[end:].strip():
        return None, checks
    checks["raw_response_is_json_object"] = True
    checks["no_prose_outside_json"] = True
    return obj, checks


def score_json_contract_response(raw_response: str, contract: LarqlJsonContract) -> dict[str, bool]:
    parsed, parse_checks = parse_exact_json_object(raw_response)
    if parsed is None:
        return {
            **parse_checks,
            **{f"has_{key}": False for key in contract.required_keys},
            **{f"exact_value_{key}_matches": False for key in contract.exact_values},
            **{f"false_value_{key}_is_false": False for key in contract.false_values},
            **{
                f"required_list_item_{field}_{_phrase_key(item)}_present": False
                for field, items in contract.required_list_items.items()
                for item in items
            },
            **{f"response_has_banned_phrase_{_phrase_key(phrase)}": True for phrase in contract.banned_response_phrases},
            **{
                f"response_has_authorization_drift_phrase_{_phrase_key(phrase)}": True
                for phrase in contract.authorization_drift_phrases
            },
        }

    lowered = raw_response.lower()
    response_lists = {
        key: parsed.get(key) if isinstance(parsed.get(key), list) else []
        for key in contract.required_list_items
    }
    checks = {
        **parse_checks,
        **{f"has_{key}": key in parsed for key in contract.required_keys},
        **{f"exact_value_{key}_matches": parsed.get(key) == value for key, value in contract.exact_values.items()},
        **{f"false_value_{key}_is_false": parsed.get(key) is False for key in contract.false_values},
        **{
            f"required_list_item_{field}_{_phrase_key(item)}_present": item in response_lists.get(field, [])
            for field, items in contract.required_list_items.items()
            for item in items
        },
        **{
            f"response_has_banned_phrase_{_phrase_key(phrase)}": phrase.lower() not in lowered
            for phrase in contract.banned_response_phrases
        },
        **{
            f"response_has_authorization_drift_phrase_{_phrase_key(phrase)}": phrase.lower() not in lowered
            for phrase in contract.authorization_drift_phrases
        },
    }
    return checks


def check_json_contract_prompt(prompt: str, contract: LarqlJsonContract) -> dict[str, bool]:
    lowered = prompt.lower()
    return {
        "prompt_has_required_phrase_return_one_json_object_only": "return one json object only" in lowered,
        "prompt_has_required_phrase_no_markdown": "no markdown" in lowered,
        "prompt_has_required_phrase_no_prose_outside_json": "no prose outside json" in lowered,
        **{
            f"prompt_has_required_phrase_{_phrase_key(phrase)}": phrase.lower() in lowered
            for phrase in contract.required_prompt_phrases
        },
        **{
            f"prompt_has_banned_phrase_{_phrase_key(phrase)}": phrase.lower() not in lowered
            for phrase in contract.banned_prompt_phrases
        },
    }


def all_checks_pass(checks: Mapping[str, bool]) -> bool:
    return all(bool(value) for value in checks.values())
