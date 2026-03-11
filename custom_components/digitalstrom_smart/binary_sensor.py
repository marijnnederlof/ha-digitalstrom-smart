"""Binary sensor entities for Digital Strom.

Rain detection from outdoor weather station.
PRO FEATURE - requires license key.
"""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Digital Strom binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]

    entities = []

    # Rain detection from outdoor weather data
    if coordinator.outdoor_sensors and "rain" in coordinator.outdoor_sensors:
        entities.append(DigitalStromRainSensor(coordinator))

    async_add_entities(entities)


class DigitalStromRainSensor(CoordinatorEntity, BinarySensorEntity):
    """Rain detection binary sensor from dSS weather station."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_name = "Rain"

    def __init__(self, coordinator: DigitalStromCoordinator) -> None:
        super().__init__(coordinator)
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_outdoor_rain_binary"
        self._attr_icon = "mdi:weather-rainy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_apartment")},
            "name": "Digital Strom Server",
            "manufacturer": MANUFACTURER,
            "model": "dSS",
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if it is raining (rain value > 0)."""
        data = self.coordinator.outdoor_sensors.get("rain", {})
        value = data.get("value")
        if value is not None:
            return float(value) > 0
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
