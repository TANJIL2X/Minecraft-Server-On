import os
import aiohttp
import discord
from discord import app_commands

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PANEL_URL = os.environ["PANEL_URL"].rstrip("/")
PANEL_API_KEY = os.environ["PANEL_API_KEY"]
SERVER_IDENTIFIER = os.environ["SERVER_IDENTIFIER"]
ALLOWED_ROLE_ID = int(os.environ["ALLOWED_ROLE_ID"])

intents = discord.Intents.default()


def has_allowed_role(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False

    return any(
        role.id == ALLOWED_ROLE_ID
        for role in interaction.user.roles
    )


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
        if not has_allowed_role(interaction):
            await interaction.response.send_message(
                "❌ তোমার কাছে Server Manager Role নেই!",
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
                            "🟢 NOXORA MC server start request পাঠানো হয়েছে!",
                            ephemeral=True
                        )
                    else:
                        print(
                            f"Panel API error: HTTP {response.status}"
                        )
                        await interaction.followup.send(
                            f"❌ Hosting API request ব্যর্থ "
                            f"(HTTP {response.status})।",
                            ephemeral=True
                        )

        except (aiohttp.ClientError, TimeoutError) as error:
            print(f"Connection error: {error!r}")
            await interaction.followup.send(
                "❌ Hosting panel-এ সংযোগ করা যায়নি।",
                ephemeral=True
            )


class NoxoraBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(ServerPanel())
        await self.tree.sync()


bot = NoxoraBot()


@bot.event
async def on_ready():
    print(f"NOXORA S-ON online: {bot.user}")


@bot.tree.command(
    name="panel",
    description="NOXORA MC server control panel"
)
async def panel(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message(
            "❌ এই command ব্যবহার করতে Server Manager Role লাগবে।",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🟢 NOXORA MC SERVER CONTROL",
        description=(
            "Minecraft server চালু করতে নিচের button চাপো।"
        ),
        color=discord.Color.green()
    )

    embed.set_footer(text="NOXORA S-ON • Server Control")

    await interaction.response.send_message(
        embed=embed,
        view=ServerPanel()
    )


bot.run(DISCORD_TOKEN)
