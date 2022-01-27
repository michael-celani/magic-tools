import os
import discord
import tempfile
from discord.ext import commands
from dotenv import load_dotenv
from shandalar import shandalarize

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

bot = commands.Bot(command_prefix='!')


@bot.command(name='shandalarize', help='Shandalarizes a decklist from Moxfield.')
async def shandalar(ctx, public_id: str):
    body = {'moxfield': [public_id]}
    response = shandalarize(body)

    if len(response['errors']['moxfield']) != 0:
        await ctx.send("There was an error downloading the Moxfield deck.")
        return

    for deck_id, deck in response['decks']['moxfield'].items():
        lines = 0
        with tempfile.NamedTemporaryFile('w', encoding="utf-8", delete=True) as fi:
            for card, card_line in deck['cards'].items():
                fi.write(card_line + "\n")
                lines += 1
            fi.flush()
            if lines != 0:
                await ctx.send(file=discord.File(fi.name, "deck.dck"))

        lines = 0
        with tempfile.NamedTemporaryFile('w', encoding="utf-8", delete=True) as err:
            for card, error_line in deck['errors'].items():
                err.write(card + ": " + error_line + "\n")
                lines += 1
            err.flush()
            if lines != 0:
                await ctx.send(file=discord.File(err.name, "errors.txt"))

bot.run(TOKEN)
