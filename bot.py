```python
import os
import asyncio
import aiohttp
import discord

from discord import app_commands
from discord.ext import tasks
from mcstatus import JavaServer

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_ROLE_ID = int(os.environ["ALLOWED_ROLE_ID"])
MINECRAFT_ADDRESS = os.environ["MINECRAFT_ADDRESS"]

intents = discord.Intents.default()


async def get_server_status():
    try:
        server = JavaServer.lookup(MINECRAFT_ADDRESS)
        status = await asyncio.wait_for(
            server.async_status(),
            timeout=5
        )

        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "version": status.version.name
        }

    except Exception as error:
        print(f"Status check failed: {error}")
        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown"
        }


def has_manager_role(interaction):
    return (
        isinstance(interaction.user, discord.Member)
        and any(
            role.id == ALLOWED_ROLE_ID
            for role in interaction.user.roles
        )
    )


class ServerPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="START SERVER",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="noxora:start"
    )
    async def start_server(self, interaction, button):

        if not has_manager_role(interaction):
            await interaction.response.send_message(
                "🛡️ Server Manager role required!",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        url = (
            f"{PANEL_URL}/api/client/servers/"
            f"{SERVER_IDENTIFIER}/power"
        )

        headers = {
            "Authorization": f"Bearer {PANEL_API_KEY}",
            "Accept": "Application/vnd.pterodactyl.v1+json",
            "Content-Type": "application/json"
        }

        try:
            timeout = aiohttp.ClientTimeout(total=20)

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.post(
                    url,
                    headers=headers,
                    json={"signal": "start"}
                ) as response:

                    if response.status in (200, 202, 204):
                        message = (
                            "🟢 NOXORA MC start request sent!\n"
                            "Wait for the server to start."
                        )
                    else:
                        print(
                            "Hosting API error:",
                            response.status,
                            (await response.text())[:300]
                        )
                        message =
