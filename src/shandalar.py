from moxfield import MoxfieldDeck

def shandalarize(body, card_collection, session):
    response = {
        'decks': {},
        'errors': {},
        'next': {}
    }

    if 'moxfield' in body:
        this_moxfield = body['moxfield'][:10]
        next_moxfield = body['moxfield'][10:]
        response['decks']['moxfield'] = {}
        response['errors']['moxfield'] = []
        response['next']['moxfield'] = next_moxfield

        for moxfield_id in this_moxfield:
            try:
                deck = MoxfieldDeck(moxfield_id, session).get()
                process_moxfield_deck(
                    response['decks']['moxfield'], deck, card_collection)
            except:
                response['errors']['moxfield'].append({
                    'deck_id': moxfield_id,
                    'errorCode': 'generalError'
                })

    return response

def process_moxfield_deck(moxfield_decks, deck, card_collection):
    public_id = deck['publicId']
    moxfield_decks[public_id] = {'cards': {}, 'errors': {}}

    for (card, val) in deck['mainboard'].items():
        if '//' in card:
            card = card.split('//')[0].strip()

        if card not in card_collection.name_index:
            moxfield_decks[public_id]['errors'][card] = 'notImplementedShandalar'
            continue

        moxfield_decks[public_id]['cards'][card] = f'{card_collection.name_index[card].shandalar_id}\t{val["quantity"]}\t{card}'
