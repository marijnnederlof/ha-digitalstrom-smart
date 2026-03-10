"""Scene entities for digitalSTROM zones."""

import logging

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DigitalStromApiError
from .const import (
    DOMAIN,
    MANUFACTURER,
    GROUP_LIGHT,
    NAMED_SCENES,
    CONF_ENABLED_ZONES,
)
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up digitalSTROM scenes."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]
    enabled_zones = entry.data.get(CONF_ENABLED_ZONES, [])

    entities = []
    for zone_id, zone_info in coordinator.zones.items():
        if enabled_zones and zone_id not in enabled_zones:
            continue
        # Create scene entities for standard dS scenes
        for scene_nr, scene_name in NAMED_SCENES.items():
            entities.append(
                DigitalStromScene(
                    coordinator, zone_id, zone_info, scene_nr, scene_name
                )
            )

    async_add_entities(entities)


class DigitalStromScene(Scene):
    """A digitalSTROM scene (primary automation method)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DigitalStromCoordinator,
        zone_id: int,
        zone_info: dict,
        scene_number: int,
        scene_name: str,
    ) -> None:
        self._coordinator = coordinator
        self._zone_id = zone_id
        self._zone_name = zone_info["name"]
        self._scene_number = scene_number
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_{zone_id}_scene_{scene_number}"
        self._attr_name = scene_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_zone_{zone_id}")},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": "Zone",
        }

    async def async_activate(self, **kwargs) -> None:
        """Activate the scene."""
        try:
            await self._coordinator.api.call_scene(
                self._zone_id, GROUP_LIGHT, self._scene_number
            )
        except DigitalStromApiError as err:
            _LOGGER.error(
                "Failed to activate scene %s in zone %s: %s",
                self._scene_number,
                self._zone_name,
                err,
            )
