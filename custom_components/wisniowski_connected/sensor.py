"""Diagnostic sensors for Wisniowski Connected."""

from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime
import json
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WisniowskiGate
from .const import (
    CONF_EXPIRES_AT,
    CONF_REFRESH_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_TOKEN_UPDATED_AT,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
)
from .coordinator import WisniowskiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic sensors."""

    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: WisniowskiCoordinator = runtime[DATA_COORDINATOR]
    client = runtime[DATA_CLIENT]

    gate = next(iter((coordinator.data or {}).values()), None)
    async_add_entities(
        [
            WisniowskiTokenExpirySensor(
                coordinator,
                gate,
                "Access token expires",
                "access_token_expires",
                _timestamp_from_epoch(client.data.get(CONF_EXPIRES_AT)),
            ),
            WisniowskiRefreshTokenExpirySensor(
                coordinator,
                gate,
                "Refresh token expires",
                "refresh_token_expires",
                client.data.get(CONF_REFRESH_TOKEN),
            ),
            WisniowskiTokenTimestampSensor(
                coordinator,
                gate,
                "Refresh token updated",
                "refresh_token_updated",
                CONF_REFRESH_TOKEN_UPDATED_AT,
            ),
        ]
    )


class WisniowskiTokenExpirySensor(CoordinatorEntity[WisniowskiCoordinator], SensorEntity):
    """Token expiry diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WisniowskiCoordinator,
        gate: WisniowskiGate | None,
        name: str,
        suffix: str,
        value: datetime | None,
    ) -> None:
        super().__init__(coordinator)
        self._value = value
        self._attr_name = name
        if gate is not None:
            self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_{suffix}"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, gate.device_id)},
                "manufacturer": "Wisniowski",
                "model": gate.model or "Connected gate",
                "name": gate.device_name or gate.name,
            }
        else:
            self._attr_unique_id = f"{DOMAIN}_{suffix}"

    @property
    def native_value(self) -> datetime | None:
        """Return token expiration timestamp."""

        return _timestamp_from_epoch(self.coordinator.client.data.get(CONF_EXPIRES_AT)) or self._value


class WisniowskiRefreshTokenExpirySensor(CoordinatorEntity[WisniowskiCoordinator], SensorEntity):
    """Refresh token expiry diagnostic sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WisniowskiCoordinator,
        gate: WisniowskiGate | None,
        name: str,
        suffix: str,
        token: Any,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._initial_token = token
        if gate is not None:
            self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_{suffix}"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, gate.device_id)},
                "manufacturer": "Wisniowski",
                "model": gate.model or "Connected gate",
                "name": gate.device_name or gate.name,
            }
        else:
            self._attr_unique_id = f"{DOMAIN}_{suffix}"

    @property
    def native_value(self) -> str | datetime | None:
        """Return refresh token expiry status."""

        if expires_at := _timestamp_from_epoch(self.coordinator.client.data.get(CONF_REFRESH_EXPIRES_AT)):
            return expires_at
        metadata = _jwt_metadata(self.coordinator.client.data.get(CONF_REFRESH_TOKEN) or self._initial_token)
        if metadata["expires_at"] is not None:
            return metadata["expires_at"]
        return metadata["status"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return non-sensitive refresh token metadata."""

        metadata = _jwt_metadata(self.coordinator.client.data.get(CONF_REFRESH_TOKEN) or self._initial_token)
        response_expires_at = _timestamp_from_epoch(self.coordinator.client.data.get(CONF_REFRESH_EXPIRES_AT))
        expiry_source = "token_response" if response_expires_at is not None else "token_claims"
        if metadata["expires_at"] is None and expiry_source == "token_claims":
            expiry_source = "not_exposed"
        return {
            "expiry_known": response_expires_at is not None or metadata["expires_at"] is not None,
            "expiry_source": expiry_source,
            "token_format": metadata["format"],
            "claim_names": metadata["claim_names"],
        }


class WisniowskiTokenTimestampSensor(CoordinatorEntity[WisniowskiCoordinator], SensorEntity):
    """Token timestamp diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WisniowskiCoordinator,
        gate: WisniowskiGate | None,
        name: str,
        suffix: str,
        data_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._data_key = data_key
        if gate is not None:
            self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_{suffix}"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, gate.device_id)},
                "manufacturer": "Wisniowski",
                "model": gate.model or "Connected gate",
                "name": gate.device_name or gate.name,
            }
        else:
            self._attr_unique_id = f"{DOMAIN}_{suffix}"

    @property
    def native_value(self) -> datetime | None:
        """Return token timestamp."""

        return _timestamp_from_epoch(self.coordinator.client.data.get(self._data_key))


def _timestamp_from_epoch(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OSError):
        return None


def _timestamp_from_jwt(token: Any) -> datetime | None:
    return _jwt_metadata(token)["expires_at"]


def _jwt_metadata(token: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "claim_names": [],
        "expires_at": None,
        "format": "missing",
        "status": "Missing",
    }
    if not isinstance(token, str):
        return result
    parts = token.split(".")
    if len(parts) < 2:
        result["format"] = "opaque"
        result["status"] = "Not exposed by provider"
        return result
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
    except (binascii.Error, ValueError, TypeError):
        result["format"] = "invalid_jwt"
        result["status"] = "Invalid token metadata"
        return result

    result["format"] = "jwt"
    result["claim_names"] = sorted(str(key) for key in data)
    result["expires_at"] = _timestamp_from_epoch(data.get("exp"))
    if result["expires_at"] is None:
        result["status"] = "Not exposed by provider"
    else:
        result["status"] = "Known"
    return result
