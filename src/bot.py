import os
import discord
import tempfile
import requests
from discord.ext import commands
from dotenv import load_dotenv
from moxfield.auth import MoxfieldAuth
from moxfield.decks import MoxfieldSpecificDeckAPI
from moxfield.search import MoxfieldSearchAPI
from shandalar import ShandalarContext
from hangman import CommanderHangman, CommanderHangmanStats

# Load environment variables.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOXFIELD_USERNAME = os.getenv('MOXFIELD_USERNAME')
MOXFIELD_PASSWORD = os.getenv('MOXFIELD_PASSWORD')

# Authenticate with Moxfield.
session = requests.Session()
session.auth = MoxfieldAuth(MOXFIELD_USERNAME, MOXFIELD_PASSWORD)
hangman_stats = CommanderHangmanStats('./data/stats.db')
hangman_session = None

# Load the data.
cards = ShandalarContext.load('./data/shandalar_data.tsv')

# Load the discord client.
client = discord.Client()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

@bot.command(name='hg', help='Guesses a card in Hangman.')
async def guess(ctx, command: str, *args):
    
    if command == 'set':
        if ctx.message.author.guild_permissions.administrator:
            source, target = args
            global hangman_session
            hangman_session = CommanderHangman(session, source, target, hangman_stats)
            await ctx.send("Hangman set.")
        else:
            await ctx.send("Invalid permissions.")
        return

    if command == 'stats':
        mentions = list(ctx.message.mentions)

        if len(mentions) > 0:
            user = mentions[0]
        else:
            user = ctx.message.author

        stats = hangman_stats.get_player_stats(user.id, None if hangman_session is None else hangman_session.hangman_source.public_id)
        desc = f'Commander Hangman statistics for user {user.name}'

        if hangman_session is not None:
            deck_name = hangman_session.hangman_source_deck['name']
            desc = desc + f" (Deck: '{deck_name}')"

        embed = discord.Embed(
            title = f'Commander Hangman Stats: {user.name}',
            description=desc
        )
        
        embed.add_field(name="Total Guesses", value=stats['all_time'])
        embed.add_field(name="Total Correct", value=stats['all_time_correct'])
        embed.add_field(name="Total Correct %", value=round(100.0 * stats['all_time_correct'] / max(1, stats['all_time']), 2))

        if hangman_session is not None:
            embed.add_field(name="Current Deck Guesses", value=stats['current'])
            embed.add_field(name="Current Deck Correct", value=stats['current_correct'])
            embed.add_field(name="Current Deck Correct %", value=round(100.0 * stats['current_correct'] / max(1, stats['current']), 2))
        await ctx.send(embed=embed)
        return

    if hangman_session is None:
        await ctx.send("Commander Hangman isn't currently enabled.")
        return

    if command == 'list':
        embed = discord.Embed(
            title='Commander Hangman',
            description='The current list of guesses for Commander Hangman.',
            url=f'https://www.moxfield.com/decks/{hangman_session.hangman_target.public_id}')
        await ctx.send(embed=embed)
        return

    if command != 'guess':
        return

    query = ' '.join(args)
    guess_results = hangman_session.guess(ctx.message.author.id, query)

    if guess_results['guess_correct']:
        await ctx.message.add_reaction('✅')
    else:
        await ctx.message.add_reaction('❌')

    if not guess_results['guess_unique']:
        await ctx.message.add_reaction('⁉️')

    if guess_results['card_name'] is None:
        await ctx.send('No card matching the query found.')
        return

    card_name = guess_results['card_name']

    if guess_results['card_name'].lower() != query.lower():
        await ctx.send(f'Guessed closest card: "{card_name}"')    


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
    deck = MoxfieldSpecificDeckAPI(public_id, session).get()
    mainboard = {card.split('//')[0].strip() : card_info['quantity'] for card, card_info in deck['mainboard'].items()}
    print(mainboard)
    return cards.convert(mainboard)

bot.run(TOKEN)
