"""Knopf "Pakete abgeholt": blendet die aktuellen Abholmeldungen aus."""
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AbgeholtButton(entry.runtime_data, entry)])


class AbgeholtButton(CoordinatorEntity, ButtonEntity):
    _attr_name = "Pakete abgeholt"
    _attr_icon = "mdi:package-variant-closed-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_abgeholt"
        self.entity_id = "button.pakete_abgeholt"

    async def async_press(self):
        await self.coordinator.mark_picked_up()
