import time
import requests
import sqlite3
import typing
from moxfield.auth import MoxfieldAuth
from moxfield.decks import MoxfieldDeckAPI, MoxfieldSpecificDeckAPI
from discord import Embed, Member
from discord.ext import tasks, commands
from hangman import CommanderHangman, CommanderHangmanStats

def guild_only():
    async def predicate(ctx):
        return ctx.guild is not None
    return commands.check(predicate)

def admin_only():
    async def predicate(ctx):
        return ctx.message.author.guild_permissions.administrator
    return commands.check(predicate)

NO_GAME_MESSAGE = "No Commander Hangman game is being played. Type `!hg start <moxfield_id>` to start one!"

class CommanderHangmanCog(commands.Cog):

    def build_embed(self, hangman_session, desc = '', with_stats = False, with_expires = False, use_source = False):
        moxfield_deck = hangman_session.hangman_source if use_source else hangman_session.hangman_target
        source_deck_name = hangman_session.hangman_source_deck['name']

        embed = Embed(
            title=f'Commander Hangman: {source_deck_name}',
            url=f'https://www.moxfield.com/decks/{moxfield_deck.public_id}',
            description=desc
        )

        if with_stats:
            with self.guild_games.stats(hangman_session.guild_id) as stats:
                out = stats.get_source_stats(hangman_session.hangman_source.public_id)
                embed.add_field(name="Guesses", value=out['guesses'])
                embed.add_field(name="Correct", value=out['correct'])
                if out['top_scorer_id'] is not None:
                    embed.add_field(name="Top Guesser", value=self.bot.get_user(int(out['top_scorer_id'])))

        if with_expires:
            embed.add_field(name="Expires", value=f'<t:{hangman_session.expiration}:R>')

        embed.set_thumbnail(url="https://gamesfreaksa.info/shandalarand/assets/006.png")

        return embed

    @commands.group(name='hg', invoke_without_command=True, help="View the current Commander Hangman game.")
    @guild_only()
    async def hangman(self, ctx):
        guild_id = ctx.guild.id

        if self.guild_games[guild_id] is None:
            await ctx.send(NO_GAME_MESSAGE)
        else:
            embed = self.build_embed(self.guild_games[guild_id], "There's a Commander Hangman game running now!", with_stats=True, with_expires = True)
            await ctx.send(embed=embed)

        pass

    @hangman.command(name='start',  help='Start a new Commander Hangman game with the given decklist.')
    @guild_only()
    async def hangman_start(self, ctx, moxfield_id: str):
        guild_id = ctx.guild.id
        author = ctx.message.author
        author_id = ctx.message.author.id
        channel_id = ctx.message.channel.id
        await ctx.message.delete()

        # Do not allow starting a new game if a current one is in progress.
        if self.guild_games[guild_id] is not None:
            embed = self.build_embed(self.guild_games[guild_id], "A Commander Hangman game is already in progress.", with_stats=True, with_expires = True)
            await ctx.send(embed=embed)
            return

        # Do not allow starting a new game with a previously played decklist.
        with self.guild_games.stats(guild_id) as stats:
            if stats.get_source_stats(moxfield_id)['guesses'] != 0:
                await ctx.send("This deck was played already.")
                return
    
        # Initialize the target and cache context:
        self.guild_games.start(guild_id, moxfield_id, ctx.message.channel.id, author_id)

        # Send success message:
        embed = self.build_embed(self.guild_games[guild_id], f'{author.name} started a new Commander Hangman game! Type `!hg guess <card name>` to guess!', with_expires = True)
        await ctx.send(embed=embed)

    @hangman.command(name='guess',  help='Guesses a card name.')
    @guild_only()
    async def hangman_guess(self, ctx, *, card_name: str):
        guild_id = ctx.guild.id

        if self.guild_games[guild_id] is None:
            await ctx.send(NO_GAME_MESSAGE)
            return

        if self.guild_games[guild_id].owner == ctx.message.author.id and not ctx.message.author.guild_permissions.administrator:
            await ctx.send("You're the owner of this Hangman game! You cannot guess.")
            return

        guess_results = self.guild_games[guild_id].guess(ctx.message.author.id, card_name)

        if guess_results['guess_correct']:
            await ctx.message.add_reaction('✅')
        else:
            await ctx.message.add_reaction('❌')

        if not guess_results['guess_unique']:
            await ctx.message.add_reaction('⁉️')

        if guess_results['card_name'] is None:
            await ctx.message.add_reaction('❓')
            return

        card_name = guess_results['card_name']

        if guess_results['card_name'].lower() != card_name.lower():
            await ctx.send(f'Guessed closest card: "{card_name}"')

    @hangman.command(name='stop',  help='Stops the currently running Commander Hangman game (administrator only).')
    @guild_only()
    @admin_only()
    async def hangman_stop(self, ctx):
        guild_id = ctx.guild.id

        if self.guild_games[guild_id] is None:
            return
        
        embed = self.build_embed(self.guild_games[guild_id], 'Commander Hangman has finished! Congratulations to the winner!', with_stats=True, use_source=True)
        await ctx.send(embed=embed)
        del self.guild_games[guild_id]

    @hangman.command(name='stats', help='Gets the stats of a player.')
    @guild_only()
    async def hangman_stats(self, ctx, *, member: typing.Optional[Member]):
        guild_id = ctx.guild.id

        if member is None:
            member = ctx.message.author

        with self.guild_games.stats(guild_id) as stat_back:
            stats = stat_back.get_player_stats(member.id, None if self.guild_games[guild_id] is None else self.guild_games[guild_id].hangman_source.public_id)
            embed = Embed(title = f'Commander Hangman Stats: {member.name}')
            embed.set_thumbnail(url=member.avatar_url)
            embed.add_field(name="Total Correct", value=stats['all_time_correct'])
            embed.add_field(name="Total Guesses", value=stats['all_time'])
            embed.add_field(name="Total Correct %", value=round(100.0 * stats['all_time_correct'] / max(1, stats['all_time']), 2))

            if self.guild_games[guild_id] is not None:
                embed.add_field(name="Current Deck Correct", value=stats['current_correct'])
                embed.add_field(name="Current Deck Guesses", value=stats['current'])
                embed.add_field(name="Current Deck Correct %", value=round(100.0 * stats['current_correct'] / max(1, stats['current']), 2))
            
            await ctx.send(embed=embed)
    
    @hangman.command(name='rank', help='Displays the top ten players.')
    @guild_only()
    async def hangman_rank(self, ctx):
        embed = Embed()
        embed.title = f'Commander Hangman: All Time Top Scorers 🏆'
        output = {}

        with self.guild_games.stats(ctx.guild.id) as stat_back:
            top_players = stat_back.get_rank_all_time()

            await self.bot.wait_until_ready()

            for player, guesses in top_players.items():
                user = self.bot.get_user(int(player))
                output[user.display_name] = guesses

            if len(output) != 0:
                embed.add_field(name="Player", value='\n'.join(output.keys()))
                embed.add_field(name="Correct Guesses", value='\n'.join(str(n) for n in output.values()))
            else:
                embed.description = 'No stats available.'

            embed.set_thumbnail(url="https://gamesfreaksa.info/shandalarand/assets/006.png")

            await ctx.send(embed=embed)
    
    @tasks.loop(seconds=10.0)
    async def finish_games(self):
        for game in self.hangman_data.expired_games():
            await self.bot.wait_until_ready()
            guild_id = game['guild_id']
            channel = await self.bot.fetch_channel(game['channel_id'])
            embed = self.build_embed(self.guild_games[guild_id], 'Commander Hangman has finished! Congratulations to the winner!', with_stats=True, use_source=True)
            await channel.send(embed=embed)
            del self.guild_games[guild_id]
            

    def __init__(self, bot, moxfield_username, moxfield_password):
        self.bot = bot
        self.session = requests.Session()
        self.session.auth = MoxfieldAuth(moxfield_username, moxfield_password)
        self.hangman_data = CommanderHangmanData('./data/hangman.db')
        self.guild_games = CommanderHangmanGuildContext(self.session, self.hangman_data)
        self.finish_games.start()


