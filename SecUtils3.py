## SEC download utils
##   M Boldin (mdboldin@gmail.com)  Apr May June July 2023
##      7/1/2023 edited
## SEC download utils

import os
import datetime as dt
import numpy as np
import pandas as pd

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)    
pd.options.mode.chained_assignment = None  # default='warn'

import secpy as sec
from secpy.secpy_client import SECPyClient
client = SECPyClient("MDBtest")

###################################

def DFjoin(dfa,dfb,on=None, reset_index=True):
    df2 = dfa.set_index(on).join(dfb.set_index(on),rsuffix='_b')
    if reset_index:
        df2.reset_index(inplace=True)
    return df2

def DFappend(dfa, dfb):
    ## Simple  DF append to add rows from dfa and dfb, ignores index
    ##    uses default axis = 0
    #     similar to dfA = dfa.append(dfb) that was removed
    dfA = pd.concat([dfa, dfb], ignore_index=True)
    return dfA


#############################################

def FillDates(dfa,dfb):
    
    dfb2 = dfb.copy()
    
    a = dfa.groupby(['fiscal_year','start'])
    b1 = a['value'].count()
    b1.sort_index(inplace=True)
    b1 = b1.reset_index()
    b1 = b1.groupby(['fiscal_year'])
    b1 = b1.last()

    a = dfa.groupby(['fiscal_year','end'])
    b2 = a['value'].count()
    b2.sort_index(inplace=True)
    b2 = b2.reset_index()
    b2 = b2.groupby(['fiscal_year'])
    b2 = b2.last()

    a = dfa.groupby(['fiscal_year','filed'])
    b3 = a['value'].count()
    b3.sort_index(inplace=True)
    b3 = b3.reset_index()
    b3= b3.groupby(['fiscal_year'])
    b3 = b3.last()

    ##Add to DataFrame dates
    xdate1, xdate2, xdate2 = None, None, None
    ryears = set(dfb2['reportingYear'])
    for y in ryears:
        rx = dfb2['reportingYear']==y
        xdate1 = b1.loc[y,'start']
        xdate2 = b2.loc[y,'end']
        xdate3 = b3.loc[y,'filed']
        y,sum(rx),xdate1,xdate2,xdate3
        dfb2.loc[rx,'startDate'] = xdate1 
        dfb2.loc[rx,'endDate'] = xdate2 
        dfb2.loc[rx,'reportingDate'] = xdate3 

    return dfb2

def RestateSEC(symbol,dfb):
    today = dt.datetime.today()
    analysisDate = today.strftime('%Y-%m-%d')
    reportingDate = 0
    reportingPeriod = 0
    #reportingYear = 2022
    dfb['analysisDate'] = analysisDate
    dfb['symbol'] = symbol
    dfb['reportingDate'] =  dfb['filed']
    dfb['reportingPeriod'] = dfb['fiscal_period']
    dfb['reportingYear'] = dfb['fiscal_year']
    dfb['startDate'] = dfb['start']
    dfb['endDate'] = dfb['end']

    return dfb


    
def GetConceptData(tsymbol, concept, company=False, taxonomy='us_gaap', units='USD'):
        if not company:
            company_facts = client.company_facts()
            company = company_facts.get_company_facts_for_ticker(tsymbol)
        cik = company.cik
        info1 = company.get_concept(taxonomy=taxonomy, concept=concept)
        #info1.label,  info1.description
        ux = info1.list_units()
        if units not in ux:
            pass
            units = ux[0]

        a = info1.get_unit(units)
        b = []
        for k, x in enumerate(a,1):
            v1 = x.value
            row = (k, tsymbol, cik, x.concept_name, units, v1, 
                   x.form, x.frame, x.start, x.end, x.fiscal_year, x.fiscal_period, x.filed)    
            #print(row)
            b.append(row)
        cx = ['rown', 'tsymbol', 'CIK', 'concept_name', 'units', 'value', 
              'form', 'frame', 'start', 'end', 'fiscal_year','fiscal_period','filed']
        dfa = pd.DataFrame(b, columns=cx)  
        return dfa

###### New set for ConceptLoop PickCases  RunSteps 7/1/2023

def ConceptLoop(symbol, company, clist, form='10-K', last=1):
    
    #print('Using New ConceptLoop')
    
    dfb = pd.DataFrame()
    dfB = pd.DataFrame()
    company_name =  company.entity_name
    #print(symbol, form, last, company_name,'\n',clist)
    for c in clist:
        ##print(company_name,c)
        #if 1:
        try:
            dfa = GetConceptData(symbol, concept=c, company=company)
        except:
            pass
            dfa=pd.DataFrame()
            ##print('Failed to get', symbol, c)
    
        dfb=[]
        if form == '10-K':
            if len(dfa):
                dfb = PickFYAnnualCases(dfa, form=form, last=last+1)
                if len(dfb):
                    dfB = DFappend(dfB, dfb)
        elif form == '10-Q':
            if len(dfa):
                dfb = PickQuarterlyCases(dfa, form=form, last=last+1)
                if len(dfb):
                    dfB = DFappend(dfB, dfb)
                    
        ##print(c, ':', len(dfb), 'rows added for dfB shape', dfB.shape)
    
    return dfB


