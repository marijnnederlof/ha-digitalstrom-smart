"""Zone-based cover entities for digitalSTROM."""

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    GROUP_SHADE,
    SCENE_COVER_OPEN,
    SCENE_COVER_CLOSE,
    SCENE_COVER_STOP,
    SCENE_OFF,
    CONF_ENABLED_ZONES,
)
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up digitalSTROM covers."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]
    enabled_zones = entry.data.get(CONF_ENABLED_ZONES, [])

    entities = []
    for zone_id, zone_info in coordinator.zones.items():
        if enabled_zones and zone_id not in enabled_zones:
            continue
        if GROUP_SHADE in zone_info["groups"]:
            entities.append(DigitalStromCover(coordinator, zone_id, zone_info))

    async_add_entities(entities)


class DigitalStromCover(CoordinatorEntity, CoverEntity):
    """A digitalSTROM zone cover (blinds/shades)."""

    _attr_has_entity_name = True
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

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
        self._attr_unique_id = f"ds_{dss_id}_{zone_id}_cover"
        self._attr_name = "Cover"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_zone_{zone_id}")},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": "Zone",
        }

    @property
    def available(self) -> bool:
        return not self.coordinator.is_paused and super().available

    @property
    def current_cover_position(self) -> int | None:
        state = self.coordinator.get_zone_state(self._zone_id, GROUP_SHADE)
        value = state.get("value")
        if value is not None:
            # dS: 0=closed, 255=open. HA: 0=closed, 100=open
            return round(value * 100 / 255)
        return None

    @property
    def is_closed(self) -> bool | None:
        state = self.coordinator.get_zone_state(self._zone_id, GROUP_SHADE)
        scene = state.get("scene")
        if scene == SCENE_OFF or scene == SCENE_COVER_CLOSE:
            return True
        if scene == SCENE_COVER_OPEN:
            return False
        value = state.get("value")
        if value is not None:
            return value == 0
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.call_scene(
            self._zone_id, GROUP_SHADE, SCENE_COVER_OPEN
        )
        self.coordinator.set_zone_state(
            self._zone_id, GROUP_SHADE, scene=SCENE_COVER_OPEN, value=255
        )
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.call_scene(
            self._zone_id, GROUP_SHADE, SCENE_COVER_CLOSE
        )
        self.coordinator.set_zone_state(
            self._zone_id, GROUP_SHADE, scene=SCENE_COVER_CLOSE, value=0
        )
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.call_scene(
            self._zone_id, GROUP_SHADE, SCENE_COVER_STOP
        )
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION, 0)
        # HA: 0=closed, 100=open → dS: 0=closed, 255=open
        ds_value = round(position * 255 / 100)
        await self.coordinator.api.set_value(
            self._zone_id, GROUP_SHADE, ds_value
        )
        self.coordinator.set_zone_state(
            self._zone_id, GROUP_SHADE, value=ds_value
        )
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
