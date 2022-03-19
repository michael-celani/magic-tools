from moxfield.decks import MoxfieldSpecificDeckAPI
from moxfield.search import MoxfieldSearchAPI
import sqlite3
import itertools

def guild_stats_path(guild_id):
    return f"./data/{int(guild_id)}.db"

class CommanderHangman:

    def guess(self, discord_id, query):
        stats_path = guild_stats_path(self.guild_id)
        card = self.__get_card(query)

        if card is None:
            return {
                "card_name": None,
                "guess_correct": False,
                "guess_unique": True
            }

        card_id = card['id']
        card_name = card['name']
        
        guess_unique = not (card_name in self.hangman_target_deck['mainboard'] or card_name in self.hangman_target_deck['maybeboard'])
        
        if card_name not in self.hangman_source_deck['mainboard']:
            if guess_unique:
                self.hangman_target.maybeboard.set(card_id, 1)
                self.hangman_target_deck['maybeboard'][card_name] = {}

                with CommanderHangmanStats(stats_path) as stats:
                    stats.add(discord_id, self.hangman_source.public_id, card_id, False)

            return {
                "card_name": card_name,
                "guess_correct": False,
                "guess_unique": guess_unique
            }

        # Update deck.
        if guess_unique:
            quantity = self.hangman_source_deck['mainboard'][card_name]['quantity']
            self.hangman_target.mainboard.set(card_id, quantity)
            self.hangman_target_deck['mainboard'][card_name] = {'quantity': quantity}

            with CommanderHangmanStats(stats_path) as stats:
                stats.add(discord_id, self.hangman_source.public_id, card_id, True)
            

        return {
            "card_name": card_name,
            "guess_correct": True,
            "guess_unique": guess_unique
         }

    def __get_card(self, query):
        card = self.search.search_named_fuzzy(query)

        if card is None:
            return None

        return card

    def get_stats(self):
        return self.stats.get_source_stats(self.hangman_source.public_id)

    def is_finished(self):
        source = sum(self.hangman_source_deck['mainboard'][card_name]['quantity'] for card_name in self.hangman_source_deck['mainboard'])
        target = sum(self.hangman_target_deck['mainboard'][card_name]['quantity'] for card_name in self.hangman_target_deck['mainboard'])
        return source == target

    def initialize_target(self):
        target_commander_ids = list(x['card']['id'] for x in self.hangman_source_deck['commanders'].values())
        
        commander_id = None if len(target_commander_ids) == 0 else target_commander_ids[0]
        partner_id = None if len(target_commander_ids) <= 1 else target_commander_ids[1]

        self.hangman_target.bulk_edit({}, {}, {})
        self.hangman_target.commanders.set((commander_id, partner_id))
        self.hangman_target_deck = self.hangman_target.get()

    def __init__(self, session, guild_id, source, target, expiration, owner, channel_id):
        self.search = MoxfieldSearchAPI(session)
        self.hangman_source = MoxfieldSpecificDeckAPI(source, session)
        self.hangman_target = MoxfieldSpecificDeckAPI(target, session)
        self.hangman_source_deck = self.hangman_source.get()
        self.hangman_target_deck = self.hangman_target.get()
        self.guild_id = guild_id
        self.expiration = expiration
        self.owner = owner
        self.channel_id = channel_id
        

class CommanderHangmanStats:

    def get_rank(self, source_id):
        cur = self.connection.cursor()
        guesses = cur.execute("SELECT discord_id, COUNT(*) AS guesses FROM HangmanStats WHERE correct=1 AND source_id=? GROUP BY discord_id ORDER BY guesses DESC LIMIT 10", (source_id, ))
        return {x: y for x, y in guesses}

    def get_rank_all_time(self):
        cur = self.connection.cursor()
        guesses = cur.execute("SELECT discord_id, COUNT(*) AS guesses FROM HangmanStats WHERE correct=1 GROUP BY discord_id ORDER BY guesses DESC LIMIT 10")
        return {x: y for x, y in guesses}

    def get_player_stats(self, discord_id, source_id):
        cur = self.connection.cursor()
        res_guesses = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE discord_id=?", (discord_id, ))
        all_time = int(res_guesses.fetchone()[0])

        res_guesses_correct = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE discord_id=? AND correct=1", (discord_id, ))
        all_time_correct = int(res_guesses_correct.fetchone()[0])

        stats = {
            "id": discord_id,
            "deck_id": source_id,
            "all_time": all_time,
            "all_time_correct": all_time_correct
        }

        if source_id is not None:
            res_guesses_current = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE discord_id=? AND source_id=?", (discord_id, source_id))
            stats["current"] = int(res_guesses_current.fetchone()[0])

            res_guesses_correct_current = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE discord_id=? AND source_id=? AND correct=1", (discord_id, source_id))
            stats["current_correct"] = int(res_guesses_correct_current.fetchone()[0])
        
        return stats

    def drop_player_stats(self, discord_id):
        query = "DELETE FROM HangmanStats WHERE discord_id=?"
        self.connection.cursor().execute(query, (discord_id, ))
        self.connection.commit()

    def get_source_stats(self, source_id):
        cur = self.connection.cursor()
        res_guesses = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE source_id=?", (source_id, ))
        guesses = int(res_guesses.fetchone()[0])

        corr_gueses = cur.execute("SELECT COUNT(*) FROM HangmanStats WHERE source_id=? AND correct=1", (source_id, ))
        correct = int(corr_gueses.fetchone()[0])

        rank = self.get_rank(source_id)
        top = list(itertools.islice(rank, 1))

        return {
            "guesses": guesses,
            "correct": correct,
            "top_scorer_id": top[0] if len(top) != 0 else None
        }

    def add(self, discord_id, source_id, card_id, correct):
        query = "INSERT INTO HangmanStats values (?, ?, ?, ?)"
        self.connection.cursor().execute(query, (discord_id, source_id, card_id, correct))
        self.connection.commit()

    def __initialize_stats(self):
        query = '''CREATE TABLE IF NOT EXISTS HangmanStats (discord_id text, source_id text, card_id text, correct integer);'''
        self.connection.cursor().execute(query)
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.connection.commit()
        self.connection.close()

    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.__initialize_stats()