import imaplib

import voluptuous as vol

from homeassistant import config_entries

from .coordinator import DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("port", default=993): int,
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Required("folders", default="INBOX"): str,
    }
)


def _check(data):
    with imaplib.IMAP4_SSL(data["host"], data["port"], timeout=20) as imap:
        imap.login(data["username"], data["password"])


class PaketeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["username"].lower())
            self._abort_if_unique_id_configured()
            try:
                await self.hass.async_add_executor_job(_check, user_input)
            except imaplib.IMAP4.error:
                errors["base"] = "invalid_auth"
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input["username"], data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
