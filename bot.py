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
        status = await asyncio.wait_for(server.async_status(), timeout=5)
        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "version": status.version.name,
        }
    except Exception as error:
        print(f"Minecraft status check failed: {error}")
        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown",
        }


def has_manager_role(interaction: discord.Interaction) -> bool:
    user = interaction.user
    return (
        isinstance(user, discord.Member)
        and any(role.id == ALLOWED_ROLE_ID for role in user.roles)
    )


class ServerPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="START SERVER",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="noxora:start",
    )
    async def start_server(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not has_manager_role(interaction):
            await interaction.response.send_message(
                "🛡️ Server Manager role required!",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        url = f"{PANEL_URL}/api/client/servers/{SERVER_IDENTIFIER}/power"
        headers = {
            "Authorization": f"Bearer {PANEL_API_KEY}",
            "Accept": "Application/vnd.pterodactyl.v1+json",
            "Content-Type": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    headers=headers,
                    json={"signal": "start"},
                ) as response:
                    if response.status in (200, 202, 204):
                        message = (
                            "🟢 NOXORA MC start request sent!\n"
                            "Please wait for the server to start."
                        )
                    else:
                        response_text = (await response.text())[:300]
                        print(
                            "Hosting API error:",
                            response.status,
                            response_text,
                        )
                        message = (
                            f"❌ Hosting API error: HTTP {response.status}. "
                            "Check PANEL_URL, API key permissions, and server identifier."
                        )
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            print(f"Hosting panel connection error: {error}")
            message = "❌ Could not connect to the hosting panel. Check PANEL_URL."

        await interaction.followup.send(message, ephemeral=True)

    @discord.ui.button(
        label="SERVER STATUS",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="noxora:status",
    )
    async def server_status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.defer(ephemeral=True)
        data = await get_server_status()

        if data["online"]:
            embed = discord.Embed(
                title="🟢 NOXORA MC — ONLINE",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Players",
                value=f'{data["players"]}/{data["max_players"]}',
                inline=True,
            )
            embed.add_field(
                name="Version",
                value=data["version"],
                inline=True,
            )
        else:
            embed = discord.Embed(
                title="🔴 NOXORA MC — OFFLINE",
                description="The Minecraft server did not respond.",
                color=discord.Color.red(),
            )

        embed.set_footer(text="NOXORA S-ON • Created by TANJIL")
        await interaction.followup.send(embed=embed, ephemeral=True)


class NoxoraBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(ServerPanel())
        await self.tree.sync()


bot = NoxoraBot()


@tasks.loop(seconds=60)
async def update_activity():
    data = await get_server_status()

    if data["online"]:
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f'NOXORA MC | {data["players"]}/{data["max_players"]} Players',
        )
    else:
        activity = discord.CustomActivity(name="✦ Created by TANJIL ✦")

    await bot.change_presence(status=discord.Status.dnd, activity=activity)


@update_activity.before_loop
async def before_activity_update():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"NOXORA S-ON online: {bot.user}")
    print("Status: Do Not Disturb")
    if not update_activity.is_running():
        update_activity.start()


@bot.tree.command(
    name="panel",
    description="Open NOXORA MC server control panel",
)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚡ NOXORA MC",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎮 **MINECRAFT SERVER CONTROL**\n\n"
            "🟢 **START SERVER**\n"
            "Only users with the Server Manager role can start the server.\n\n"
            "📊 **SERVER STATUS**\n"
            "Check whether the Minecraft server is online.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 170, 255),
    )
    embed.set_footer(text="✦ Created by TANJIL ✦ • NOXORA S-ON")
    await interaction.response.send_message(embed=embed, view=ServerPanel())


@bot.tree.command(
    name="serverinfo",
    description="Check NOXORA MC server information",
)
async def serverinfo(interaction: discord.Interaction):
    await interaction.response.defer()
    data = await get_server_status()

    if data["online"]:
        embed = discord.Embed(
            title="🌐 NOXORA MC — SERVER INFO",
            color=discord.Color.green(),
        )
        embed.add_field(name="Status", value="🟢 ONLINE", inline=True)
        embed.add_field(
            name="Players",
            value=f'{data["players"]}/{data["max_players"]}',
            inline=True,
        )
        embed.add_field(name="Version", value=data["version"], inline=True)
    else:
        embed = discord.Embed(
            title="🌐 NOXORA MC — SERVER INFO",
            description="🔴 Offline or not responding.",
            color=discord.Color.red(),
        )

    embed.set_footer(text="NOXORA S-ON • Created by TANJIL")
    await interaction.followup.send(embed=embed)


@bot.tree.command(
    name="help",
    description="Show NOXORA S-ON commands",
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚡ NOXORA S-ON — HELP",
        description=(
            "`/panel` — Open the server control panel\n\n"
            "`/serverinfo` — Check server status\n\n"
            "`/help` — Show commands\n\n"
            "🛡️ Server Manager role is required to start the server."
        ),
        color=discord.Color.from_rgb(0, 170, 255),
    )
    embed.set_footer(text="✦ Created by TANJIL ✦")
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(DISCORD_TOKEN)
