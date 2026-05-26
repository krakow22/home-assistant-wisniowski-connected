"""Button platform for Wisniowski Connected."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up Wisniowski buttons from a config entry."""

    coordinator: WisniowskiCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        WisniowskiStepByStepButton(coordinator, channel_id)
        for channel_id, gate in (coordinator.data or {}).items()
        if coordinator.client.supports_step_by_step(gate)
    )


class WisniowskiStepByStepButton(CoordinatorEntity[WisniowskiCoordinator], ButtonEntity):
    """A step-by-step gate control button."""

    _attr_has_entity_name = True
    _attr_name = "Step by step"

    def __init__(self, coordinator: WisniowskiCoordinator, channel_id: str) -> None:
        super().__init__(coordinator)
        self._channel_id = channel_id
        gate = self.gate
        self._attr_unique_id = f"{coordinator.client.gate_unique_id(gate)}_step_by_step"
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
        """Return whether the button is available."""

        return self.gate.connection_state == "CONNECTED"

    async def async_press(self) -> None:
        """Press the step-by-step button."""

        await self.coordinator.async_step_by_step(self.gate)
