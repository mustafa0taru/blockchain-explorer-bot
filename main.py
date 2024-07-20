import pandas as pd
import numpy as np
import requests
import math
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Replace with your own Alchemy API key
alchemy_key = ''

# Replace with your Telegram Bot API token
telegram_token = ''
bot = Bot(token=telegram_token)

def get_nft_data(owner):
    URL = f'https://eth-mainnet.g.alchemy.com/nft/v3/{apiKey}/getNFTsForOwner?owner=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045&withMetadata=true&excludeFilters%5B%5D=SPAM&includeFilters%5B%5D=AIRDROPS&pageSize=100'
    r = requests.get(url=URL)

    if r.status_code != 200:
        return 'No NFTs found', None

    data = r.json()
    nfts = data.get('ownedNfts', [])

    if 'pageKey' in data:
        more_pages = True
        while more_pages:
            URL = f'https://eth-mainnet.g.alchemy.com/nft/v3/{apiKey}/getNFTsForOwner?owner=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045&withMetadata=true&excludeFilters%5B%5D=SPAM&includeFilters%5B%5D=AIRDROPS&pageSize=100'
            r = requests.get(url=URL)
            data = r.json()
            nfts.extend(data.get('ownedNfts', []))
            if 'pageKey' not in data:
                more_pages = False

    return None, nfts

def calculate_key_metrics(nfts):
    holdings = pd.DataFrame(nfts)
    holdings['balance'] = pd.to_numeric(holdings['balance'])
    holdings['address'] = holdings.apply(lambda x: x['contract']['address'], axis=1)
    holdings = holdings[['address', 'balance']]
    holdings = holdings.groupby(['address']).sum().reset_index()

    total_nfts = holdings['balance'].sum()
    unique_contracts = holdings['address'].nunique()
    top_collections = holdings.sort_values('balance', ascending=False).head(5)
    average_holding = holdings['balance'].mean()

    key_metrics = {
        'Total NFTs Held': total_nfts,
        'Unique NFT Contracts': unique_contracts,
        'Top Collections': top_collections.to_dict(orient='records'),
        'Average Holding per Collection': average_holding,
    }

    return key_metrics

def get_nft_details(nfts, address):
    details = [nft for nft in nfts if nft['contract']['address'] == address]
    return details

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to diins_bot! Send me the name of an NFT project or a wallet address to get key metrics and details.')

def nft_info(update: Update, context: CallbackContext) -> None:
    input_text = update.message.text
    chat_id = update.message.chat_id

    update.message.reply_text(f'Fetching data for {input_text}...')

    message, nfts = get_nft_data(input_text)
    if message:
        bot.send_message(chat_id=chat_id, text=message)
        return

    key_metrics = calculate_key_metrics(nfts)
    summary = f"""
    NFT Key Metrics for {input_text}:
    Total NFTs Held: {key_metrics['Total NFTs Held']}
    Unique NFT Contracts: {key_metrics['Unique NFT Contracts']}
    Average Holding per Collection: {key_metrics['Average Holding per Collection']:.2f}

    Top Collections:
    """
    for collection in key_metrics['Top Collections']:
        summary += f"- Contract Address: {collection['address']}, NFTs Held: {collection['balance']}\n"

    bot.send_message(chat_id=chat_id, text=summary)

def nft_details(update: Update, context: CallbackContext) -> None:
    address = update.message.text
    chat_id = update.message.chat_id

    message, nfts = get_nft_data(address)
    if message:
        bot.send_message(chat_id=chat_id, text=message)
        return

    details = get_nft_details(nfts, address)
    if not details:
        bot.send_message(chat_id=chat_id, text='No details found for this contract address.')
        return

    for detail in details:
        metadata = detail.get('metadata', {})
        attributes = metadata.get('attributes', [])
        attributes_str = '\n'.join([f"{attr['trait_type']}: {attr['value']}" for attr in attributes])

        detail_text = f"""
        Contract Address: {detail['contract']['address']}
        Token ID: {detail['id']['tokenId']}
        Title: {metadata.get('title', 'N/A')}
        Description: {metadata.get('description', 'N/A')}
        Attributes:
        {attributes_str}
        """
        bot.send_message(chat_id=chat_id, text=detail_text)

def main():
    updater = Updater(token=telegram_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, nft_info))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^0x[a-fA-F0-9]{40}$'), nft_details))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main
