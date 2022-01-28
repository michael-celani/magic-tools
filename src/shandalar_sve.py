import itertools
import struct
from collections import Counter
import json

save_file = './src/MAGIC7.SVE'
shandalar_path = './src/all_data.tsv'

card_data = {}

with open(shandalar_path) as fi:
    for line in itertools.islice(fi, 1, None):
        card_line = line.strip().split('\t')
        card_id = card_line[0]
        card_internal = card_line[1]
        card_name = card_line[2]

        try:
            card_data[int(card_internal)] = {'id': card_id, 'name': card_name} 
        except:
            pass


with open(save_file, 'rb') as save:
    c = Counter()
    s = Counter()
    save.seek(0x01424)
    for i in range(499):
        buf = save.read(4)
        card_internal_id = struct.unpack('<HH', buf)
        if card_internal_id[0] != 0xFFFF:
            try:
                if card_internal_id[1] == 0x01:
                    c.update([card_data[card_internal_id[0]]['name']])
                elif card_internal_id[1] == 0x08:
                    s.update([card_data[card_internal_id[0]]['name']])
            except:
                if card_internal_id[1] == 0x01:
                    print(f'id in deck not found: {card_internal_id[0]}')
                elif card_internal_id[1] == 0x08:
                    print(f'id out of deck not found: {card_internal_id[0]}')
    
    for key, value in c.items():
        print(f'{value} {key}')

    print('\nSIDEBOARD:')

    for key, value in s.items():
        print(f'{value} {key}')
        