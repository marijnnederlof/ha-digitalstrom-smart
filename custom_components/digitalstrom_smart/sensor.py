"""Sensor entities for digitalSTROM (temperature + energy)."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, CONF_ENABLED_ZONES
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up digitalSTROM sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]
    enabled_zones = entry.data.get(CONF_ENABLED_ZONES, [])

    entities: list[SensorEntity] = []

    # Apartment energy sensor (always added)
    entities.append(DigitalStromEnergySensor(coordinator))

    # Temperature sensor per zone (if zone has temp data)
    for zone_id, zone_info in coordinator.zones.items():
        if enabled_zones and zone_id not in enabled_zones:
            continue
        # Add temp sensor if we have temperature data for this zone
        if coordinator.get_temperature(zone_id) is not None:
            entities.append(
                DigitalStromTemperatureSensor(coordinator, zone_id, zone_info)
            )

    async_add_entities(entities)


class DigitalStromEnergySensor(CoordinatorEntity, SensorEntity):
    """Apartment-level power consumption sensor."""

    _attr_has_entity_name = True
    _attr_name = "dSS Power Consumption"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    def __init__(self, coordinator: DigitalStromCoordinator) -> None:
        super().__init__(coordinator)
        dss_id = coordinator.dss_id
        self._attr_unique_id = f"ds_{dss_id}_apartment_consumption"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_apartment")},
            "name": "digitalSTROM Apartment",
            "manufacturer": MANUFACTURER,
            "model": "dSS",
        }

    @property
    def available(self) -> bool:
        return not self.coordinator.is_paused and super().available

    @property
    def native_value(self) -> int | None:
        return self.coordinator.consumption

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class DigitalStromTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Zone temperature sensor (from getTemperatureControlValues)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

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
        self._attr_unique_id = f"ds_{dss_id}_{zone_id}_temperature"
        self._attr_name = "Temperature"
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
    def native_value(self) -> float | None:
        return self.coordinator.get_temperature(self._zone_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
