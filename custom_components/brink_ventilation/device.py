from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME, DEFAULT_MODEL


class BrinkHomeDeviceEntity(CoordinatorEntity):
    """Defines a base Brink home device entity."""

    def __init__(self, client, coordinator, device_index, entity_name):
        """Initialize the Brink home entity."""
        super().__init__(coordinator)
        self.client = client
        self.device_index = device_index
        self.entity_name = entity_name
        self.system_id = self.coordinator.data[self.device_index]["system_id"]
        self.gateway_id = self.coordinator.data[self.device_index]["gateway_id"]

    @property
    def data(self):
        """Shortcut to access data for the entity."""
        return self.coordinator.data[self.device_index][self.entity_name]

    @property
    def device_info(self):
        """Return device info for the Brink entity."""
        return {
            "identifiers": {(DOMAIN, self.system_id, self.gateway_id)},
            "name": self.data["name"],
            "manufacturer": DEFAULT_NAME,
            "model": DEFAULT_MODEL,
        }
