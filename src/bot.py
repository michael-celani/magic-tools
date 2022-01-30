import os
import discord
import tempfile
import requests
from thefuzz import fuzz, process
from discord.ext import commands
from dotenv import load_dotenv
from moxfield import MoxfieldAuth, MoxfieldDeck
from shandalar import ShandalarContext

# Load environment variables.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOXFIELD_USERNAME = os.getenv('MOXFIELD_USERNAME')
MOXFIELD_PASSWORD = os.getenv('MOXFIELD_PASSWORD')
MOXFIELD_HANGMAN_SOURCE = os.getenv('MOXFIELD_HANGMAN_SOURCE')
MOXFIELD_HANGMAN_TARGET = os.getenv('MOXFIELD_HANGMAN_TARGET')

# Authenticate with Moxfield.
session = requests.Session()
session.auth = MoxfieldAuth(MOXFIELD_USERNAME, MOXFIELD_PASSWORD)
hangman_source = MoxfieldDeck(MOXFIELD_HANGMAN_SOURCE, session)
hangman_target = MoxfieldDeck(MOXFIELD_HANGMAN_TARGET, session)
hangman_source_deck = hangman_source.get()

# Load the data.
cards = ShandalarContext.load('./shandalar_data.tsv')
moxfield_cards = {}
with open('./moxfield_ids.tsv') as moxfield_data:
    for line in moxfield_data:
        data = line.split('\t')
        moxfield_cards[data[0]] = data[1]

# Load the discord client.
client = discord.Client()
bot = commands.Bot(command_prefix='!')


def is_hangman_enabled():
    return MOXFIELD_HANGMAN_SOURCE is not None

@bot.command(name='hg', help='Guesses a card in Hangman.')
async def guess(ctx, command: str, *args):
    if not is_hangman_enabled():
        await ctx.send("Commander Hangman isn't currently enabled.")
        return

    if command == 'list':
        embed = discord.Embed(
            title='Commander Hangman',
            description='The current list of guesses for Commander Hangman.',
            url=f'https://www.moxfield.com/decks/{MOXFIELD_HANGMAN_TARGET}')
        await ctx.send(embed=embed)

    if command != 'guess':
        return

    card_name = ' '.join(args)

    # Check if it's a card name.
    if card_name not in moxfield_cards:
        new_card_name = process.extractOne(card_name, moxfield_cards.keys(), scorer=fuzz.token_sort_ratio)[0]
        if new_card_name.lower() != card_name.lower():
            await ctx.send(f'Guessing closest card: "{new_card_name}"')
        card_name = new_card_name

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
async def shandalar(ctx, deck_site: str, public_id: str):
    lines, errors = None, None

    if deck_site.lower() == 'moxfield':
        try:
            lines, errors = shandalarize_moxfield(public_id)
        except:
            await ctx.send("There was an error getting the deck from Moxfield.")
            return
    else:
        await ctx.send(f"The deck site '{deck_site}' is not currently supported.")
        return

    if len(lines) != 0:
        with tempfile.NamedTemporaryFile('w', encoding="utf-8", delete=True) as fi:
            fi.writelines(lines)
            fi.flush()
            await ctx.send(file=discord.File(fi.name, 'deck.dck'))

    if len(errors) != 0:
        with tempfile.NamedTemporaryFile('w', encoding="utf-8", delete=True) as err:
            err.writelines(errors)
            err.flush()
            await ctx.send(file=discord.File(err.name, 'errors.txt'))

def shandalarize_moxfield(public_id: str):
    # Get the Moxfield deck:
    deck = MoxfieldDeck(public_id, session).get()
    mainboard = {card.split('//')[0].strip() : card_info['quantity'] for card, card_info in deck['mainboard'].items()}
    print(mainboard)
    return cards.convert(mainboard)

bot.run(TOKEN)
