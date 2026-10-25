```python
import os
import asyncio
import aiohttp
import discord

from discord import app_commands
from discord.ext import tasks
from mcstatus import JavaServer


# ==========================================
# NOXORA S-ON CONFIGURATION
# ==========================================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_ROLE_ID = int(os.environ["ALLOWED_ROLE_ID"])
MINECRAFT_ADDRESS = os.environ["MINECRAFT_ADDRESS"]

intents = discord.Intents.default()


# ==========================================
# MINECRAFT SERVER STATUS
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
        print(f"Minecraft status error: {error}")

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown"
        }


# ==========================================
# ROLE PERMISSION
# ==========================================

def has_manager_role(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        return False

    return any(
        role.id == ALLOWED_ROLE_ID
        for role in interaction.user.roles
    )


# ==========================================
# SERVER START BUTTON
# ==========================================

class ServerPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

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
                            "🟢 **NOXORA MC**\n"
                            "Start request sent successfully!\n"
                            "Please wait for the server to start.",
                            ephemeral=True
                        )

                    else:
                        error_text = await response.text()

                        print(
                            f"Hosting API error: "
                            f"{response.status} - {error_text[:300]}"
                        )

                        await interaction.followup.send(
                            f"❌ Hosting API error: "
                            f"HTTP {response.status}\n"
                            "Please check your Railway variables "
                            "and hosting API access.",
                            ephemeral=True
                        )

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            print(f"Hosting connection error: {error}")

            await interaction.followup.send(
                "❌ Could not connect to the hosting panel.",
                ephemeral=True
            )


    # ======================================
    # SERVER STATUS BUTTON
    # ======================================

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
                description="The Minecraft server is responding.",
                color=discord.Color.green()
            )

            embed.add_field(
                name="👥 Players",
                value=(
                    f'{data["players"]}/'
                    f'{data["max_players"]}'
                ),
                inline=True
            )

            embed.add_field(
                name="🎮 Version",
                value=data["version"],
                inline=True
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
# DISCORD BOT
# ==========================================

class NoxoraBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):

        # Keep the buttons working after bot restarts.
        self.add_view(ServerPanel())

        # Register slash commands.
        await self.tree.sync()

        # Start automatic activity updates.
        if not update_activity.is_running():
            update_activity.start()


bot = NoxoraBot()


# ==========================================
# AUTOMATIC ACTIVITY AND DND STATUS
# ==========================================

activity_rotation = 0


@tasks.loop(seconds=60)
async def update_activity():

    global activity_rotation

    data = await get_server_status()

    # Rotate between the creator activity and live server info.
    if data["online"] and activity_rotation % 2 == 0:

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=(
                f"NOXORA MC | "
                f'{data["players"]}/{data["max_players"]} Players'
            )
        )

    elif data["online"]:

        activity = discord.CustomActivity(
            name="✦ Created by TANJIL ✦"
        )

    else:

        activity = discord.CustomActivity(
            name="✦ Created by TANJIL ✦"
        )

    activity_rotation += 1

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=activity
    )


@update_activity.before_loop
async def before_activity_update():
    await bot.wait_until_ready()


@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")
    print("⚡ NOXORA S-ON is online!")
    print("🔴 Bot status: Do Not Disturb")
    print("🎮 Automatic server status updates enabled")


# ==========================================
# /PANEL COMMAND
# ==========================================

@bot.tree.command(
    name="panel",
    description="Open the NOXORA MC server control panel"
)
async def panel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="⚡ NOXORA MC",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎮 **MINECRAFT SERVER CONTROL**\n\n"
            "🟢 **START SERVER**\n"
            "Start the server (Server Manager role required).\n\n"
            "📊 **SERVER STATUS**\n"
            "Check whether the Minecraft server is online.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 170, 255)
    )

    embed.set_footer(
        text="✦ Created by TANJIL ✦ • NOXORA S-ON"
    )

    await interaction.response.send_message(
        embed=embed,
        view=ServerPanel()
    )


# ==========================================
# /SERVERINFO COMMAND
# ==========================================

@bot.tree.command(
    name="serverinfo",
    description="Check NOXORA MC server information"
)
async def serverinfo(interaction: discord.Interaction):

    await interaction.response.defer()

    data = await get_server_status()

    if data["online"]:

        embed = discord.Embed(
            title="🌐 NOXORA MC — SERVER INFO",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Status",
            value="🟢 ONLINE",
            inline=True
        )

        embed.add_field(
            name="Players",
            value=(
                f'{data["players"]}/'
                f'{data["max_players"]}'
            ),
            inline=True
        )

        embed.add_field(
            name="Version",
            value=data["version"],
            inline=False
        )

    else:

        embed = discord.Embed(
            title="🌐 NOXORA MC — SERVER INFO",
            description="🔴 Server is offline or not responding.",
            color=discord.Color.red()
        )

    embed.set_footer(
        text="NOXORA S-ON • Created by TANJIL"
    )

    await interaction.followup.send(embed=embed)


# ==========================================
# /HELP COMMAND
# ==========================================

@bot.tree.command(
    name="help",
    description="Show NOXORA S-ON commands"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="⚡ NOXORA S-ON — HELP",
        description=(
            "`/panel` — Open the server control panel\n\n"
            "`/serverinfo` — Check server status and players\n\n"
            "`/help` — Show this help menu\n\n"
            "🛡️ **Server Permissions**\n"
            "Only members with the Server Manager role "
            "can start the Minecraft server."
        ),
        color=discord.Color.from_rgb(0, 170, 255)
    )

    embed.set_footer(
        text="✦ Created by TANJIL ✦"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ==========================================
# RUN BOT
# ==========================================

bot.run(DISCORD_TOKEN)
```
