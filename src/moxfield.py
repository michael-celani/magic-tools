import requests

# https://api.moxfield.com/v2/cards/search

class Moxfield:

    def login(self, username, password):
        s = requests.Session()
        payload = {'userName': username, 'password': password}
        headers = {
            'Accept': 'application/json, text/plain, */*', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json'
        }
        r = s.post('https://api.moxfield.com/v1/account/token', json=payload, headers=headers)

        access_token = r.json()['access_token']
        s.headers['Authorization']= f'Bearer {access_token}'
        s.headers['Origin'] = 'https://www.moxfield.com'
        s.headers['Referrer'] = 'https://www.moxfield.com'
        return s

    def __init__(self, username, password):
        self.session = self.login(username, password)
        self.decks = Decks(self.session)

class Decks:

    def set_mainboard(self, public_id, card_id, card_amount):
        deck = self.get(public_id)
        deck_id = deck['id']
        deck_mainboard = deck['mainboard']

        value = 0
        for obj in deck['mainboard'].values():
            if obj['card']['id'] == card_id:
                value = obj['quantity']

        headers = {
            'Accept': '*/*', 
            'Accept-Language': 'en-US,en;q=0.5',
        }

        json = {'cardId': card_id, 'quantity': card_amount}

        if value == 0:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard'
            r = self.session.post(url, json=json, headers=headers)
        elif card_amount == 0:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard/{card_id}'
            self.session.delete(url, headers=headers)
        else:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard/{card_id}'
            self.session.put(url, json=json, headers=headers)
        

    def get(self, public_id):
        r = self.session.get(f'https://api.moxfield.com/v2/decks/all/{public_id}')
        return r.json()

    def __init__(self, session):
        self.session = session
        pass
