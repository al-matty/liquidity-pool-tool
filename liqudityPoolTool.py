#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os, inspect, sys
from math import sqrt
import random
import pandas as pd
from time import sleep
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib.pyplot as plt


def plot_line(df, col_x, col_y):
    '''
    Quick labeled line plot of one dfCol vs. another.
    Assumes col_x and col_y column labels (str) of df.
    '''
    assert type(col_x) == str and type(col_y) == str, 'col_x and col_y must be strings, ya dummy...'
    plotDf = df.sort_values(by=col_x, inplace=False)
    plt.plot(plotDf[col_x].values, plotDf[col_y].values)
    plt.xlabel(col_x)
    plt.ylabel(col_y)
    plt.title('Line Plot of %s and %s' % (col_y, col_x))
    plt.show()

# Scrapes and returns price of 1 asset from coingecko
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

# Scrapes and returns market cap of 1 asset from coingecko
def getTokenMc(tokenStr):
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

# Returns 1 tuple of current pool allocation given initial asset amounts and current prices
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

# Takes pairs dict and updates it inplace. Calls getTokenPrice(), getTokenMc()
# TODO: Should call getTokenMetrics per token instead.
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
                tokenData = getTokenMetrics(tokenStr)

#                price = getTokenPrice(tokenStr)
#                mc = getTokenMc()
                
                price = tokenData('price')
                mc = tokenData('mc')
                rank = tokenData('rank')
                
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
    poolVal = (asset1Amount * asset1Price) + (asset2Amount * asset2Price)
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

# Cycles through all table rows of a website and returns [integer from] first [matching] row/cell
def findCell(tableRows, rowKw, cellKw=None, stripToInt=True):
    '''
    Assumes tableRows = bs.findAll('tr').
    Cycles through all table rows / cells of a website and returns a match
    
    If no cellKw set:    Returns 1st matching row. 
    If cellKw set:       Returns first matching cell within that row.
    If stripToInt:       Returns int (all numbers within that cell).
    
    Example:
                >>>findCell(tableRows, 'Price', '$')
                >>>575
    '''
    funcName = inspect.currentframe().f_code.co_name
    result = None

    for row in tableRows:
        
        # Possibility no cellKw: Return the first row containing rowKw
        if rowKw in row.get_text():
            result = str(row)
            
    # Possibility cellKw: Return the first cell containing cellKw
    if cellKw and result:
        sCell = [str(cell) for cell in row if cellKw in result][0]
        result = sCell
                
    # Possibility stripToInt: Extract integers and return int
    if stripToInt and result:
        try:
            n = int(''.join(filter(lambda i: i.isdigit(), result)))
            result = n
        except ValueError:
            print( \
            f'''
            {funcName}():
            There are no digits in the first row containing '{rowKw}' and
            its first cell containing '{cellKw}'.
            ''')

    # Possibility: No rows found matching rowKw
    if not result:
        print(f'{funcName}(): No rows found containing {rowKw}!')
    return result    

