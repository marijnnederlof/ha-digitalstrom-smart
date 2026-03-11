"""Climate entities for Digital Strom zones.

Full thermostat control: set target temperature, switch heating/cooling modes.
PRO FEATURE - requires license key.
"""

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import DigitalStromApiError
from .const import (
    DOMAIN,
    MANUFACTURER,
    GROUP_HEATING,
    GROUP_COOLING,
    GROUP_TEMP_CONTROL,
    SCENE_OFF,
    SCENE_1,
    SCENE_2,
    SCENE_3,
    SCENE_4,
    CONF_ENABLED_ZONES,
)
from .coordinator import DigitalStromCoordinator

_LOGGER = logging.getLogger(__name__)

# dS OperationMode to HA preset
DS_PRESET_MAP = {
    0: "off",
    1: "comfort",
    2: "economy",
    4: "night",
    5: "holiday",
}

# HA preset to dS scene number (for GROUP_HEATING)
PRESET_TO_SCENE = {
    "off": SCENE_OFF,
    "comfort": SCENE_1,
    "economy": SCENE_2,
    "night": SCENE_3,
    "holiday": SCENE_4,
}

# dS ControlMode values
CONTROL_MODE_OFF = 0
CONTROL_MODE_PID = 1       # Heating
CONTROL_MODE_ZONE_FOLLOWER = 2
CONTROL_MODE_FIXED = 3
CONTROL_MODE_MANUAL = 4
CONTROL_MODE_COOLING = 11  # Cooling
CONTROL_MODE_COOL_OFF = 12


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Digital Strom climate entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DigitalStromCoordinator = data["coordinator"]
    enabled_zones = entry.data.get(CONF_ENABLED_ZONES, [])

    entities = []
    for zone_id, zone_info in coordinator.zones.items():
        if enabled_zones and zone_id not in enabled_zones:
            continue
        # Zone needs temp control data (not just dumb heating actuators)
        if coordinator.has_temp_control(zone_id):
            entities.append(
                DigitalStromClimate(coordinator, zone_id, zone_info)
            )

    async_add_entities(entities)


class DigitalStromClimate(CoordinatorEntity, ClimateEntity):
    """A Digital Strom zone thermostat with heating and cooling support."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF, HVACMode.AUTO]
    _attr_preset_modes = ["comfort", "economy", "night", "holiday"]
    _attr_min_temp = 5.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 0.5
    _enable_turn_on_off_backwards_compat = False

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
        self._attr_unique_id = f"ds_{dss_id}_{zone_id}_climate"
        self._attr_name = "Climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{dss_id}_zone_{zone_id}")},
            "name": self._zone_name,
            "manufacturer": MANUFACTURER,
            "model": "Zone",
        }

    @property
    def current_temperature(self) -> float | None:
        status = self.coordinator.get_climate_status(self._zone_id)
        if status:
            temp = status.get("TemperatureValue")
            if temp and temp > 0:
                return temp
        return self.coordinator.get_current_temperature(self._zone_id)

    @property
    def target_temperature(self) -> float | None:
        status = self.coordinator.get_climate_status(self._zone_id)
        if status:
            nv = status.get("NominalValue")
            if nv and nv > 0:
                return nv
        return self.coordinator.get_temperature(self._zone_id)

    @property
    def hvac_mode(self) -> HVACMode:
        status = self.coordinator.get_climate_status(self._zone_id)
        if status:
            op_mode = status.get("OperationMode", 0)
            if op_mode == 0:
                return HVACMode.OFF
            # Check ControlMode for heating vs cooling
            control_mode = status.get("ControlMode", CONTROL_MODE_PID)
            if control_mode in (CONTROL_MODE_COOLING, CONTROL_MODE_COOL_OFF):
                return HVACMode.COOL
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        status = self.coordinator.get_climate_status(self._zone_id)
        if status:
            op_mode = status.get("OperationMode", 0)
            if op_mode == 0:
                return HVACAction.OFF
            control_value = status.get("ControlValue", 0)
            control_mode = status.get("ControlMode", CONTROL_MODE_PID)
            if control_value > 0:
                if control_mode in (CONTROL_MODE_COOLING, CONTROL_MODE_COOL_OFF):
                    return HVACAction.COOLING
                return HVACAction.HEATING
            return HVACAction.IDLE
        return None

    @property
    def preset_mode(self) -> str | None:
        status = self.coordinator.get_climate_status(self._zone_id)
        if status:
            op_mode = status.get("OperationMode", 1)
            return DS_PRESET_MAP.get(op_mode, "comfort")
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        try:
            await self.coordinator.api.set_temperature_control_values(
                self._zone_id, temp
            )
            # Update local state
            status = self.coordinator.get_climate_status(self._zone_id)
            if status:
                status["NominalValue"] = temp
            self.async_write_ha_state()
        except DigitalStromApiError as err:
            _LOGGER.error("Failed to set temperature for %s: %s", self._zone_name, err)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (heat/cool/off/auto)."""
        if hvac_mode == HVACMode.OFF:
            scene = SCENE_OFF
        else:
            scene = SCENE_1  # Comfort
        try:
            await self.coordinator.api.call_scene(
                self._zone_id, GROUP_HEATING, scene
            )
            self.async_write_ha_state()
        except DigitalStromApiError as err:
            _LOGGER.error("Failed to set HVAC mode for %s: %s", self._zone_name, err)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set heating preset (comfort/economy/night/holiday)."""
        scene = PRESET_TO_SCENE.get(preset_mode, SCENE_1)
        try:
            await self.coordinator.api.call_scene(
                self._zone_id, GROUP_HEATING, scene
            )
            self.async_write_ha_state()
        except DigitalStromApiError as err:
            _LOGGER.error("Failed to set preset for %s: %s", self._zone_name, err)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
