```python
import os
import asyncio
import aiohttp
import discord

from discord import app_commands
from discord.ext import tasks
from mcstatus import JavaServer


# ==========================================
# CONFIGURATION
# ==========================================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_ROLE_ID = int(os.environ["ALLOWED_ROLE_ID"])
MINECRAFT_ADDRESS = os.environ["MINECRAFT_ADDRESS"]

intents = discord.Intents.default()


# ==========================================
# MINECRAFT STATUS
# ==========================================

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
        print(f"Minecraft status check failed: {error}")

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown"
        }


# ==========================================
# ROLE CHECK
# ==========================================

def has_manager_role(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        return False

    return any(
        role.id == ALLOWED_ROLE_ID
        for role in interaction.user.roles
    )


# ==========================================
# SERVER CONTROL PANEL
# ==========================================

class ServerPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # START SERVER BUTTON

    @discord.ui.button(
        label="START SERVER",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="noxora:start"
    )
    async def start_server(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_manager_role(interaction):
            await interaction.response.send_message(
                "🛡️ You need the Server Manager role "
                "to start NOXORA MC.",
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
                        await interaction.followup.send(
                            "🟢 NOXORA MC start request sent!\n"
                            "Please wait for the server to start.",
                            ephemeral=True
                        )

                    else:
                        error_text = await response.text()

                        print(
                            f"Hosting API error: {response.status} "
                            f"{error_text[:300]}"
                        )

                        await interaction.followup.send(
                            f"❌ Hosting API error: HTTP "
                            f"{response.status}.\n"
                            "Please check your hosting API settings.",
                            ephemeral=True
                        )

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            print(f"Hosting connection failed: {error}")

            await interaction.followup.send(
                "❌ Could not connect to the hosting panel.",
                ephemeral=True
            )

    # SERVER STATUS BUTTON

    @discord.ui.button(
        label="SERVER STATUS",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="noxora:status"
    )
    async def server_status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(ephemeral=True)

        data = await get_server_status()

        if data["online"]:
            embed = discord.Embed(
                title="🟢 NOXORA MC — ONLINE",
                description="Minecraft server is responding.",
                color=discord.Color.green()
            )

            embed.add_field(
                name="👥 Players",
                value=f'{data["players"]}/{data["max_players"]}'
            )

            embed.add_field(
                name="🎮 Version",
                value=data["version"]
            )

        else:
            embed = discord.Embed(
                title="🔴 NOXORA MC — OFFLINE",
                description=(
                    "The server did not respond to the status check."
                ),
                color=discord.Color.red()
            )

        embed.set_footer(
            text="NOXORA S-ON • Created by TANJIL"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# ==========================================
# BOT SETUP
# ==========================================

class NoxoraBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(ServerPanel())
        await self
