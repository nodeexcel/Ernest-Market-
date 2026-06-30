"""YAML configuration loader for buy rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.listing import VALID_MARKETPLACES


class ConfigError(ValueError):
    """Raised when config.yaml is missing or invalid."""


@dataclass(frozen=True)
class BuyRule:
    keyword: str
    max_price: float
    min_price: float = 0.0
    match_in: str = "title"
    exclude_words: list[str] = field(default_factory=list)
    marketplace: str = "ebay"

    def __post_init__(self) -> None:
        if not self.keyword.strip():
            raise ConfigError("Each rule must have a non-empty keyword.")
        if self.max_price <= 0:
            raise ConfigError(f"max_price must be > 0 for keyword {self.keyword!r}.")
        if self.min_price < 0:
            raise ConfigError(f"min_price must be >= 0 for keyword {self.keyword!r}.")
        if self.min_price > self.max_price:
            raise ConfigError(
                f"min_price ({self.min_price}) cannot exceed max_price ({self.max_price}) "
                f"for keyword {self.keyword!r}."
            )
        if self.match_in not in {"title", "title_and_description"}:
            raise ConfigError(
                f"match_in must be 'title' or 'title_and_description' for keyword {self.keyword!r}."
            )
        if self.marketplace not in VALID_MARKETPLACES:
            raise ConfigError(
                f"marketplace must be 'ebay' for keyword {self.keyword!r}."
            )


@dataclass(frozen=True)
class AppConfig:
    rules: list[BuyRule]


def _parse_rule(raw: dict[str, Any], index: int) -> BuyRule:
    if not isinstance(raw, dict):
        raise ConfigError(f"Rule at index {index} must be a mapping.")

    keyword = str(raw.get("keyword", "")).strip()
    if "max_price" not in raw:
        raise ConfigError(f"Rule at index {index} ({keyword!r}) is missing max_price.")

    try:
        max_price = float(raw["max_price"])
        min_price = float(raw.get("min_price", 0))
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid price in rule at index {index} ({keyword!r}).") from exc

    exclude_raw = raw.get("exclude_words", [])
    if exclude_raw is None:
        exclude_words: list[str] = []
    elif not isinstance(exclude_raw, list):
        raise ConfigError(f"exclude_words must be a list for rule {keyword!r}.")
    else:
        exclude_words = [str(word).strip().lower() for word in exclude_raw if str(word).strip()]

    marketplace = str(raw.get("marketplace", "ebay")).strip().lower()
    if marketplace != "ebay":
        raise ConfigError(
            f"Only eBay is supported. Rule {keyword!r} has marketplace={marketplace!r}."
        )

    return BuyRule(
        keyword=keyword,
        max_price=max_price,
        min_price=min_price,
        match_in=str(raw.get("match_in", "title")).strip().lower(),
        exclude_words=exclude_words,
        marketplace="ebay",
    )


def load_config(path: Path) -> AppConfig:
    """Load and validate buy rules from a YAML file."""
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}. Copy config.example.yaml to config.yaml and edit it."
        )

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ConfigError("config.yaml root must be a mapping.")

    rules_raw = data.get("rules")
    if not rules_raw:
        raise ConfigError("config.yaml must contain at least one entry under 'rules'.")
    if not isinstance(rules_raw, list):
        raise ConfigError("'rules' must be a list.")

    rules = [_parse_rule(item, index) for index, item in enumerate(rules_raw)]
    return AppConfig(rules=rules)
