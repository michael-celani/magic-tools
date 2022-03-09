import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from hangman_cog import CommanderHangmanCog

# Load environment variables.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOXFIELD_USERNAME = os.getenv('MOXFIELD_USERNAME')
MOXFIELD_PASSWORD = os.getenv('MOXFIELD_PASSWORD')

# Load the discord client.
bot = commands.Bot(command_prefix='!', activity = discord.Game(name="!help hg"), intents=discord.Intents.all())
bot.add_cog(CommanderHangmanCog(bot, MOXFIELD_USERNAME, MOXFIELD_PASSWORD))
bot.run(TOKEN)