class CommanderHangmanGuildContext:

    def setup_target_id(self, guild_id):
        target_id = MoxfieldDeckAPI(self.session).create('Commander Hangman', format='commander').public_id
        self.data.set_target_id(guild_id, target_id)
        return target_id

    def get_target_id(self, guild_id):
        target_id = self.data.get_target_id(guild_id)

        if target_id is None:
            target_id = self.setup_target_id(guild_id)
        
        return target_id

    def start(self, guild_id, source_id, channel_id, owner_id):
        self[guild_id] = CommanderHangman(self.session, guild_id, source_id, self.get_target_id(guild_id), int(time.time()) + 3600, owner_id, channel_id)
        self[guild_id].initialize_target()

    def stats(self, guild_id):
        return CommanderHangmanStats(f"./data/{int(guild_id)}.db")

    def __setitem__(self, guild_id, value):
        self.data.set_current_game(guild_id, value.hangman_source.public_id, value.owner, value.channel_id, value.expiration)
        self.cache[guild_id] = value
        pass

    def __delitem__(self, guild_id):
        self.data.delete_current_game(guild_id)
        self.cache[guild_id] = None

    def __getitem__(self, guild_id):
        if guild_id in self.cache:
            return self.cache[guild_id]
        
        # Get the current game.
        current_game = self.data.get_current_game(guild_id)

        if current_game is None:
            self.cache[guild_id] = None
        else:
            target_id = self.get_target_id(guild_id)
            self.cache[guild_id] = CommanderHangman(self.session, guild_id, current_game['source_id'], target_id, current_game['expires'], current_game['owner_id'], current_game['channel_id'])

        return self.cache[guild_id]

    def __init__(self, session, data):
        self.session = session
        self.data = data
        self.cache = {}

