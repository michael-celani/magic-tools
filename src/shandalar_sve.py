import struct
from collections import Counter

IN_MAINBOARD = 0x1
IN_SIDEBOARD = 0x8
DECK_MEMORY_LOCATION = 0x1424

def read_decklist(save_file_ptr, card_collection):
    mainboard = Counter()
    sideboard = Counter()

    # Seek to the location of the files.
    save_file_ptr.seek(DECK_MEMORY_LOCATION)

    for i in range(499):
        buf = save_file_ptr.read(4)
        card_internal_id, card_location = struct.unpack('<HH', buf)

        if card_internal_id == 0xFFFF:
            continue

        try:
            card_name = card_collection.shandalar_internal_index[card_internal_id].name
            
            if card_location == IN_MAINBOARD:
                mainboard.update([card_name])
            elif card_location == IN_SIDEBOARD:
                sideboard.update([card_name])
        except:
            if card_location == 0x01:
                print(f'id in deck not found: {card_internal_id}')
            elif card_location == 0x08:
                print(f'id out of deck not found: {card_internal_id}')
    
    return {'mainboard': mainboard, 'sideboard': sideboard}
