import discord
from discord.ext import commands
import config
import os

intents = discord.Intents.all()
client = commands.Bot(command_prefix=config.PREFIX, intents=intents)

async def load_cogs_and_sync_commands():
    print(f'Logged in as {client.user.name}')
    loaded_cogs = 0
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            cog_name = filename[:-3]  # Quita la extensión .py para obtener el nombre del cog
            try:
                await client.load_extension(f'cogs.{cog_name}')
                print(f'Cog loaded: {cog_name}')
                loaded_cogs += 1
            except Exception as e:
                print(f'Failed to load cog: {cog_name}\n{e}')
    print(f'{loaded_cogs} cogs loaded.')
    await client.tree.sync()  # Sincroniza los comandos slash con Discord
    print('Slash commands synced.')

async def setup_hook():
    await load_cogs_and_sync_commands()

client.setup_hook = setup_hook

client.run(config.DISCORD_TOKEN)
