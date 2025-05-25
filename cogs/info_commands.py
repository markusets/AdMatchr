import discord
from discord.ext import commands
from datetime import datetime

class InfoCommands(commands.Cog):
    """
    Cog that provides basic info and shortcuts.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="info",
        description="Display basic bot information and usage."
    )
    async def info(self, interaction: discord.Interaction):
        """
        Send a brief overview of the bot’s purpose and available commands.
        """
        message = (
            "**Daily Insights Bot**\n"
            "Generates reports of advertising insights from Meta and Ringba.\n"
            "Use `/daily_general_report` to fetch today’s insights."
        )
        await interaction.response.send_message(message, ephemeral=True)

    @discord.app_commands.command(
        name="daily_general_report",
        description="Trigger the daily Meta and Ringba insights report."
    )
    async def daily_general_report(self, interaction: discord.Interaction):
        """
        Shortcut command to invoke the daily-general-report cog.
        """
        # This command delegates to the main reporting cog
        from .daily_general_report import DailyGeneralReport
        cog = self.bot.get_cog('DailyGeneralReport')
        if cog:
            # Use today’s date in YYYY-MM-DD format
            today = datetime.now().strftime('%Y-%m-%d')
            await cog.general_report.callback(cog, interaction, since=today)
        else:
            await interaction.response.send_message(
                "Reporting cog not loaded.", ephemeral=True
            )

async def setup(bot: commands.Bot):
    """
    Add the info commands cog to the bot.
    """
    await bot.add_cog(InfoCommands(bot))
