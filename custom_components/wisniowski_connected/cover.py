"""Cover platform for Wisniowski Connected gates."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import ATTR_POSITION, CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
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
    """Set up Wisniowski gate covers from a config entry."""

    coordinator: WisniowskiCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        WisniowskiGateCover(coordinator, channel_id)
        for channel_id in (coordinator.data or {})
    )


class WisniowskiGateCover(CoordinatorEntity[WisniowskiCoordinator], CoverEntity):
    """A Wisniowski Connected gate channel."""

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_has_entity_name = False

    def __init__(self, coordinator: WisniowskiCoordinator, channel_id: str) -> None:
        super().__init__(coordinator)
        self._channel_id = channel_id
        gate = self.gate
        self._attr_name = gate.name
        self._attr_unique_id = coordinator.client.gate_unique_id(gate)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, gate.device_id)},
            "manufacturer": "Wisniowski",
            "model": gate.model or "Connected gate",
            "name": gate.device_name or gate.name,
        }

    @property
    def gate(self) -> WisniowskiGate:
        """Return current gate data."""

        return self.coordinator.data[self._channel_id]

    @property
    def available(self) -> bool:
        """Return whether the gate is available."""

        return self.gate.connection_state == "CONNECTED"

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Return supported cover features for this gate."""

        gate = self.gate
        features = CoverEntityFeature(0)
        if self.coordinator.client.supports_set_direction(gate) or self.coordinator.client.supports_step_by_step(gate):
            features |= CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self.coordinator.client.supports_set_position(gate):
            features |= CoverEntityFeature.SET_POSITION
        return features

    @property
    def is_closed(self) -> bool | None:
        """Return whether the gate is closed."""

        direction = self.gate.direction
        if direction == "CLOSED":
            return True
        if direction == "OPEN":
            return False
        if self.gate.position is not None:
            return self.gate.position >= 100
        return None

    @property
    def is_opening(self) -> bool:
        """Return whether the gate is opening."""

        return self.gate.direction == "OPENING"

    @property
    def is_closing(self) -> bool:
        """Return whether the gate is closing."""

        return self.gate.direction == "CLOSING"

    @property
    def current_cover_position(self) -> int | None:
        """Return current gate position."""

        if self.gate.position is None:
            if self.gate.direction == "CLOSED":
                return 0
            if self.gate.direction == "OPEN":
                return 100
            return None
        return max(0, min(100, 100 - self.gate.position))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra diagnostic attributes."""

        gate = self.gate
        return {
            "channel_id": gate.channel_id,
            "device_id": gate.device_id,
            "direction": gate.direction,
            "lock_status": gate.lock_status,
            "gate_mode": gate.gate_mode,
            "connection_state": gate.connection_state,
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the gate."""

        if self.coordinator.client.supports_set_direction(self.gate):
            await self.coordinator.async_open(self.gate)
        elif self.is_closed:
            await self.coordinator.async_step_by_step(self.gate)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the gate."""

        if self.coordinator.client.supports_set_direction(self.gate):
            await self.coordinator.async_close(self.gate)
        elif self.is_closed is False:
            await self.coordinator.async_step_by_step(self.gate)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the gate."""

        if self.coordinator.client.supports_set_direction(self.gate):
            await self.coordinator.async_stop_cover(self.gate)
        else:
            await self.coordinator.async_step_by_step(self.gate)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set gate position."""

        if ATTR_POSITION in kwargs and self.coordinator.client.supports_set_position(self.gate):
            await self.coordinator.async_set_position(self.gate, int(kwargs[ATTR_POSITION]))
