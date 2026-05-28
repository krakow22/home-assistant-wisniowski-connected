"""Diagnostic binary sensors for Wisniowski Connected."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WisniowskiGate
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import WisniowskiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic binary sensors."""

    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: WisniowskiCoordinator = runtime[DATA_COORDINATOR]
    gates = list((coordinator.data or {}).values())
    primary_gate = gates[0] if gates else None

    entities: list[BinarySensorEntity] = [
        WisniowskiCloudApiAuthenticatedSensor(coordinator, primary_gate),
    ]
    entities.extend(WisniowskiGateCloudConnectedSensor(coordinator, gate) for gate in gates)
    async_add_entities(entities)


class WisniowskiDiagnosticBinarySensor(CoordinatorEntity[WisniowskiCoordinator], BinarySensorEntity):
    """Base class for Wisniowski diagnostic binary sensors."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def _set_device_info(self, gate: WisniowskiGate | None) -> None:
        if gate is None:
            return
        self._attr_device_info = {
            "identifiers": {(DOMAIN, gate.device_id)},
            "manufacturer": "Wisniowski",
            "model": gate.model or "Connected gate",
            "name": gate.device_name or gate.name,
        }


class WisniowskiCloudApiAuthenticatedSensor(WisniowskiDiagnosticBinarySensor):
    """Report whether the last cloud API refresh was authenticated and successful."""

    _attr_name = "Cloud API authenticated"

    def __init__(self, coordinator: WisniowskiCoordinator, gate: WisniowskiGate | None) -> None:
        super().__init__(coordinator)
        if gate is not None:
            self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_cloud_api_authenticated"
        else:
            self._attr_unique_id = f"{DOMAIN}_cloud_api_authenticated"
        self._set_device_info(gate)

    @property
    def is_on(self) -> bool:
        """Return whether the last API check succeeded."""

        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic cloud status attributes."""

        last_exception = getattr(self.coordinator, "last_exception", None)
        return {
            "broker_url": self.coordinator.client.broker_url,
            "gate_count": len(self.coordinator.data or {}),
            "installation_id": self.coordinator.client.installation_id,
            "last_exception": str(last_exception) if last_exception else None,
        }


class WisniowskiGateCloudConnectedSensor(WisniowskiDiagnosticBinarySensor):
    """Report whether a gate module is connected to the vendor cloud."""

    _attr_name = "Gate cloud connection"

    def __init__(self, coordinator: WisniowskiCoordinator, gate: WisniowskiGate) -> None:
        super().__init__(coordinator)
        self._channel_id = gate.channel_id
        self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_gate_cloud_connection"
        self._set_device_info(gate)

    @property
    def is_on(self) -> bool | None:
        """Return whether the gate module is connected to the cloud."""

        gate = self.coordinator.data.get(self._channel_id) if self.coordinator.data else None
        if gate is None:
            return None
        return gate.connection_state == "CONNECTED"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return current non-sensitive gate cloud attributes."""

        gate = self.coordinator.data.get(self._channel_id) if self.coordinator.data else None
        if gate is None:
            return {}
        return {
            "connection_state": gate.connection_state,
            "direction": gate.direction,
            "position": gate.position,
        }
