"""Pakete: Amazon, DHL, DPD, Hermes aus den Versandmails (heute / unterwegs)."""
from homeassistant.const import Platform

from .coordinator import PaketeCoordinator

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass, entry):
    conf = {**entry.data, "folders": [f.strip() for f in entry.data["folders"].split(",") if f.strip()]}
    coordinator = PaketeCoordinator(hass, conf)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
