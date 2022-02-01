import argparse
import pathlib
import requests
from moxfield import MoxfieldAuth, MoxfieldDeckFactory

def load_deck(fi):
    deck = {}
    deck_lines = [x.strip() for x in fi.readlines() if x.startswith('.') and '\t' in x]

    for line in deck_lines:
        card_id, card_quantity, card_name = line.split('\t')
        deck[card_name] = card_quantity

    return deck

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Uploads a Shandalar deck to Moxfield.')
    parser.add_argument('username', type=str, help='The Moxfield username.')
    parser.add_argument('password', type=str, help='The Moxfield password.')
    parser.add_argument('path', type=pathlib.Path, help='The path of the Shandalar deck.')
    args = parser.parse_args()

    session = requests.Session()
    session.auth = MoxfieldAuth(args.username, args.password)
    factory = MoxfieldDeckFactory(session)

    decklist = None
    with open(args.path, 'r') as fi:
        decklist = load_deck(fi)
    
    deck = factory.create(args.path.name, decklist, visibility='unlisted')
    print(f'https://www.moxfield.com/decks/{deck.public_id}')
