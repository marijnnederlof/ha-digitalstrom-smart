"""Apartment system state entities for Digital Strom. PRO feature.

Provides:
- Presence mode select (Present/Absent/Sleeping/Wakeup/Standby/Deep Off)
- Alarm switches (Alarm 1-4, Panic)
"""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    APARTMENT_PRESENCE_SCENES,
    APARTMENT_ALARM_SCENES,
)
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Digital Strom apartment state entities (PRO)."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]

    if not coordinator.pro_enabled:
        return

    entities = []

    # Presence mode select
    entities.append(DigitalStromPresenceSelect(coordinator))

    # Alarm switches
    for scene_nr, name in APARTMENT_ALARM_SCENES.items():
        entities.append(DigitalStromAlarmSwitch(coordinator, scene_nr, name))

    async_add_entities(entities)


class DigitalStromPresenceSelect(CoordinatorEntity, SelectEntity):
    """Apartment presence mode: Present, Absent, Sleeping, etc."""

    _attr_has_entity_name = True
    _attr_name = "Presence Mode"
    _attr_icon = "mdi:home-account"

    def __init__(self, coordinator: DigitalStromCoordinator) -> None:
        super().__init__(coordinator)
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_apartment_presence"
        self._attr_options = list(APARTMENT_PRESENCE_SCENES.values())
        self._scene_to_name = APARTMENT_PRESENCE_SCENES
        self._name_to_scene = {v: k for k, v in APARTMENT_PRESENCE_SCENES.items()}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_apartment")},
            "name": "Digital Strom Server",
            "manufacturer": MANUFACTURER,
            "model": "dSS",
        }

    @property
    def current_option(self) -> str | None:
        scene = self.coordinator.apartment_presence
        if scene is not None:
            return self._scene_to_name.get(scene)
        return None

    async def async_select_option(self, option: str) -> None:
        scene_nr = self._name_to_scene.get(option)
        if scene_nr is not None:
            await self.coordinator.call_apartment_scene(scene_nr)
            self.coordinator.set_apartment_presence(scene_nr)
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class DigitalStromAlarmSwitch(CoordinatorEntity, SwitchEntity):
    """Apartment alarm switch: Alarm 1-4, Panic."""

    _attr_has_entity_name = True

    _ICONS = {
        "Alarm 1": "mdi:alarm-light",
        "Alarm 2": "mdi:alarm-light-outline",
        "Alarm 3": "mdi:fire",
        "Alarm 4": "mdi:alert",
        "Panic": "mdi:alert-octagon",
    }

    def __init__(
        self, coordinator: DigitalStromCoordinator, scene_nr: int, name: str,
    ) -> None:
        super().__init__(coordinator)
        self._scene_nr = scene_nr
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_apartment_alarm_{scene_nr}"
        self._attr_name = name
        self._attr_icon = self._ICONS.get(name, "mdi:alarm-light")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_apartment")},
            "name": "Digital Strom Server",
            "manufacturer": MANUFACTURER,
            "model": "dSS",
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_alarm_active(self._scene_nr)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.call_apartment_scene(self._scene_nr)
        self.coordinator.apartment_alarms.add(self._scene_nr)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.undo_apartment_scene(self._scene_nr)
        self.coordinator.apartment_alarms.discard(self._scene_nr)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
