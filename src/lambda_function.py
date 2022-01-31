import base64
import json
import logging
import tempfile
import zipfile
import requests

from moxfield import MoxfieldDeck
from collections import Counter
from shandalar import ShandalarContext

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Session
session = requests.Session()
session.headers['Origin'] = 'https://www.moxfield.com'
session.headers['Referrer'] = 'https://www.moxfield.com'

# Context
shandalar_context = ShandalarContext.load('./data/shandalar_data.tsv')

KEYS = [
    '0010', '0016', '0021', '0030', '0049', '0055', '0056', '0069',
    '0074', '0076', '0094', '0095', '0102', '0127', '0135', '0139',
    '0141', '0150', '0151', '0170', '0175', '0179', '0192', '0203',
    '0204', '0207', '0211', '0218', '0219', '0220', '0221', '0229',
    '0232', '0245', '0260', '0261', '0262', '0263', '0283', '0289',
    '0291', '0399', '0414', '0426', '0434', '0437', '0442', '0456',
    '0897', '0990', '0991', '0992', '0993', '0994', '0999'
]

MAX_DECKS = 25

def lambda_handler(event, context):
    body = event['body']

    if 'isBase64Encoded' in event and event['isBase64Encoded']:
        body = base64.b64decode(body)
        body = json.loads(body)

    data = body['data']

    if Counter(KEYS) != Counter(data.keys()):
        return {
            'statusCode': 400,
            'body': 'Bad request'
        }

    output = {key: [] for key in KEYS}
    errors = []

    for key in KEYS:
        for moxfield_id in data[key][:MAX_DECKS]:
            try:
                deck = MoxfieldDeck(moxfield_id, session).get()
            except:
                errors.append(f'{moxfield_id}: unreadable')
                continue

            mainboard = {standardize(card) : card_info['quantity'] for card, card_info in deck['mainboard'].items()}
            lines, problems = shandalar_context.convert(mainboard)

            if len(problems) != 0:
                errors.append(f'{moxfield_id}: had errors')
                for error in problems:
                    errors.append(error)
            else:
                output[key].append('\n'.join(lines))

        # Add errors for decks
        for moxfield_id in data[key][MAX_DECKS:]:
            errors.append(f'{moxfield_id}: too many decks defined for {key}')

    resp = create_zip_file(output, errors)

    return {
        'headers': {"Content-Type": "application/zip"},
        'statusCode': 200,
        'body': resp,
        'isBase64Encoded': True
    }


def standardize(card_name):
    return card_name.split('//')[0].strip()


def create_zip_file(decks, errors):
    with tempfile.SpooledTemporaryFile(mode='w+b') as temp:
        with zipfile.ZipFile(temp, mode='w') as zip:

            # Write Files
            for key, decklists in decks.items():
                for i, decklist in enumerate(decklists):
                    zip.writestr(f'/data/{key}/{i}.dck', decklist)

            # Write Errors
            zip.writestr(f'/errors/errors.txt', '\n'.join(errors))

        # Actual write
        temp.seek(0)
        return base64.b64encode(temp.read()).decode('utf-8')
