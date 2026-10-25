```python
import os
import asyncio
import itertools
import aiohttp
import discord

from discord import app_commands
from mcstatus import JavaServer

# ==============================
# NOXORA S-ON CONFIGURATION
# ==============================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_ROLE_ID = int(os.environ["ALLOWED_ROLE_ID"])
MINECRAFT_ADDRESS = os.environ["MINECRAFT_ADDRESS"]

intents = discord.Intents.default()


# ==============================
# MINECRAFT SERVER STATUS
# ==============================

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

    except Exception:
        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown"
        }


def has_manager_role(interaction):
    user = interaction.user

    return (
        isinstance(user, discord.Member)
        and any(role.id == ALLOWED_ROLE_ID for role in user.roles)
    )


# ==============================
# SERVER CONTROL BUTTONS
# ==============================

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
                "🛡️ You need the Server Manager role to start the server.",
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
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json={"signal": "start"},
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:

                    if response.status in (200, 202, 204):
                        message = (
                            "🟢 Start request sent!\n"
                            "Please wait while NOXORA MC starts."
                        )
                    else:
                        print(
                            "Panel API error:",
                            response.status,
                            (await response.text())[:300]
                        )
                        message = (
                            f"❌ Hosting API returned HTTP "
                            f"{response.status}. Check the panel settings."
                        )

        except (aiohttp.ClientError, asyncio.TimeoutError):
            message = "❌ Could not connect to the hosting panel."

        await interaction.followup.send(
            message,
            ephemeral=True
        )

    @discord.ui.button(
        label="SERVER STATUS",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="noxora:status"
    )
    async def server_status(self, interaction, button):

        await interaction.response.defer(ephemeral=True)

        data = await get_server_status()

        if data["online"]:
            embed = discord.Embed(
                title="🟢 NOXORA MC — ONLINE",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Players",
                value=f'{data["players"]}/{data["max_players"]}'
            )
            embed.add_field(
                name="Version",
                value=data["version"],
                inline=False
            )
        else:
            embed = discord.Embed(
                title="🔴 NOXORA MC — OFFLINE",
                description=(
                    "The server did not respond to the status check."
                ),
                color=discord.Color.red()
            )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# ==============================
# BOT SETUP
# ==============================

class NoxoraBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(ServerPanel())
        await self.tree.sync()


bot = NoxoraBot()


# ==============================
# AUTO ACTIVITY + DND STATUS
# ==============================

async def auto_status_loop():

    activities = itertools.cycle([
        discord.CustomActivity(
            name="✦ Created by TANJIL ✦"
        ),
        discord.Activity(
            type=discord.ActivityType.watching,
            name="NOXORA MC Server"
        )
    ])

    await bot.wait_until_ready()

    while not bot.is_closed():

        data = await get_server_status()

        if data["online"]:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=(
                    f"NOXORA MC | "
                    f"{data['players']}/{data['max_players']} Players"
                )
            )
        else:
            activity = next(activities)

        await bot.change_presence(
            status=discord.Status.dnd,
            activity=activity
        )

        await asyncio.sleep(60)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("⚡ NOXORA S-ON is online!")
    print("🔴 Presence: Do Not Disturb")


@bot.event
async def setup_hook():
    # This event is handled by the class setup_hook above.
    pass


# ==============================
# /PANEL COMMAND
# ==============================

@bot.tree.command(
    name="panel",
    description="Open the NOXORA MC control panel"
)
async def panel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="⚡ NOXORA MC",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "🎮 **MINECRAFT SERVER CONTROL**\n\n"
            "🟢 Start Server — Server Manager only\n"
            "📊 Server Status — Check server availability\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 170, 255)
    )

    embed.set_footer(
        text="✦ Created by TANJIL ✦ | NOXORA S-ON"
    )

    await interaction.response.send_message(
        embed=embed,
        view=ServerPanel()
    )


# ==============================
# /SERVERINFO COMMAND
# ==============================

@bot.tree.command(
    name="serverinfo",
    description="View NOXORA MC server status"
)
async def serverinfo(interaction: discord.Interaction):

    await interaction.response.defer()

    data = await get_server_status()

    embed = discord.Embed(
        title="🌐 NOXORA MC SERVER INFO",
        color=(
            discord.Color.green()
            if data["online"]
            else discord.Color.red()
        )
    )

    embed.add_field(
        name="Status",
        value="🟢 ONLINE" if data["online"] else "🔴 OFFLINE"
    )

    if data["online"]:
        embed.add_field(
            name="Players",
            value=f'{data["players"]}/{data["max_players"]}'
        )
        embed.add_field(
            name="Version",
            value=data["version"],
            inline=False
        )

    embed.set_footer(text="NOXORA S-ON • Created by TANJIL")

    await interaction.followup.send(embed=embed)


# ==============================
# /HELP COMMAND
# ==============================

@bot.tree.command(
    name="help",
    description="Show NOXORA S-ON bot commands"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="⚡ NOXORA S-ON — HELP",
        description=(
            "`/panel` — Open the server control panel\n"
            "`/serverinfo` — Check Minecraft server status\n"
            "`/help` — Show this help menu\n\n"
            "🛡️ Only members with the Server Manager role "
            "can start the server."
        ),
        color=discord.Color.from_rgb(0, 170, 255)
    )

    embed.set_footer(text="✦ Created by TANJIL ✦")

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


bot.setup_hook = bot.setup_hook
bot.run(DISCORD_TOKEN)
```
