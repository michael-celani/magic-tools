from multiprocessing import AuthenticationError
import requests
import urllib.parse
import dateutil.parser
from datetime import datetime, timezone

# https://api.moxfield.com/v2/cards/search


class MoxfieldAuth(requests.auth.AuthBase):

    @staticmethod
    def login(username, password):
        payload = {'userName': username, 'password': password}
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json'
        }
        r = requests.post(
            'https://api.moxfield.com/v1/account/token', json=payload, headers=headers)

        if r.status_code != 200:
            raise ValueError('incorrect password')

        resp_json = r.json()
        return MoxfieldAuth(resp_json['access_token'], resp_json['refresh_token'], dateutil.parser.parse(resp_json['expiration']))

    def __refresh(self):
        payload = {'refreshToken': self.refresh_token}
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json'
        }
        r = requests.post(
            'https://api.moxfield.com/v1/account/token/refresh', json=payload, headers=headers)

        if r.status_code != 200:
            raise ValueError('bad refresh')

        resp_json = r.json()
        self.access_token = resp_json['access_token']
        self.refresh_token = resp_json['refresh_token']
        self.expiration = dateutil.parser.parse(resp_json['expiration'])

    def __init__(self, access_token: str, refresh_token: str, expiration: datetime):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiration = expiration

    def __call__(self, r):
        if datetime.now(timezone.utc) > self.expiration:
            self.__refresh()

        r.headers['Authorization'] = f'Bearer {self.access_token}'
        r.headers['Origin'] = 'https://www.moxfield.com'
        r.headers['Referrer'] = 'https://www.moxfield.com'
        return r


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

        url_card_id = urllib.parse.quote(card_id, safe='')

        if value == card_amount:
            return
        elif value == 0:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard'
            r = self.session.post(url, json=json, headers=headers)
        elif card_amount == 0:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard/{url_card_id}'
            self.session.delete(url, headers=headers)
        else:
            url = f'https://api.moxfield.com/v2/decks/{deck_id}/cards/mainboard/{url_card_id}'
            self.session.put(url, json=json, headers=headers)

    def get(self, public_id):
        public_id = urllib.parse.quote(public_id, safe='')
        r = self.session.get(
            f'https://api.moxfield.com/v2/decks/all/{public_id}')
        return r.json()

    def __init__(self, session):
        self.session = session
        pass
