#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import sqrt
import random
import pandas as pd
from time import sleep
import urllib.request
from bs4 import BeautifulSoup


def getTokenPrice(tokenStr):
    '''
    Assumes a string matching an existing html child of 'coingecko.com/en/coins/', i.e. 'ethereum'.
    Returns float of current asset price (USD) as given on coingecko.com.
    '''
    url = 'https://www.coingecko.com/en/coins/' + tokenStr
    userAgent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)' + \
        ' Chrome/41.0.2228.0 Safari/537.36'
    req = urllib.request.Request(url, headers= {'User-Agent' : userAgent})
    html = urllib.request.urlopen(req)
    bs = BeautifulSoup(html.read(), 'html.parser')
    
    # Scrape price data
    varList = bs.findAll('span', {'class': 'no-wrap'})  
    priceStr = varList[0].get_text()
    priceUSD = float(priceStr.replace(',','').replace('$',''))
    
    # Sleep max 2 seconds before function can be called again
    sleep(random.random()*2)
    
    return priceUSD


def balanceAssets(asset1Amount, asset1Price, asset2Amount, asset2Price):
    '''
    Assumes token amounts at pool entry and their current usd values.
    Returns estimated current amounts based on current asset prices,
    not factoring in accumulated fees.
    '''
    # Simulation of Uniswap/Sushiswap balancing function based on price of assets
    meanVal = sqrt(asset1Amount * asset1Price + asset2Amount * asset2Price)**2
    currentAsset1 = 0.5 * meanVal / asset1Price
    currentAsset2 = 0.5 * meanVal / asset2Price
    
    return currentAsset1, currentAsset2


def updatePrices(dataDict, verbose=True):
    '''
    Assumes nested dict of asset pairings of asset prices.
    Updates token prices by calling getTokenPrice() and returns updated version.
    '''
    # Temp storage to prevent unnecessary scraping
    alreadyScraped = {}
    
    # Cycle through token pairings as given in input dict
    for pairKey in dataDict.keys():
        try:
            strKeys = ['colStr', 'assStr']
        except KeyError:
            print('''
            %s is not in the data dict yet.
            You need to add "colStr" and "assStr" values for %s first.''' % (pairKey, pairKey))

        # Update collateral & asset per token pairing
        updateMap = {'colStr': 'priceCol', 'assStr': 'priceAss'}
        for nameKey, valKey in updateMap.items():
            tokenStr = dataDict[pairKey][nameKey]
            if tokenStr in alreadyScraped:
                dataDict[pairKey][valKey] = alreadyScraped[tokenStr]
            else:
                price = getTokenPrice(tokenStr)
                dataDict[pairKey][valKey] = price
                alreadyScraped[tokenStr] = price
                if verbose:
                    print('Successfully scraped current data for %s from Coingecko.' % tokenStr)
    if verbose:
        print('')
                    
    return dataDict


def getPoolStatus(data, roundTo=2):
    '''
    Assumes nested dict of token pairs. Returns nested dict:
    Returns per pair: current value of pool, current amount of collateral,
    current amount of asset.
    '''
    poolData = {}
    for pair in data:
        d = data[pair]
        amtColNow, amtAssNow = balanceAssets(
            d['numColEntry'],
            d['priceCol'],
            d['numAssEntry'],
            d['priceAss']
            )
        poolVal = amtColNow * d['priceCol'] + amtAssNow * d['priceAss']
        poolData[pair] = {
            'poolValue': round(poolVal, roundTo),
            'amtCol': round(amtColNow, roundTo),
            'amtAss': round(amtAssNow, roundTo)
        }
        
    return poolData