def PickFYAnnualCases(dfa, form='10-K', last=False, after=None):
    
    #print('Using New PickFYAnnualCases')

    vx = 'rown form frame fiscal_year fiscal_period value filed  start end concept_name'.split()
    #print('Using PICKCASES v3x2',set(dfa['concept_name']), len(dfa), 'intial rows')
    #print(dfa[vx].tail(20))

    ##print()
    ##print(40*'*')
    
    ## Will need to check end-start days > 330 (or < 100)
    date1, date2 = 'start', 'end'
    dfa['date1'] = pd.to_datetime(dfa[date1])
    dfa['date2'] = pd.to_datetime(dfa[date2])
    dfa['date_diff'] = (dfa['date2']-dfa['date1'])
    def getDays(d):
        days = d.days
        return days
    dfa['days'] = dfa['date_diff'].apply(lambda x: getDays(x))
    
    ## Screen for 10-K or 10-Q
    if form == '10-K':
        dfb1 = dfa.query("form == '%s'" % form)
        rx = (dfb1['frame'].str[6] == 'Q')
        dfb1 = dfb1[rx==False]
        rx =  dfb1['days'] < 330 
        dfb1 = dfb1[rx==False] 
        sortby = ['fiscal_year', 'filed', 'rown']
        dfb1.sort_values(sortby, ascending=True, inplace=True)
        
        ## More FY screening needed? first check if pruning needed
        ##   Screen if more than 1 row for FY, fiscal_year value may not right
        ##   Best prune: for each FY, pick if frame = 'CYyear' 
        ##    or use last filed
        n = len(dfb1)
        fyears = dfb1['fiscal_year'].to_list()
        fyears = list(set(fyears))
        fyears.sort()
        fycount = len(fyears) ## count of unique cases
        ##print(n,fycount,fycount < n,fyears)
        ##print('*1');#print(dfb1[vx[:7]])
        dfb2 = pd.DataFrame()
        if not (fycount < n):
            ## Use all rows
            dfb2 = dfb1.copy()
        else:
            ## Prune rows, more than 1 row per fyear
            for fy in fyears:
                rx = dfb1['fiscal_year'] == fy
                dfx2 = dfb1[rx]
                if sum(rx) == 1:
                    dfb2 = DFappend(dfb2,dfx2)
                elif sum(rx) > 1:
                    rx2a = (dfx2['frame'] == 'CY'+str(fy))
                    rx2b = (dfx2['value'] != None)
                    if sum(rx2a)==1:
                        dfb2 = DFappend(dfb2,dfx2[rx2a])
                    elif sum(rx2b)==1:
                        dfb2 = DFappend(dfb2,dfx2[rx2b])
                    else: ## Pick last one
                        dfx2 = dfx2.iloc[-1:,:]
                        dfb2 = DFappend(dfb2,dfx2)
                else:
                    ## No rows for fy
                    pass 
                
                cx = set(dfx2['concept_name'])
                #print('PickCases3x ', cx, form, fy, len(dfx2), len(dfb2))
                ##print('***');#print(dfb1[vx[:7]])
                #print(' -- ', len(dfa), 'rows, initially screened to', sum(rx), len(dfb1), 'rows')
                #print(' -- final screen to:', len(dfx2), 'combined set:', len(dfb2),'rows', end='') 
                #print(' -----  upto', max(dfb2['fiscal_year']), 'for', concept)
            ##print(dfb2[vx[:6]])
            ##print()   
            
        dfb = dfb2.copy()
        sortby = ['fiscal_year', 'filed', 'rown']
        dfb.sort_values(sortby, ascending=True, inplace=True)
        #print('Done', fy, len(dfb2))
    
    return dfb
    
def PickQuarterlyCases(dfa, form='10-Q', last=False, after=None):
    print('Quarterly version', form, 'not ready')
    
    return None



