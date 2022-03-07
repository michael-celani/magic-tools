import itertools
import struct
from typing import Tuple, Dict, Iterator, List
from collections import Counter

IN_MAINBOARD = 0x1
IN_SIDEBOARD = 0x8
DECK_MEMORY_LOCATION = 0x1420
DECK_CARD_MAXIMUM = 500
DECK_CARD_SIZE = 4

class ShandalarCard:

    def __init__(self, name, shandalar_id, shandalar_internal_id, moxfield_id):
        self.name = name
        self.shandalar_id = shandalar_id
        self.shandalar_internal_id = shandalar_internal_id
        self.moxfield_id = moxfield_id

class ShandalarContext:
    
    @staticmethod
    def load(tsv_path):
        with open(tsv_path) as fi:
            return ShandalarContext(ShandalarContext.__load(fi))

    @staticmethod
    def __load(fi):
        for line in itertools.islice(fi, 1, None):
            card_line = line.strip().split('\t')
            yield ShandalarCard(card_line[2], card_line[0], int(card_line[1]), card_line[3])

    def convert(self, mainboard: Dict[str, int]) -> Tuple[List[str], List[str]]:
        lines = []
        errors = []

        for card_name, quantity in mainboard.items():
            if card_name not in self.name_index:
                errors.append(f'{card_name} was not found in Shandalar\n')
            else:
                card = self.name_index[card_name]
                lines.append(f'{card.shandalar_id}\t{quantity}\t{card_name}\n')
        
        return (lines, errors)

    def add(self, card):
        self.cards.append(card)
        self.name_index[card.name] = card
        self.shandalar_internal_index[card.shandalar_internal_id] = card

    def __init__(self, card_iterable):
        self.cards = []
        self.name_index = {}
        self.shandalar_internal_index = {}
        for card in card_iterable:
            self.add(card)

class ShandalarSave:

    def __read_decklist(self) -> bytes:
        with open(self.file_name, 'rb') as fi:
            fi.seek(DECK_MEMORY_LOCATION)
            return fi.read(DECK_CARD_SIZE * DECK_CARD_MAXIMUM)

    def __write_decklist(self, decklist: bytes) -> None:
        with open(self.file_name, 'r+b') as fi:
            fi.seek(DECK_MEMORY_LOCATION)
            fi.write(decklist)

    def __decklist_cards(self) -> Iterator[Tuple[int, bool]]:
        buf = self.__read_decklist()

        for card_internal_id, card_location in struct.iter_unpack('<HH', buf):
            # Ignore empty slots
            if card_internal_id == 0xFFFF:
                continue

            if card_location == IN_MAINBOARD:
                yield (card_internal_id, True)
            elif card_location == IN_SIDEBOARD:
                yield (card_internal_id, False)
            else:
                raise RuntimeError(f'card with id {card_internal_id} neither in mainboard or sideboard')

    def read_decklist(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        mainboard = Counter()
        sideboard = Counter()

        for card_id, in_mainboard in self.__decklist_cards():
            try:
                card_name = self.context.shandalar_internal_index[card_id].name
                cardboard = mainboard if in_mainboard else sideboard
                cardboard.update([card_name])
            except:
                raise RuntimeError(f'card with id {card_id} not found in Shandalar context')

        return (mainboard, sideboard)

    def write_decklist(self, mainboard: Dict[str, int], sideboard: Dict[str, int]):
        mainboard = mainboard if mainboard is not None else {}
        sideboard = sideboard if sideboard is not None else {}
        num_mainboard = sum(mainboard.values())
        num_sideboard = sum(sideboard.values())
        empty_slots = DECK_CARD_MAXIMUM - num_mainboard - num_sideboard

        if empty_slots < 0:
            raise RuntimeError('The maximum collection size in Shandalar is 500.')
        
        def yield_cards(cards: dict[str, int], in_mainboard: bool):
            for card, quantity in cards.items():
                card_internal_id = self.context.name_index[card].shandalar_internal_id
                card_internal_bytes = struct.pack('<HH', card_internal_id, IN_MAINBOARD if in_mainboard else IN_SIDEBOARD)
                yield from itertools.repeat(card_internal_bytes, quantity)
        
        card_list_bytes = itertools.chain(yield_cards(mainboard, True), yield_cards(sideboard, False), itertools.repeat(struct.pack('<HH', 0xFFFF, 0xFFFF), empty_slots))
        self.__write_decklist(b''.join(card_list_bytes))

    def __init__(self, file_name: str, context: ShandalarContext):
        self.file_name = file_name
        self.context = context