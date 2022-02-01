import argparse
import pathlib
import time
import requests
from moxfield.auth import MoxfieldAuth
from moxfield.decks import MoxfieldDeckAPI
from moxfield.folders import MoxfieldDeckFoldersAPI

def load_deck(fi):
    deck = {}
    deck_lines = [x.strip() for x in fi.readlines() if x.startswith('.') and '\t' in x]

    for line in deck_lines:
        card_id, card_quantity, card_name = line.split('\t')
        deck[card_name] = card_quantity

    print(deck)
    return deck

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Uploads a Shandalar deck to Moxfield.')
    parser.add_argument('username', type=str, help='The Moxfield username.')
    parser.add_argument('password', type=str, help='The Moxfield password.')
    parser.add_argument('path', type=pathlib.Path, help='The directory of the Shandalar decks.')
    args = parser.parse_args()

    session = requests.Session()
    session.auth = MoxfieldAuth(args.username, args.password)
    factory = MoxfieldDeckAPI(session)
    folders = MoxfieldDeckFoldersAPI(session)
    upload_folder = folders.create(args.path.name)

    decklist = None
    for path in (x for x in args.path.iterdir() if x.is_file() and x.suffix == '.dck'):
        print(path)
        with open(path, 'r', encoding="utf-8") as fi:
            deck = factory.create(path.name, load_deck(fi), visibility='unlisted')
            upload_folder.add_deck(deck)
            print(f'https://www.moxfield.com/decks/{deck.public_id}')
        time.sleep(2)
