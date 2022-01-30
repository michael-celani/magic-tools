import requests
import urllib.parse
import dateutil.parser
from datetime import datetime, timezone

class MoxfieldAuth(requests.auth.AuthBase):

    def __login(self):
        payload = {'userName': self.__username, 'password': self.__password}
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json'
        }
        r = requests.post(
            'https://api.moxfield.com/v1/account/token', json=payload, headers=headers)

        if r.status_code != 200:
            raise ValueError('bad login')

        self.__update(r.json())

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
            self.__login()

        self.__update(r.json())

    def __update(self, ref_json):
        self.access_token = ref_json['access_token']
        self.refresh_token = ref_json['refresh_token']
        self.expiration = dateutil.parser.parse(ref_json['expiration'])

    def __init__(self, username: str, password: str):
        self.access_token = None
        self.refresh_token = None
        self.expiration = None
        self.__username = username
        self.__password = password

    def __call__(self, r):
        if self.expiration is None:
            self.__login()

        elif datetime.now(timezone.utc) > self.expiration:
            self.__refresh()

        r.headers['Authorization'] = f'Bearer {self.access_token}'
        r.headers['Origin'] = 'https://www.moxfield.com'
        r.headers['Referrer'] = 'https://www.moxfield.com'
        return r

class MoxfieldSearch:

    def search(self, fmt, filt):
        fmt = urllib.parse.quote(fmt, safe='')
        filt = urllib.parse.quote(filt, safe='')
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        params = {
            'pageNumber': 1,
            'pageSize': 64,
            'sortType': 'updated',
            'sortDirection': 'Descending',
            'fmt': fmt,
            'filter': filt
        }
        r = self.session.get(f'https://api.moxfield.com/v2/decks/search', params=params, headers=headers)
        data = r.json()
        for pageNumber in range(2, data['totalPages'] + 1):
            for obj in data['data']:
                yield MoxfieldDeck(obj['publicId'], self.session)
            
            params['pageNumber'] = pageNumber
            r = self.session.get(f'https://api.moxfield.com/v2/decks/search', params=params, headers=headers)
            data = r.json()

    def __init__(self, session):
        self.session = session

class MoxfieldDeck:

    def bulk_edit(self, mainboard, sideboard, maybeboard):
        public_id = urllib.parse.quote(self.public_id, safe='')
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        json = {
            "mainboard":'\n'.join(f'{value} {key}' for key, value in mainboard.items()),
            "sideboard":'\n'.join(f'{value} {key}' for key, value in sideboard.items()),
            "maybeboard":'\n'.join(f'{value} {key}' for key, value in maybeboard.items()),
            "playStyle":"paperDollars",
            "pricingProvider":"tcgplayer"
        }
        url = f'https://api.moxfield.com/v2/decks/{public_id}/bulk-edit'
        r = self.session.put(url, json=json, headers=headers)
        return r.json()


    def set_mainboard(self, card_id, card_amount):
        deck = self.get()
        deck_id = deck['id']
        deck_mainboard = deck['mainboard']

        value = 0
        for obj in deck_mainboard.values():
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

    def get(self):
        public_id = urllib.parse.quote(self.public_id, safe='')
        r = self.session.get(
            f'https://api.moxfield.com/v2/decks/all/{public_id}')
        
        if r.status_code != 200:
            raise Exception()

        return r.json()

    def __init__(self, public_id, session):
        self.public_id = public_id
        self.session = session
        pass
