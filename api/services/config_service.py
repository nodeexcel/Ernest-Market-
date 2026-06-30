"""Read and write buy rules in config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.config_loader import BuyRule, ConfigError, _parse_rule, load_config


def rules_to_dicts(rules: list[BuyRule]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for rule in rules:
        entry: dict[str, Any] = {
            "keyword": rule.keyword,
            "max_price": rule.max_price,
            "min_price": rule.min_price,
            "match_in": rule.match_in,
        }
        if rule.exclude_words:
            entry["exclude_words"] = list(rule.exclude_words)
        result.append(entry)
    return result


def load_raw_rules(path: Path) -> list[BuyRule]:
    """Load buy rules from config.yaml."""
    config = load_config(path)
    return list(config.rules)


def save_rules(path: Path, rules_payload: list[dict[str, Any]]) -> list[BuyRule]:
    validated: list[BuyRule] = []
    for index, raw in enumerate(rules_payload):
        validated.append(_parse_rule(raw, index))

    data = {"rules": rules_to_dicts(validated)}
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return validated


def validate_rules_payload(rules_payload: list[dict[str, Any]]) -> None:
    for index, raw in enumerate(rules_payload):
        _parse_rule(raw, index)
