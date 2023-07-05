## SEC download utils
##   M Boldin (mdboldin@gmail.com)  Apr May 2023

import os
import datetime as dt
import numpy as np
import pandas as pd

import secpy as sec
from secpy.secpy_client import SECPyClient
#client = SECPyClient("MDBtest")

###################################

def DfJoin(dfa,dfb,on=None, reset_index=True):
    df2 = dfa.set_index(on).join(dfb.set_index(on),rsuffix='_b')
    if reset_index:
        df2.reset_index(inplace=True)
    return df2

#############################################

def GetContent1(CIK=None, tsymbol=None, concept=None,
             ftype='FY', units = 'USD'):    
    company_facts = client.company_facts()
    if CIK:
        info = company_facts.get_company_facts_for_cik(CIK)
        symbol = "XXXX"
    else:
        info = company_facts.get_company_facts_for_ticker(tsymbol)
        CIK = info.cik
    #print(symbol,info.cik,info.entity_name,concept,ftype)
    taxonomy="us_gaap"
    concept_info = info.get_concept(taxonomy=taxonomy, concept=concept)
    columns = 'k CIK symbol concept_name frame fiscal_year fiscal_period filed end value'.split()
    dfA = pd.DataFrame(columns = columns)
    n = dfA.shape[0]
    for k in range(n):
        a = concept_info.get_unit(units)[k]
        if a.fiscal_period == ftype:
            x = [k, CIK, tsymbol, a.concept_name, a.frame, a.fiscal_year, a.fiscal_period, a.filed, a.end, a.value]
            dfx = pd.DataFrame(columns = columns)
            dfx.loc[0,columns] = x
            dfA = dfA.append(dfx)    
            #print(dfx)
    #keep lastest        
    sortby = ['CIK', 'end', 'filed', 'k']
    dfA.sort_values(sortby, ascending=False, inplace=True)
    return dfA


def GetConceptData1(tsymbol, concept, taxonomy='us_gaap', units='USD'):
        company_facts = client.company_facts()
        company1 = company_facts.get_company_facts_for_ticker(tsymbol)
        cik = company1.cik
        info1 = company1.get_concept(taxonomy=taxonomy, concept=concept)
        #info1.label,  info1.description
        ux = info1.list_units()
        if units not in ux:
            pass
            units = ux[0]

        a = info1.get_unit(units)
        b = []
        for k, x in enumerate(a,1):
            v1 = x.value
            row = (k, tsymbol, cik, x.concept_name, units, v1, x.form, x.frame, x.end, x.fiscal_year, x.fiscal_period, x.filed)    
            #print(row)
            b.append(row)
        #cx = ['rown', 'tsymbol', 'CIK', 'concept_name', 'units', concept, 'form', 'frame', 'end', 'fiscal_year','fiscal_period','filed']
        cx = ['rown', 'tsymbol', 'CIK', 'concept_name', 'units', 'value', 'form', 'frame', 'end', 'fiscal_year','fiscal_period','filed']
        dfa = pd.DataFrame(b, columns=cx)  
        return dfa

    
def GetConceptData2(tsymbol, concept, company=False, taxonomy='us_gaap', units='USD'):
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
            row = (k, tsymbol, cik, x.concept_name, units, v1, x.form, x.frame, x.start, x.end, x.fiscal_year, x.fiscal_period, x.filed)    
            #print(row)
            b.append(row)
        cx = ['rown', 'tsymbol', 'CIK', 'concept_name', 'units', 'value', 'form', 'frame', 'start', 'end', 'fiscal_year','fiscal_period','filed']
        dfa = pd.DataFrame(b, columns=cx)  
        return dfa

    
def PickCases2(dfa, form='10-K', last=False, after=None):
        # Screen for `10-K or 10-Q
        dfb1 = dfa.query("form == '%s'" % form)
        #print( dfa.shape, dfb1.shape )
        #Keep latest filed or most recent  only        
        sortby = ['fiscal_year', 'end', 'filed', 'rown']
        dfb1.sort_values(sortby, ascending=True, inplace=True)
        dfGroup = dfb1.groupby('end')
        dfb2 = dfGroup.first()
        dfb2.reset_index(inplace=True)
        #print( dfa.shape, dfb1.shape, dfb2.shape )
        if isinstance(last,bool) and last==True:
            last = 1
        if isinstance(last,int) and last > 0:
            m = dfb2.shape[0]
            dfb3 = dfb2.loc[m-last:m,:]
            return dfb3
        else:
            return dfb2       
        
        
def ConceptLoop2(symbol, company, clist, form='10-K', last=1):
    dfB = []
    company_name =  company.entity_name
    #print(clist)
    for c in clist:
        #print(company_name,c)
        try:
            dfa = GetConceptData2(symbol, concept=c, company=company)
            dfb = PickCases2(dfa, form=form, last=last+1)
            #print(dfb.head())
            if not len(dfB):
                dfB = pd.DataFrame(dfb)
            else:
                dfB = dfB.append(dfb)
                #print( dfB.shape)
        except:
            pass
    return dfB

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

