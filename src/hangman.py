from moxfield.auth import MoxfieldAuth
from moxfield.decks import MoxfieldSpecificDeckAPI
from moxfield.search import MoxfieldSearchAPI
import sqlite3
import requests

class CommanderHangman:

    def guess(self, discord_id, query):
        card = self.__get_card(query)

        if card is None:
            return {
                "card_name": None,
                "guess_correct": False,
                "guess_unique": True
            }

        card_id = card['id']
        card_name = card['name']
        
        hangman_target_deck = self.hangman_target.get()
        guess_unique = not (card_name in hangman_target_deck['mainboard'] or card_name in hangman_target_deck['maybeboard'])
        
        if card_name not in self.hangman_source_deck['mainboard']:
            if guess_unique:
                self.hangman_target.maybeboard.set(card_id, 1)
                self.stats.add(discord_id, self.hangman_source.public_id, card_id, False)

            return {
                "card_name": card_name,
                "guess_correct": False,
                "guess_unique": guess_unique
            }

        # Update deck.
        if guess_unique:
            quantity = self.hangman_source_deck['mainboard'][card_name]['quantity']
            self.hangman_target.mainboard.set(card_id, quantity)
            self.stats.add(discord_id, self.hangman_source.public_id, card_id, True)

        return {
            "card_name": card_name,
            "guess_correct": True,
            "guess_unique": guess_unique
         }

    def __get_card(self, query):
        params = {'fuzzy': query}

        r = requests.get('https://api.scryfall.com/cards/named', params=params)

        try:
            r.raise_for_status()
            resp = r.json()
            name = resp['name']
            query = f'!"{name}"'
        except:
            return None

        card = self.search.search_single(query)

        if card is None:
            return None

        return card

    def __init__(self, session, source, target, stats):
        self.hangman_source = MoxfieldSpecificDeckAPI(source, session)
        self.hangman_target = MoxfieldSpecificDeckAPI(target, session)
        self.hangman_source_deck = self.hangman_source.get()
        self.search = MoxfieldSearchAPI(session)
        self.stats = stats
        pass

class CommanderHangmanStats:

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

    def add(self, discord_id, source_id, card_id, correct):
        query = "INSERT INTO HangmanStats values (?, ?, ?, ?)"
        self.connection.cursor().execute(query, (discord_id, source_id, card_id, correct))
        self.connection.commit()

    def __initialize_stats(self):
        query = '''CREATE TABLE IF NOT EXISTS HangmanStats (discord_id text, source_id text, card_id text, correct integer);'''
        self.connection.cursor().execute(query)
        self.connection.commit()

    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.__initialize_stats()
        pass