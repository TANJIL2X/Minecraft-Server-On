```python
import os
import aiohttp
import discord
from discord import app_commands

# Environment Variables
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])

intents = discord.Intents.default()


class ServerPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ON SERVER",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="noxora:start_server"
    )
    async def start_server(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # Only the authorized user can start the server
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "❌ You are not allowed to use this button.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

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

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    headers=headers,
                    json={"signal": "start"}
                ) as response:

                    if response.status in (200, 202, 204):
                        await interaction.followup.send(
                            "🟢 **NOXORA MC** server start request sent! "
                            "Please wait for the server to start.",
                            ephemeral=True
                        )
                    else:
                        error_text = (await response.text())[:500]
                        print(
                            f"Panel API error: HTTP {response.status} "
                            f"- {error_text}"
                       
