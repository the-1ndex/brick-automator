import json
import time
from pathlib import Path

import requests
import typer
from base58 import b58decode
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from rich.progress import track

MODIFIED_URI_PREFIX = f"https://nft-collage.s3.eu-central-1.amazonaws.com/"


def load_wallet(update_wallet: Path) -> bytes:
    wallet = open(update_wallet).read().strip()
    try:
        return b58decode(wallet)  # base58 format
    except:
        return bytes(json.loads(wallet))  # array of integers format


def send_transactions(wallet: Keypair, result):
    client = Client('https://api.mainnet-beta.solana.com')
    print('Signing and sending transactions')
    for tx in track(result['transactions']):
        tx = Transaction.deserialize(b58decode(tx['transaction']))
        client.send_transaction(tx, wallet)
        time.sleep(1)


def main(collection_symbol: str = typer.Option('', help='Collection symbol'),
         no_confirmation: bool = typer.Option(False, help='Automatically approve transactions'),
         watermark_text: str = typer.Option('', help='Watermark text for bricking the NFTs'),
         update_wallet: Path = typer.Argument(..., help="Path to update authority wallet"),
         api_token: str = typer.Argument(..., help='CoralCube API token')):
    wallet = Keypair.from_secret_key(load_wallet(update_wallet))
    endpoint = f'https://api.coralcube.cc/{api_token}/inspector'
    print('Using update authority', wallet.public_key)
    extra_args = '' if collection_symbol is None else f'&collection_symbol={collection_symbol}'
    mints = requests.get(f'{endpoint}/getMints?update_authority={wallet.public_key}' + extra_args).json()
    total = len(mints)
    should_bricks = []
    should_reverts = []
    for mint in mints:
        debt = 0
        metadata = mint['metadata']
        for sale in mint['sales']:
            expected = sale['price'] * metadata['seller_fee_basis_points'] / 10000
            actual = sale['royalty_fee']
            debt += expected - actual
        bricked = metadata['uri'].startswith(MODIFIED_URI_PREFIX)
        listed = 'listing' in mint
        brickable = (debt > 0 or listed)
        if brickable and not bricked:
            should_bricks.append(mint)
        if not brickable and bricked:
            should_reverts.append(mint)
    print(f'Found {total} mints')
    print(f'{len(should_reverts)} mints should be reverted to their original state')
    print(f'{len(should_bricks)} mints should be bricked')
    if should_reverts:
        if no_confirmation:
            confirmed = True
        else:
            confirmed = typer.confirm(f"Do you want to revert {len(should_reverts)} NFTs to their original state?")
        if confirmed:
            result = requests.post(f'{endpoint}/getUpdateMetadataTransactions', json={
                "mints": [mint['metadata']['mint'] for mint in should_reverts],
                "revert": True
            }).json()
            send_transactions(wallet, result)
    if should_bricks:
        if no_confirmation:
            confirmed = True
        else:
            confirmed = typer.confirm(f"Do you want to brick {len(should_bricks)} NFTs?")
        if confirmed:
            result = requests.post(f'{endpoint}/getUpdateMetadataTransactions', json={
                "mints": [mint['metadata']['mint'] for mint in should_bricks],
                "image_update": {
                    "blur": 5,
                    "watermark": watermark_text
                },
                "revert": False
            }).json()
            send_transactions(wallet, result)


if __name__ == "__main__":
    typer.run(main)
