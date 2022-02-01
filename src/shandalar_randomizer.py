import asyncio
import os
import random
import shutil
import sys
from pathlib import Path

async def randomize(shanda_path, data_path):
    sub_paths = [x for x in data_path.iterdir() if x.is_dir()]

    for sub_path in sub_paths:
        deck_name = sub_path.parts[-1]
        deck_path = random.choice([x for x in sub_path.iterdir() if x.is_file()])
        out_path = shanda_path / f'{deck_name}.dck'
        print(f'Copying {deck_path} to {out_path}.')
        try:
            shutil.copyfile(deck_path, shanda_path / f'{deck_name}.dck')
        except:
            sys.stderr.write("Error copying file.\n")

    print('\n')

async def main(interval, shanda_path, data_path):
    while True:
        await asyncio.gather(
                asyncio.sleep(interval),
                randomize(shanda_path, data_path),
            )

if __name__ == "__main__":
    script_loc = os.path.realpath(__file__)
    shanda_path = Path(script_loc).parent
    data_path = shanda_path / 'data'

    if not data_path.exists():
        raise RuntimeError('shandalar data folder does not exist')

    print(f'Randomizing decks from {data_path}....')
    asyncio.run(main(30, shanda_path, data_path))