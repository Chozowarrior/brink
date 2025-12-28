"""Support for Brink ventilation CO2 sensors."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION
from homeassistant.core import HomeAssistant

from .device import BrinkHomeDeviceEntity
from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Sensor-definitie(s)
SENSOR_TYPES = {
    "co2": {
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": CONCENTRATION_PARTS_PER_MILLION,
        "icon": "mdi:molecule-co2",
        # Matcht o.a. "PPM eBus CO2-sensor 2"
        "pattern": r"co2",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the Brink CO2 sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[BrinkSensor] = []

    _LOGGER.debug("Setting up Brink ventilation sensors")
    _LOGGER.debug("Coordinator data: %s", coordinator.data)

    for device_index, device_data in enumerate(coordinator.data):
        _LOGGER.debug(
            "Device %s available keys: %s",
            device_index,
            list(device_data.keys()),
        )

        for key, value in device_data.items():
            # We verwachten dicts met minstens name + value
            if not isinstance(value, dict):
                continue
            if "name" not in value or "value" not in value:
                continue

            sensor_name: str = value.get("name", "")
            _LOGGER.debug(
                "Checking potential sensor on device %s: key=%s name=%s",
                device_index,
                key,
                sensor_name,
            )

            for sensor_type, props in SENSOR
