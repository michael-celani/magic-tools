import itertools

class CardRecord:

    def __init__(self, name, shandalar_id, shandalar_internal_id, moxfield_id):
        self.name = name
        self.shandalar_id = shandalar_id
        self.shandalar_internal_id = shandalar_internal_id
        self.moxfield_id = moxfield_id

class CardCollection:
    
    @staticmethod
    def load(tsv_path):
        with open(tsv_path) as fi:
            return CardCollection(CardCollection.__load(fi))

    @staticmethod
    def __load(fi):
        for line in itertools.islice(fi, 1, None):
            card_line = line.strip().split('\t')
            yield CardRecord(card_line[2], card_line[0], int(card_line[1]), card_line[3])

    def __init__(self, card_iterable):
        self.cards = []
        self.name_index = {}
        self.shandalar_internal_index = {}

        for card in card_iterable:
            self.cards.append(card)
            self.name_index[card.name] = card
            self.shandalar_internal_index[card.shandalar_internal_id] = card
