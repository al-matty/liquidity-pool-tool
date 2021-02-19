#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from math import sqrt
import random
import pandas as pd
from time import sleep
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime

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

def balanceAssets(asset1Amount, asset1Price, asset2Amount, asset2Price, roundTo=None):
    '''
    Assumes token amounts at pool entry and their current usd values.
    Returns estimated current amounts based on current asset prices,
    not factoring in accumulated fees.
    '''
    # Simulation of Uniswap/Sushiswap balancing function based on price of assets
    meanVal = sqrt(asset1Amount * asset1Price + asset2Amount * asset2Price)**2
    currentAsset1 = 0.5 * meanVal / asset1Price
    currentAsset2 = 0.5 * meanVal / asset2Price

    if roundTo:
        return round(currentAsset1, roundTo), round(currentAsset2, roundTo)
    else:
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
                    print('Successfully scraped price data for %s from Coingecko.' % tokenStr)
    if verbose:
        print('')

    return dataDict

def getPoolVal(asset1Amount, asset1Price, asset2Amount, asset2Price, roundTo=None):
    '''
    Returns total current value of liquidity pool based on given asset
    amounts and prices.
    '''
    poolVal = asset1Amount * asset1Price + asset2Amount * asset2Price
    if roundTo:
        return round(poolVal, roundTo)
    else:
        return poolVal

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
        poolVal = getPoolVal(
            amtColNow, d['priceCol'], amtAssNow, d['priceAss']
            )
        poolData[pair] = {
            'poolValue': round(poolVal, roundTo),
            'amtCol': round(amtColNow, roundTo),
            'amtAss': round(amtAssNow, roundTo)
            }

    return poolData

def appendToCsv(fileName, varList, varNames, verbose=True):
    '''
    Appends each value in varList as a new row to a file as specified in fileName.
    Creates new file with header if not found in working dir.

    Format of header:    id,time,[varNames]
    Example for row:     0,2021 Feb 18 16:24,0.03,72,NaN,Yes,...

    1st value: Successive id (=first value in last row of file + 1).
    2nd value: The current time in format "2021 Feb 18 17:34"
    If there is no file yet: Creates file with header = id, timestamp, [varNames]
    '''
#    import os
#    from datetime import datetime

    # Abort if number of variables and names don't add up.
    if len(varList) != len(varNames):
        import inspect, sys
        funcName = inspect.currentframe().f_code.co_name
        print('%s(): len(varNames) != len(varList)!' % funcName)

    else:
        # Get current time.
        timestamp = datetime.now()
        parsedTime = timestamp.strftime('%Y %b %d %H:%M')

        # Possibility: fileName doesn't exist yet. Create file with header and data.
        if not os.path.isfile(fileName):
            header = 'id,' + 'time,' + str(','.join(varNames))
            with open(fileName, 'a') as wfile:
                wfile.write(header)
                varList = [str(var) for var in varList]
                row = '\n' + '0' + ',' + parsedTime + ',' + str(','.join(varList))
                wfile.write(row)
            if verbose:
                print('''
                No file called "%s" has been found, so it has been created.
                Header: %s
                ''' % (fileName, header))
                print('Added new row to data: \t', row[1:])

        # Possibility: fileName exists. Only append new data.
        else:
            # Determine new id value based on most recent line of file.
            with open(fileName, 'r') as rfile:
                rows = rfile.readlines()
                try:
                    id_ = str(int(rows[-1].split(',')[0]) + 1)
                    # Write id, time, data to file.
                    with open(fileName, 'a') as wfile:
                        varList = [str(var) for var in varList]
                        row = '\n' + str(id_) + ',' + parsedTime + ',' + str(','.join(varList))
                        wfile.write(row)
                        if verbose:
                            print('Added new row to data: \t', row[1:])

                # Possibility: id can't be determined from file. Abort.
                except ValueError:
                    print('''
                    The last line of "%s" doesn't start with a valid id value (int).
                    Something is wrong with your data file.
                    No data has been written to the file.''' % fileName)

def updateCSV(dataDict, fileName, verbose=True):
    '''
    Appends current pool data from nested dict to csv file to keep track of
    asset ratios over time.
    '''
    outDf = pd.DataFrame(dataDict)

    for pair in outDf:
        name = pair
        varNames = outDf[pair].index.tolist()
        varNames.insert(0, 'pair')
        varList = outDf[pair].values.tolist()
        varList.insert(0, name)
        appendToCsv(fileName, varList, varNames, verbose=verbose)
