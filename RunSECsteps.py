#!/usr/bin/env python
# coding: utf-8

## Access and retrieve Company Level Financial data from SEC EDGAR system
##   M Boldin March-April 2023 
##   UPWORK job  for Rueben Reuben Vandeventer, Second Sight Data Science

## Produces CSV file 
##   filename == {symbol} + {”_”} + {reportingYear} + {”_”} + {analysisDate} + {”_FY}

##   Annual Financial Metrics
##   **analysisDate:** this is the date that this data pull was executed
##   **symbol:** the symbol of the equity in which data has been pulled
##   **reportingDate:** this is the date that the company posted these results
##   **reportingPeriod:** this is the date range to which the reported numbers represent
##   **reportingYear:** this is the quarter and year of the reporting period represented
##   **earningsFY:** this is total earnings posted for the reporting period defined.  Note this should be the raw earnings, not earnings per share.
##   **cummDepreciationFY:** accumulated depreciation is a running total of depreciation expense reported on the balance sheet.
##   **depreciationExpenseFY:** depreciation expense is reported on the income statement as any other normal business expense
##   **amortizationFY:** amortization is an accounting technique used to periodically lower the book value of a [loan](https://www.investopedia.com/terms/l/loan.asp) or an [intangible asset](https://www.investopedia.com/terms/i/intangibleasset.asp) over a set period of time.
##   **totalCapexFY:** a company's capital expenditures (CapEx) can also be found on the cash flow statement under the "Investing Activities" section. Capital expenditures can also be listed as "Property, Plant, and Equipment" (PP&E), which are both the same thing, just named differently.
##   **maintenanceCapexFY**:  money a company spends to restore assets to what they were before.
##   **operatingCashFlowFY**: cash that's generated from normal business operations or activities.
##   **freeCashFlowFY:** cash that a company generates from its normal business operations before interest payments and after subtracting any money spent on capital expenditures. Capital expenditures, or CAPEX for short, are purchases of long-term fixed assets, such as property, plant, and equipment.
##   **sharesOutstandingFY:** Shares outstanding refer to a company's stock currently held by all its shareholders, including share blocks held by institutional investors and restricted shares owned by the company’s officers and insiders. Outstanding shares are shown on a company’s balance sheet under the heading “Capital Stock.”Needs secpy module  https://github.com/McKalvan/secpy
##      use pip install sec-python
##
##   DO NOT USE  pip install secpy  (different package)
##
##   also sec-python fails with Python 3.11
##   "AttributeError: module 'asyncio' has no attribute 'coroutine'." in Py…
##   Generator-based Coroutines which contains @asyncio.coroutine decorator is removed in Python 3.11

## IMPORT Python modules 
##  M Boldin APRIL-MAY 2023

import os
import sys
import datetime as dt
import numpy as np
import pandas as pd

##  My extra code
import secpy as sec
from secpy.secpy_client import SECPyClient

from SecUtils import *
##  SecUtils.py can be in different directory 
##   use os.sys.path.append("./Util") to add location to Python system path 

pd.options.mode.chained_assignment = None  # default='warn'
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)    

print('** MODULE IMPORTs Done **', dt.datetime.now()) 
print('Operating System:', sys.platform, '\n Python version:', sys.version)



## Need a SEC Edgar API user code

client = SECPyClient("MDBtest")
print(client.user_agent)


## Master function to call download steps and process data 
##  Uses SECitems.csv for defining variable terms and renaming