# Scrapes coingecko and returns dict of various token metrics for 1 asset (calls findCell() for mc rank)
def getTokenMetrics(tokenStr):
    '''
    Assumes a string matching an existing html child of 'coingecko.com/en/coins/', i.e. 'ethereum'.
    Returns a dict of current asset metrics as given on coingecko.com.
    '''
    
    # Get name of function for error messages (depends on inspect, sys)
    funcName = inspect.currentframe().f_code.co_name
    tokenDict = {}
    
    # Scrape coingecko content for given token
    url = 'https://www.coingecko.com/en/coins/' + tokenStr
    userAgent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)' + \
        ' Chrome/41.0.2228.0 Safari/537.36'
    req = urllib.request.Request(url, headers= {'User-Agent' : userAgent})
    html = urllib.request.urlopen(req)
    bs = BeautifulSoup(html.read(), 'html.parser')
    
    # Helper function: Removes any '$' and ',' from target string and converts to float
    def clean(string):
        # Abort if scraped metric is empty or None
        assert string not in {None, ''}, \
            f"""
            Coingecko seems to have restructured their website.
            One of the metrics couldn't be scraped. Check {funcName}().
            """
        return float(string.replace(',','').replace('$',''))
    
    # Load needed html tag result sets
    noWrapTags = bs.findAll('span', {'class': 'no-wrap'})  # list of html tags
    mt1Tags = bs.findAll('div', {'class': 'mt-1'}) 
    tableRows = bs.findAll('tr')

    # Extract metrics that need html tag key attribute or other special treatment
    try:
        manuallyScraped = ['priceBTC', 'mcBTC']
        tokenDict['priceBTC'] = float(noWrapTags[0].get('data-price-btc'))
        tokenDict['mcBTC'] = float(noWrapTags[1].get('data-price-btc'))
        tokenDict['circSupply'] = float(mt1Tags[6].get_text().split('/')[0].strip().replace(',',''))
        tokenDict['totalSupply'] = float(mt1Tags[6].get_text().split('/')[1].strip().replace(',',''))
        tokenDict['mcRank'] = findCell(tableRows, 'Rank', stripToInt=True)      
        
    # Possibility: str-to-float conversion failed because it got None as argument 
    except TypeError:
        print(f"""
            Coingecko seems to have restructured their website.
            One of these metrics couldn't be scraped:
            {manuallyScraped}
            Check {funcName}().
            """)
    
    # Extract all other metrics from text
    tokenDict['priceUSD'] = clean(noWrapTags[0].get_text())
    tokenDict['mcUSD'] = clean(noWrapTags[1].get_text())
    tokenDict['24hVol'] = clean(noWrapTags[2].get_text())
    tokenDict['24hLow'] = clean(noWrapTags[3].get_text())
    tokenDict['24hHigh'] = clean(noWrapTags[4].get_text())
    tokenDict['7dLow'] = clean(noWrapTags[10].get_text())
    tokenDict['7dHigh'] = clean(noWrapTags[11].get_text())
    tokenDict['ATH'] = clean(noWrapTags[12].get_text())
    tokenDict['ATL'] = clean(noWrapTags[12].get_text())
    tokenDict['symbol'] = noWrapTags[0].get('data-coin-symbol')    
    
    # Sleep max 2 seconds before function can be called again (= scrape in a nice way)
    sleep(random.random()*2)
    
    return tokenDict

# Appends a new row to csv as specified in fileName
def appendToCsv(fileName, varList, varNames, verbose=True):
    '''
    Appends each value in varList as a new row to a file as specified in fileName.
    Creates new file with header if not found in working dir.
    Aborts with error message if it would change shape[1] of csv (= number of vars per row).
    
    Format of header:    id,time,[varNames]
    Example for row:     0,2021 Feb 18 16:24,0.03,72,NaN,Yes,...
    
    1st value: Successive id (=first value in last row of file + 1).
    2nd value: The current time in format "2021 Feb 18 17:34"
    If there is no file yet: Creates file with header = id, timestamp, [varNames]
    '''

    # Get name of function for error messages (depends on inspect, sys)
    funcName = inspect.currentframe().f_code.co_name
    
    # Abort if number of variables and names don't add up.
    assert len(varList) == len(varNames), \
        f"{funcName}(): The number of variables and names to append to csv must be the same."
    
    # Abort if number of variables to append differs from number of elements in csv header.
    with open(fileName, 'r') as infile:
        header = infile.readlines()[0]
        n_header = len(header.split(','))
    assert len(varList) == n_header, \
        f"""
        {funcName}(): You're trying to append a row of {len(varList)} variables to csv.
        In the csv header there are only {n_header}. To be imported as pandas dataframe for analytics,
        the number of variables per row in the csv needs to stay consistent throughout all rows.
        """

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
                # Write id, time, data to file.
                id_ = str(int(rows[-1].split(',')[0]) + 1)
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

# Calls appendToCsv(). Values in dataDict per pair become veriables per row in csv
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


        
        
def updateBounds(data):
    boundsDict = data.copy()

def withinBounds(tokenStr):
    '''
    Returns True if token is within bounds as given in data dict.
    '''
    # loads historical min and max values per metric per token 
    price = 0
    lowerBound = 0
    upperBound = 0
    if price >= lowerBound <= upperBound:
        return True


