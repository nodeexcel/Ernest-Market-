"""Configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependencies import get_settings
from api.schemas import AppSettingsResponse, BuyRuleSchema, MessageResponse, RulesConfigResponse
from api.services.config_service import load_raw_rules, rules_to_dicts, save_rules, validate_rules_payload
from src.config_loader import ConfigError

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/rules", response_model=RulesConfigResponse)
def get_rules() -> RulesConfigResponse:
    settings = get_settings()
    try:
        rules = load_raw_rules(settings.config_path)
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RulesConfigResponse(
        rules=[BuyRuleSchema(**entry) for entry in rules_to_dicts(rules)],
        rule_count=len(rules),
    )


@router.put("/rules", response_model=MessageResponse)
def update_rules(body: RulesConfigResponse) -> MessageResponse:
    settings = get_settings()
    payload = [rule.model_dump() for rule in body.rules]

    try:
        validate_rules_payload(payload)
        save_rules(settings.config_path, payload)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return MessageResponse(
        message="Buy rules saved successfully.",
        detail={"rule_count": len(body.rules)},
    )


@router.get("/settings", response_model=AppSettingsResponse)
def get_app_settings() -> AppSettingsResponse:
    settings = get_settings()
    return AppSettingsResponse(
        poll_interval_minutes=settings.poll_interval_minutes,
        rules_per_run=settings.rules_per_run,
        max_alerts_per_run=settings.max_alerts_per_run,
        max_price_tolerance_percent=settings.max_price_tolerance_percent,
        rule_search_delay_seconds=settings.rule_search_delay_seconds,
        ebay_backend=settings.ebay_backend,
        ebay_marketplace_id=settings.ebay_marketplace_id,
        google_sheets_configured=settings.google_credentials_path.exists(),
        telegram_configured=bool(settings.telegram_bot_token and settings.telegram_channel_id),
    )