def RunSECsteps(tsymbol=None,last=1,form='10-K',items='SECitems.csv', make_csv=True):

    ## Use CSV file to define items
    dfSECitems = pd.read_csv('SECitems.csv')
    ## Renaming dictionary used below
    c1 = dfSECitems['ConceptNameFY'].to_list()
    c2 = dfSECitems['ItemFY'].to_list()
    drename = dict(zip(c1,c2))
 
    ## Identify Concept items and Calc items
    dfx = dfSECitems.copy()
    rx = dfx['type'] == 'calc'
    dfx2 = dfx[rx]
    concepts1 = dfx.loc[~rx,'ConceptNameFY']
    concepts1 = concepts1.to_list()
 

    ## Loop -- Get all needed Company Concept Items 
    company_facts = client.company_facts()
    company1 = company_facts.get_company_facts_for_ticker(tsymbol)
    #print(tsymbol, company1.cik, company1.entity_name)
    clist = concepts1[:]
    dfB1 = ConceptLoop2(tsymbol,company1,clist,form='10-K',last=last)

    ## Restate to item names
    dfB2 = RestateSEC(tsymbol,dfB1)

    ## PIVOT  make concept-name individual column names
    dfa = dfB2.copy()
    jx = ['analysisDate', 'symbol', 'reportingDate', 'reportingPeriod', 'reportingYear', 'endDate']
    dfa['case'] = dfa['concept_name']
    dfb = dfa.pivot_table(values = 'value', index=jx, columns = 'case')
    dfb.reset_index(inplace=True)
    dfb.columns = dfb.columns.to_flat_index()
    dfB3 = dfb.copy()

    ## List of extracted items used to see what is missing 
    ca = dfB3.columns
    #print(ca)
    #print(dfB3.tail(2).T)

    ## Make Depreciation CapEx and FCF and AccumDeprec
    dfB3['AccumDepreciation'] = 0
    dfB3['Amortization'] = 0
    dfB3['CapitalExpenditures']  = 0
    dfB3['FreeCashFlow']  = 0


    ##Net PPE lag and change
    if 'PropertyPlantAndEquipmentNet' in ca:
        dfB3['NetPPE_lag'] = dfB3['PropertyPlantAndEquipmentNet'].shift(1)
        dfB3['NetPPE_chg'] = dfB3['PropertyPlantAndEquipmentNet'] - dfB3['NetPPE_lag']
    if 'PropertyPlantAndEquipmentAdditions' in ca:
        dfB3['CapitalExpenditures'] = dfB3['PropertyPlantAndEquipmentAdditions']
    else:
        net = 0; dep = 0; psale=0;
        if 'NetPPE_chg' in dfB3.columns:
            net = dfB3['NetPPE_chg']
        if 'Depreciation' in dfB3.columns:
            dep = dfB3['Depreciation']
        elif 'DepreciationAndAmortization' in dfB3.columns:
            dep = dfB3['DepreciationAndAmortization']
        if 'ProceedsFromSaleOfPropertyPlantAndEquipment' in dfB3.columns:
            psale = dfB3['ProceedsFromSaleOfPropertyPlantAndEquipment'] 
        dfB3['CapitalExpenditures'] = net  + dep + psale

    if 'NetCashProvidedByUsedInOperatingActivities'	 in ca:
        dfB3['FreeCashFlow'] = dfB3['NetCashProvidedByUsedInOperatingActivities'] -  dfB3['CapitalExpenditures'] 
    #if 'NetCashProvidedByUsedInOperatingActivities'	 in ca:

    if 'AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment' in ca:
        dfB3['AccumDepreciation'] = dfB3['AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment']
    elif ('PropertyPlantAndEquipmentNet' in ca) and ('PropertyPlantAndEquipmentGross' in ca):
        dfB3['AccumDepreciation'] = dfB3['PropertyPlantAndEquipmentGross'] - dfB3['PropertyPlantAndEquipmentNet'];

    if 'AmortizationOfIntangibleAssets' in ca:
        dfB3['Amortization'] = dfB3['AmortizationOfIntangibleAssets']
    elif ('Depreciation' in dfB3.columns) and ('DepreciationAndAmortization' in dfB3.columns):
        dfB3['Amortization'] = dfB3['DepreciationAndAmortization'] - dfB3['Depreciation']

    if 'Depreciation' not in ca:
        dfB3['Depreciation'] = 0
        
    ## Rename SEC concept_name to Item FY tag 
    ##   rename dictionary defined above
    c1 = dfB3.columns
    c2 = list(c1)
    for k,c in enumerate(c1):
        #print(k, c)    
        if (c in drename.keys()) and  (drename[c] != 'extra'): 
            #print(k, c, drename[c])
            c2[k] = drename[c]
    dfB4 = dfB3.copy()
    dfB4[c2] = dfB4[c1]

    ## Re-oder and finish
    
    ca = ['analysisDate', 'symbol', 'reportingDate', 'reportingPeriod','reportingYear', 'endDate']
    
    cb = ['earningsFY',
    'cummDepreciationFY',
    'depreciationExpenseFY',
    'amortizationFY',
    'totalCapexFY',
    'operatingCashFlowFY',
    'freeCashFlowFY']
    if 'sharesOutstandingFY' in dfB4.columns: 
        cb.append('sharesOutstandingFY')

    k = dfB4.shape[0]
    if last==1:
        dfB5 = dfB4.loc[k-1:,ca+cb]
    else:
        dfB5 = dfB4.loc[k-last:k,ca+cb]    
        
    if make_csv == True:
        x=dfB5.iloc[-1,:]
        symbol = x['symbol']
        reportingYear = x['reportingYear']
        analysisDate = x['analysisDate']
        filename = f'{symbol}_{reportingYear}_{analysisDate}_FY.csv'
        print('Creating:', filename)
        dfB5.to_csv(filename)
        
    return dfB5


## Example extract

Msft = RunSECsteps('MSFT',last=2, form='10-K')
print(Msft.T)




