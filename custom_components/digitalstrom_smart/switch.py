"""Switch entities for Digital Strom - Joker (black) device control."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import DigitalStromApiError
from .const import DOMAIN, MANUFACTURER, GROUP_JOKER, CONF_ENABLED_ZONES, SCENE_OFF, SCENE_MAX
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Digital Strom switches for Joker devices."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]
    enabled_zones = entry.data.get(CONF_ENABLED_ZONES, [])

    entities = []

    # Create switches for zones with Joker (black) group devices
    for zone_id, zone_info in coordinator.zones.items():
        if enabled_zones and zone_id not in enabled_zones:
            continue
        if GROUP_JOKER in zone_info["groups"]:
            entities.append(
                DigitalStromJokerSwitch(coordinator, zone_id, zone_info)
            )

    async_add_entities(entities)


class DigitalStromJokerSwitch(CoordinatorEntity, SwitchEntity):
    """A Digital Strom Joker (black) zone switch - on/off control."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DigitalStromCoordinator,
        zone_id: int,
        zone_info: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_name = zone_info["name"]
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_{zone_id}_joker_switch"
        self._attr_name = "Switch"
        self._attr_icon = "mdi:electric-switch"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_zone_{zone_id}")},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": "Zone",
        }

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.get_zone_state(self._zone_id, GROUP_JOKER)
        return state.get("is_on")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on Joker devices in zone."""
        try:
            await self.coordinator.api.call_scene(
                self._zone_id, GROUP_JOKER, SCENE_MAX
            )
            self.coordinator.set_zone_state(
                self._zone_id, GROUP_JOKER, is_on=True, scene=SCENE_MAX
            )
            self.async_write_ha_state()
        except DigitalStromApiError as err:
            _LOGGER.error("Failed to turn on %s: %s", self._zone_name, err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off Joker devices in zone."""
        try:
            await self.coordinator.api.call_scene(
                self._zone_id, GROUP_JOKER, SCENE_OFF
            )
            self.coordinator.set_zone_state(
                self._zone_id, GROUP_JOKER, is_on=False, scene=SCENE_OFF
            )
            self.async_write_ha_state()
        except DigitalStromApiError as err:
            _LOGGER.error("Failed to turn off %s: %s", self._zone_name, err)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
