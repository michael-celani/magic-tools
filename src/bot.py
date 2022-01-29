import os
import discord
import tempfile
import requests
from discord.ext import commands
from dotenv import load_dotenv
from moxfield import MoxfieldAuth, MoxfieldDeck
from card_collection import CardCollection, CardRecord
from shandalar import shandalarize

# Load environment variables.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOXFIELD_USERNAME = os.getenv('MOXFIELD_USERNAME')
MOXFIELD_PASSWORD=os.getenv('MOXFIELD_PASSWORD')
MOXFIELD_HANGMAN_SOURCE=os.getenv('MOXFIELD_HANGMAN_SOURCE')
MOXFIELD_HANGMAN_TARGET=os.getenv('MOXFIELD_HANGMAN_TARGET')

print(MOXFIELD_HANGMAN_TARGET)

# Authenticate with Moxfield.
session = requests.Session()
session.auth = MoxfieldAuth.login(MOXFIELD_USERNAME, MOXFIELD_PASSWORD)
hangman_source = MoxfieldDeck(MOXFIELD_HANGMAN_SOURCE, session)
hangman_target = MoxfieldDeck(MOXFIELD_HANGMAN_TARGET, session)
hangman_source_deck = hangman_source.get()

# Load the data.
cards = CardCollection.load('./shandalar_data.tsv')
moxfield_cards = {}
with open('./moxfield_ids.tsv') as moxfield_data:
    for line in moxfield_data:
        data = line.split('\t')
        moxfield_cards[data[0]] = data[1]

# Load the discord client.
client = discord.Client()
bot = commands.Bot(command_prefix='!')

@bot.command(name='hangman_list', help='Gets the current hangman deck.')
async def hangman_deck(ctx):
    if MOXFIELD_HANGMAN_SOURCE is None:
        await ctx.send("Commander Hangman isn't currently enabled.")
        return

    embed = discord.Embed(title='Commander Hangman', description= 'The current list of guesses for Commander Hangman.', url=f'https://www.moxfield.com/decks/{MOXFIELD_HANGMAN_TARGET}')
    await ctx.send(embed=embed)

@bot.command(name='hangman_guess', help='Guesses a card in Hangman.')
async def guess(ctx, card_name: str):
    # Check if hangman is enabled.
    if MOXFIELD_HANGMAN_SOURCE is None:
        await ctx.send("Commander Hangman isn't currently enabled.")
        await ctx.message.add_reaction('❌')
        return

    # Check if it's a card name.
    if card_name not in moxfield_cards:
        await ctx.send("Your guess wasn't a Magic: the Gathering card. Capitalization matters, and if it's multiple words, use quotes!")
        await ctx.message.add_reaction('❌')
        return

    # Check the source for the card name.
    if card_name not in hangman_source_deck['mainboard']:
        await ctx.message.add_reaction('❌')
        return

    # Update deck.
    moxfield_id = moxfield_cards[card_name]
    quantity = hangman_source_deck['mainboard'][card_name]['quantity']
    hangman_target.set_mainboard(moxfield_id, quantity)
    await ctx.message.add_reaction('✅')

@bot.command(name='shandalarize', help='Shandalarizes a decklist from Moxfield.')
async def shandalar(ctx, public_id: str):
    body = {'moxfield': [public_id]}
    response = shandalarize(body, cards, session)

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
