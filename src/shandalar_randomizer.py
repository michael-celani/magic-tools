import asyncio
import argparse
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
        
        try:
            shutil.copyfile(deck_path, shanda_path / f'{deck_name}.dck')
            print(f'Copied {deck_path} to {out_path}.')
        except:
            sys.stderr.write("Error copying file.\n")
            print(f'Error copying {deck_path} to {out_path}.')

    print('\n')

async def main(interval, shanda_path, data_path):
    while True:
        await asyncio.gather(
                asyncio.sleep(interval),
                randomize(shanda_path, data_path),
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Runs the Shandalar randomizer.')
    parser.add_argument('path', type=Path, help='The directory of the Shandalar decks.')
    args = parser.parse_args()

    shanda_path = args.path
    data_path = shanda_path / 'data'

    if not data_path.exists():
        raise RuntimeError('shandalar data folder does not exist')

    print(f'Randomizing decks from {data_path} to {shanda_path}...')
    asyncio.run(main(30, shanda_path, data_path))