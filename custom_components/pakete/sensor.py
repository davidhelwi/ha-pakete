"""sensor.pakete_heute, _unterwegs, _abholen, _zugestellt (heute); Liste im Attribut "pakete"."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .parcels import ABHOLEN, HEUTE, UNTERWEGS, ZUGESTELLT


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([
        PaketSensor(c, entry, HEUTE, "Pakete heute", "mdi:truck-fast"),
        PaketSensor(c, entry, UNTERWEGS, "Pakete unterwegs", "mdi:truck-delivery"),
        PaketSensor(c, entry, ABHOLEN, "Pakete abholen", "mdi:package-variant-closed-check"),
        PaketSensor(c, entry, ZUGESTELLT, "Pakete zugestellt", "mdi:package-variant"),
    ])


class PaketSensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = "Pakete"

    def __init__(self, coordinator, entry, key, name, icon):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self.entity_id = f"sensor.pakete_{key}"

    @property
    def native_value(self):
        return len(self.coordinator.data[self._key])

    @property
    def extra_state_attributes(self):
        return {"pakete": self.coordinator.data[self._key]}
