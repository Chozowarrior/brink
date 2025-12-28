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
    _LOGGER.warning("Brink CO2 sensor platform async_setup_entry called")

    client = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[BrinkSensor] = []

    _LOGGER.warning("Brink coordinator raw data: %s", coordinator.data)

    for device_index, device_data in enumerate(coordinator.data):
        _LOGGER.warning(
            "Brink device %s data keys: %s",
            device_index,
            list(device_data.keys()),
        )

        for key, value in device_data.items():
            if not isinstance(value, dict):
                continue
            if "name" not in value or "value" not in value:
                continue

            sensor_name: str = value.get("name", "")
            _LOGGER.warning(
                "Checking potential sensor on device %s: key=%s name=%s value=%s",
                device_index,
                key,
                sensor_name,
                value.get("value"),
            )

            for sensor_type, props in SENSOR_TYPES.items():
                pattern = re.compile(props["pattern"], re.IGNORECASE)

                # 1) match op key (bijv. 'co2_sensor_2')
                if pattern.search(str(key)):
                    _LOGGER.warning(
                        "Matched %s sensor by KEY on device %s: key=%s name=%s",
                        sensor_type,
                        device_index,
                        key,
                        sensor_name,
                    )
                    entities.append(
                        BrinkSensor(
                            client=client,
                            coordinator=coordinator,
                            device_index=device_index,
                            entity_name=key,
                            display_name=sensor_name,
                            device_class=props["device_class"],
                            state_class=props["state_class"],
                            unit=props["unit"],
                            icon=props["icon"],
                        )
                    )
                    continue

                # 2) match op naam (bijv. 'PPM eBus CO2-sensor 2')
                if pattern.search(sensor_name):
                    _LOGGER.warning(
                        "Matched %s sensor by NAME on device %s: key=%s name=%s",
                        sensor_type,
                        device_index,
                        key,
                        sensor_name,
                    )
                    entities.append(
                        BrinkSensor(
                            client=client,
                            coordinator=coordinator,
                            device_index=device_index,
                            entity_name=key,
                            display_name=sensor_name,
                            device_class=props["device_class"],
                            state_class=props["state_class"],
                            unit=props["unit"],
                            icon=props["icon"],
                        )
                    )

    if entities:
        _LOGGER.warning(
            "Adding %s Brink CO2 sensor entities: %s",
            len(entities),
            [e.entity_name for e in entities],
        )
        async_add_entities(entities)
    else:
        _LOGGER.warning(
            "No Brink CO2 sensors found in data. "
            "Check logged device data and patterns."
        )


class BrinkSensor(BrinkHomeDeviceEntity, SensorEntity):
    """Representation of a Brink CO2 sensor."""

    def __init__(
        self,
        client,
        coordinator,
        device_index: int,
        entity_name: str,
        display_name: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit: str | None,
        icon: str | None,
    ) -> None:
        """Initialize the Brink sensor."""
        super().__init__(client, coordinator, device_index, entity_name)
        self._display_name = display_name
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def id(self) -> str:
        """Return the ID of the sensor."""
        return f"{DOMAIN}_{self.entity_name}_{self.device_index}_sensor"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        base_name = self.coordinator.data[self.device_index].get("name", "")
        return f"{base_name} {self._display_name}".strip()

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        try:
            value = self.coordinator.data[self.device_index][self.entity_name]

            if isinstance(value, dict) and "value" in value:
                value = value["value"]

            if isinstance(value, str):
                try:
                    if "." in value:
                        return float(value)
                    return int(value)
                except (ValueError, TypeError):
                    return value

            return value
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning(
                "Error getting value for %s on device %s: %s",
                self.entity_name,
                self.device_index,
                err,
            )
            return None
