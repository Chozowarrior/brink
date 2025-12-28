"""Support for the Brink-home API."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_DEVICES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .core.brink_home_cloud import BrinkHomeCloud

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SELECT,
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.SENSOR,
]

# YAML-config wordt niet meer ondersteund; alleen config entries
CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Brink-home from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    scan_interval: int = entry.options.get(
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL,
    )

    session = async_get_clientsession(hass)
    brink_client = BrinkHomeCloud(session, username, password)

    try:
        await brink_client.login()
    except asyncio.TimeoutError as ex:
        raise ConfigEntryNotReady from ex
    except aiohttp.ClientResponseError as ex:
        if ex.status == 401:
            raise ConfigEntryAuthFailed from ex
        raise ConfigEntryNotReady from ex
    except aiohttp.ClientError as ex:
        raise ConfigEntryNotReady from ex
    except Exception as ex:  # noqa: BLE001
        _LOGGER.error("Failed to set up Brink-home: %s", ex)
        return False

    async def async_update_data():
        """Fetch latest data from the Brink-home API."""
        try:
            return await async_get_devices(hass, entry, brink_client)
        except Exception:
            # Eerste poging faalt: probeer opnieuw na re-login
            try:
                await brink_client.login()
                return await async_get_devices(hass, entry, brink_client)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception(
                    "Unknown error occurred during Brink-home update request: %s",
                    err,
                )
                raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: brink_client,
        DATA_COORDINATOR: coordinator,
        DATA_DEVICES: [],
    }

    # Initiale fetch zodat entiteiten meteen data hebben
    await coordinator.async_config_entry_first_refresh()

    # Onderliggende platformen (sensor, fan, ...) opzetten
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_get_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    brink_client: BrinkHomeCloud,
):
    """Fetch data from Brink-home API."""
    # Zekerheidshalve nog een login; Brink-home sessies kunnen verlopen
    await brink_client.login()

    systems = await brink_client.get_systems()

    for system in systems:
        description = await brink_client.get_description_values(
            system["system_id"],
            system["gateway_id"],
        )

        # Basis ventilatie/algemene info
        system["ventilation"] = description["ventilation"]
        system["mode"] = description["mode"]
        system["filters_need_change"] = description["filters_need_change"]

        # Alle overige sensoren (CO2, temp, vocht, e.d.) toevoegen
        for key, value in description.items():
            system[key] = value

    hass.data[DOMAIN][entry.entry_id][DATA_DEVICES] = systems

    return systems


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
