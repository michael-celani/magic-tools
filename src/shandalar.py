import json
import urllib3
import urllib.parse


def shandalarize(body):
    response = {
        'decks': {},
        'errors': {},
        'next': {}
    }

    # Load the shandalar path.
    card_ids = load_shandalar_data(r'./shandalar_list.txt')

    # Stard the urllib3 pool manager.
    http = urllib3.PoolManager()

    if 'moxfield' in body:
        this_moxfield = body['moxfield'][:10]
        next_moxfield = body['moxfield'][10:]
        response['decks']['moxfield'] = {}
        response['errors']['moxfield'] = []
        response['next']['moxfield'] = next_moxfield

        for moxfield_id in this_moxfield:
            try:
                deck = get_moxfield_deck(moxfield_id, http)
                process_moxfield_deck(
                    response['decks']['moxfield'], deck, card_ids)
            except:
                response['errors']['moxfield'].append({
                    'deck_id': moxfield_id,
                    'errorCode': 'generalError'
                })

    return response


def load_shandalar_data(shandalar_path):
    card_ids = {}

    with open(shandalar_path) as fi:
        for line in fi:
            card_data = line.strip().split('\t')
            card_ids[card_data[1]] = card_data[0]

    return card_ids


def get_moxfield_deck(public_id, http):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/json',
        'Origin': 'https://www.moxfield.com',
        'Referrer': 'https://www.moxfield.com'
    }

    public_id = urllib.parse.quote(public_id, safe='')
    r = http.request(
        'GET', f'https://api.moxfield.com/v2/decks/all/{public_id}', headers=headers)

    if r.status != 200:
        raise Exception()

    return json.loads(r.data.decode('utf-8'))


def process_moxfield_deck(moxfield_decks, deck, card_ids):
    public_id = deck['publicId']
    moxfield_decks[public_id] = {'cards': {}, 'errors': {}}

    for (card, val) in deck['mainboard'].items():
        if '//' in card:
            card = card.split('//')[0].strip()

        if card not in card_ids:
            moxfield_decks[public_id]['errors'][card] = 'notImplementedShandalar'
            continue

        moxfield_decks[public_id]['cards'][card] = f'{card_ids[card]}\t{val["quantity"]}\t{card}'