## Complete steps
def RunSECsteps(tsymbol=None, last=1, form='10-K', 
                  items='SECitems.csv', make_csv=True, output=1):
    
    ## Master function to call download steps and process data 
    ##  Uses SECitems.csv for defining variable terms and renaming

    #print('Using RunSECsteps5 for',tsymbol)

    ## Load CSV file to define items
    dfSECitems = pd.read_csv('SECitems.csv')
    ## Renaming dictionary used below
    c1 = dfSECitems['ConceptNameFY'].to_list()
    c2 = dfSECitems['ItemFY'].to_list()
    drename = dict(zip(c1,c2))

    ## Identify Direct match to Concept items, (vs Calc item)
    ##   concepts1 list will have non calcs in SecItems set 
    ##   should be ['Assets','Revenues',
    ##     'NetIncomeLoss','Depreciation',
    ##     'NetCashProvidedByUsedInOperatingActivities', 'CommonStockSharesOutstanding',
    ##     'OperatingIncomeLoss', 'DepreciationAndAmortization', 'PropertyPlantAndEquipmentGross', 'PropertyPlantAndEquipmentNet',
    ##     'PropertyPlantAndEquipmentAdditions','ProceedsFromSaleOfPropertyPlantAndEquipment',
    ##     'AmortizationOfIntangibleAssets','AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment']
    dfx = dfSECitems.copy()
    rx = dfx['type'] == 'calc'
    dfx2 = dfx[rx]
    concepts1 = dfx.loc[~rx,'ConceptNameFY']
    concepts1 = concepts1.to_list()
    
    ## Loop -- Get all needed Company Concept Items 
    company_facts = client.company_facts()
    company1 = company_facts.get_company_facts_for_ticker(tsymbol)
    #print(tsymbol, company1.cik, company1.entity_name)
    
    ## Loop over needed SEC items, ConceptLoop3x() includes PickCases
    dfB1 = ConceptLoop(tsymbol,company1,concepts1,form=form,last=last)
    
    ## Restate to item names
    dfB2 = RestateSEC(tsymbol,dfB1)
    
    ## PIVOT  make concept-name individual column names
    dfa = dfB2.copy()
    jx = ['analysisDate', 'symbol', 'reportingPeriod', 'reportingYear']
    dfa['case'] = dfa['concept_name']
    dfb = dfa.pivot_table(values = 'value', index=jx, columns = 'case')
    dfb.reset_index(inplace=True)
    dfb.columns = dfb.columns.to_flat_index()
    dfB3a = dfb.copy()
    
    ## Fill in dates - start end filed --> reportingDate, startDate, endDate
    dfB3 = FillDates(dfB2,dfB3a)

    ## List of extracted items used to see what is missing 
    ca = dfB3.columns

    ## Make Depreciation, CapEx, Free Cash Flow and AccumDeprec
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
    
    ## Use either WeightedAverageNumberOfSharesOutstandingBasic or
    ##   CommonStockSharesOutstanding for sharesOutstandingFY
    if  'WeightedAverageNumberOfSharesOutstandingBasic' in dfB3.columns:
        print('Found WeightedAverageNumberOfSharesOutstandingBasic for sharesOutstanding')
        dfB3['shares'] = dfB3['WeightedAverageNumberOfSharesOutstandingBasic']
    elif 'CommonStockSharesOutstanding' not in dfB3.columns:   
        print('Using CommonStockSharesOutstanding for sharesOutstanding')
        dfB3['shares'] = dfB3['CommonStockSharesOutstanding']
        
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
    
    ## Add missing items as all missing values -- Nan
    a = ['analysisDate', 'symbol', 'reportingDate', 'reportingPeriod',
       'reportingYear', 'endDate', 'earningsFY', 'cummDepreciationFY',
       'depreciationExpenseFY', 'amortizationFY', 'totalCapexFY',
       'operatingCashFlowFY', 'freeCashFlowFY', 'sharesOutstandingFY']
    b = list(dfB4.columns)
    
    adds = [ c for c in a if c not in b]
    if len(adds):
        print('Missing items:',adds)
        for c in adds:
            dfB4[c] = np.float64(None)
    else:
        pass
        #print('All items',b)
    
    ## Re-order and finish
    ca = ['analysisDate', 'symbol', 
          'reportingDate', 'reportingPeriod','reportingYear', 'startDate', 'endDate']
    cb = ['earningsFY',    'cummDepreciationFY', 'depreciationExpenseFY', 'amortizationFY',
            'totalCapexFY','operatingCashFlowFY','freeCashFlowFY']
    ## sharesOutstanding check, may not be an available  download item
    if 'sharesOutstandingFY' in dfB4.columns: 
        cb.append('sharesOutstandingFY')
        
    k = dfB4.shape[0]
    if last==1:
        dfB5 = dfB4.loc[k-1:,ca+cb]
    else:
        dfB5 = dfB4.loc[k-last:k,ca+cb]    

    if make_csv == True:
        vx = ['analysisDate', 'symbol', 'reportingDate', 'reportingPeriod',
       'reportingYear', 'startDate', 'endDate', 'earningsFY', 'cummDepreciationFY',
       'depreciationExpenseFY', 'amortizationFY', 'totalCapexFY',
       'operatingCashFlowFY', 'freeCashFlowFY', 'sharesOutstandingFY']
        x=dfB5.iloc[-1,:]
        symbol = x['symbol']
        reportingYear = x['reportingYear']
        analysisDate = x['analysisDate']
        filename = f'{symbol}_{reportingYear}_{analysisDate}_FY.csv'
        print('Creating:', filename)
        dfX = dfB5[vx]
        dfX.to_csv(filename)
        #print(dfX)
    
    ## Return only the final DataFrame set, same as CSV file design 
    ##   or also preliminary sets in a tuple
    ## dfB1 from SEC download no renaming, TSYMBOL FISCAL_YEAR FY_PERIOD FILED VALUE + more
    if output==1:
        return dfB5
    elif output==2:
        return (dfB1,dfB5)
    elif output==3:
        return (dfB1,dfB2,dfB3,dfB4,dfB5)
    elif output==0:
        return None    
    
    