class CommanderHangmanData:

    def expired_games(self):
        cur = self.database.cursor()
        current_game = cur.execute("SELECT guild_id, source_id, channel_id, expiration FROM CurrentGames WHERE expiration<?", [int(time.time())])

        for game in current_game:
            yield {
                'guild_id': game[0],
                'source_id': game[1],
                'channel_id': game[2],
                'expires': game[3]
            }

    def get_current_game(self, guild_id):
        cur = self.database.cursor()
        current_game = cur.execute("SELECT source_id, owner_id, channel_id, expiration FROM CurrentGames WHERE guild_id=?", [guild_id])

        for game in current_game:
            return {
                'source_id': game[0],
                'owner_id': game[1],
                'channel_id': game[2],
                'expires': game[3]
            }

        return None

    def set_current_game(self, guild_id, source_id, owner_id, channel_id, expiration):
        cur = self.database.cursor()
        cur.execute('DELETE FROM CurrentGames WHERE guild_id=?', [guild_id])
        cur.execute('INSERT INTO CurrentGames (guild_id, source_id, owner_id, channel_id, expiration) VALUES (?, ?, ?, ?, ?)', [guild_id, source_id, owner_id, channel_id, expiration])
        self.database.commit()

    def delete_current_game(self, guild_id):
        cur = self.database.cursor()
        cur.execute('DELETE FROM CurrentGames WHERE guild_id=?', [guild_id])
        self.database.commit()

    def get_target_id(self, guild_id):
        cur = self.database.cursor()
        guild_data = cur.execute("SELECT target_id FROM GuildData WHERE guild_id=?", [guild_id])

        for data in guild_data:
            return data[0]

        return None

    def set_target_id(self, guild_id, target_id):
        cur = self.database.cursor()
        cur.execute('DELETE FROM GuildData WHERE guild_id=?', [guild_id])
        cur.execute('INSERT INTO GuildData (guild_id, target_id) VALUES (?, ?)', [guild_id, target_id])
        self.database.commit()

    def __initialize_database(self):
        cursor = self.database.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS GuildData (guild_id integer UNIQUE, target_id text);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS CurrentGames (guild_id integer UNIQUE, source_id text, owner_id integer, channel_id integer, expiration integer);''')
        self.database.commit()

    def __init__(self, path):
        self.database = sqlite3.connect(path)
        self.__initialize_database()