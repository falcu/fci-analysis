import pandas as pd
import statsmodels.api as sm

MARKET = 'Merval'
IR = 'LEBAC'
FCIS = {
            'Class A':['1810 RVA', '1822 RVN', 'Alpha A', 'Axis A', 'Arpenta', 'Fima PB A', 'Gainvest', 'Pellegrini A',
                       'SBS A', 'Superfondo A', 'Premier A', 'Pionero'],
            'Class B':['Alpha B', 'Axis B', 'FBA B', 'Fima PB B', 'Pellegrini B', 'SBS B', 'Superfondo B', 'Premier B'],
        }

FROM_DATE = '2015-09-15'
FILE_NAME = 'FCIs Monthly.xlsx'

def _flatten(x):
    if isinstance(x, list):
        return [a for i in x for a in _flatten(i)]
    else:
        return [x]

def _allFCIs():

    return _flatten(list(FCIS.values()))

def get_returns(fromDate='2015-09-15', dropLastRow=True, prefix='Monthly', fileName=FILE_NAME):
    series = []
    filePath = _filePath( fileName )
    if prefix:
        fileName = lambda f : f+' - '+prefix
    else:
        fileName = lambda f: f
    marketDF = pd.read_excel(filePath, sheetname = fileName(MARKET))
    marketDF.set_index('Exchange Date', inplace=True, drop=False)
    marketFromDateDF = marketDF.loc[fromDate:]
    marketDateS = marketFromDateDF['Exchange Date']
    marketDateS.reset_index( drop=True, inplace=True)
    marketDateS.name='Date'
    series.append(marketDateS)
    marketCloseS = marketFromDateDF['Close']
    marketCloseS.reset_index(drop=True, inplace=True)
    marketCloseS.name = MARKET
    series.append(marketFromDateDF['Close'])
    for aFCI in _allFCIs():
        fciDF = pd.read_excel(filePath, sheetname = fileName(aFCI))
        fciDF.set_index('Date', inplace=True, drop=True)
        fciCloseS = fciDF.loc[fromDate:]['NAV']
        fciCloseS.reset_index(drop=True, inplace=True)
        fciCloseS.name = aFCI
        series.append(fciCloseS)

    pricesDF = pd.concat(series, axis=1, ignore_index=False)
    if dropLastRow:
        pricesDF = pricesDF[:-1]

    dates = pricesDF['Date'][1:].reset_index(drop=True)
    pricesDF.drop(['Date'], axis=1, inplace=True)

    zeroToTMinus1PricesDF = pricesDF[:-1].reset_index(drop=True)
    oneToTPricesDF = pricesDF[1:].reset_index(drop=True)
    fciReturnsDF = oneToTPricesDF.sub(zeroToTMinus1PricesDF).divide(zeroToTMinus1PricesDF)

    result = pd.concat([dates,fciReturnsDF], axis=1)
    result.set_index('Date', drop=False, inplace=True)
    #result.reset_index(drop=True, inplace=True)
    return result

def indicator_func(func, returnsDF, risk_free=0.025, reverse=False, compareFunc=None):
    result = {k:[] for k in FCIS}
    marketReturnsDF = returnsDF[MARKET]
    for k in FCIS:
        for aFCI in FCIS[k]:
            fciResult = _flatten([ aFCI,func(marketReturnsDF,returnsDF[aFCI],risk_free)])
            result[k].append(fciResult)

    for k in result:
        _sortResult(result[k],reverse=reverse,compareFunc=compareFunc)

    return result

def alpha_jensen(marketReturnsDF,fciReturnsDF, risk_free=0.025):
    marketName = marketReturnsDF.name
    fciName = fciReturnsDF.name
    marketReturnsDF = marketReturnsDF - risk_free
    marketReturnsDF.name = marketName
    fciReturnsDF = fciReturnsDF - risk_free
    fciReturnsDF.name = fciName
    model = sm.OLS(fciReturnsDF, sm.add_constant(marketReturnsDF)).fit()

    return [model.params[0],model.pvalues[0]]

def sharpe_ratio(marketReturnsDF,fciReturnsDF, risk_free=0.025):
    return (fciReturnsDF.mean() - risk_free.mean()) / fciReturnsDF.std()

def tracking_error(marketReturnsDF,fciReturnsDF, risk_free=0.025):
    return marketReturnsDF.mean() - fciReturnsDF.mean()

def treynor_ratio(marketReturnsDF,fciReturnsDF, risk_free=0.025):
    beta = (marketReturnsDF.cov(fciReturnsDF)) / marketReturnsDF.var()
    return (fciReturnsDF.mean() - risk_free.mean()) / beta

def _sortResult(result, reverse=False, compareFunc=None):
    compareFunc = compareFunc or (lambda pair : pair[1])
    result.sort(key=compareFunc, reverse=reverse)
    return result

def _absResult(result):
    return abs(result[1])

def _sortAlphaJensen(result):
    return result[2]

def risk_free(returnsDF,fromDate=FROM_DATE):
    irDF = pd.read_excel(_filePath(FILE_NAME), sheetname='{} - Monthly'.format(IR))
    irDF.set_index('Date', inplace=True, drop=True)
    irS = irDF.loc[fromDate:]['Yield']
    irS.reset_index(drop=True, inplace=True)
    irS = irS[:-1]
    irS.name = IR
    dates = returnsDF['Date']
    dates.reset_index(drop=True, inplace=True)
    dates.name = 'Date'
    irsFinal = pd.concat([dates,irS], axis=1)
    irsFinal.set_index('Date', inplace=True, drop=True)
    return irsFinal[IR]

def _filePath(*args):
    import os
    mainPath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(mainPath,*args)

#(Name of indicator, function)
FCI_ANALYSIS_FUNCS = [('Alpha Jensen',alpha_jensen,['FCI','Alpha','P Value'],False,_sortAlphaJensen),
                      ('Sharpe Ratio',sharpe_ratio,['FCI','Sharpe Ratio'],True,None),
                      ("Tracking Error",tracking_error,['FCI','Tracking Error'],False,_absResult),
                      ("Treynor Ratio",treynor_ratio,['FCI','Treynor Ratio'],True,None)]


def main():
    from prettytable import PrettyTable
    returnsDF = get_returns()
    riskFree = risk_free(returnsDF)
    for fciData in FCI_ANALYSIS_FUNCS:
        fciIndicatorName, fciFunc, fciColumns, fciReverseResult, fciCustomFuncSort = fciData
        fciResult = indicator_func(fciFunc,returnsDF,riskFree,fciReverseResult,fciCustomFuncSort)
        for fciClass in fciResult:
            t = PrettyTable(fciColumns)
            result = fciResult[fciClass]
            for pair in result:
                t.add_row(pair)
            print(fciIndicatorName+" - "+fciClass)
            print(t)
            print("--------------------------------------------------------")

if __name__ == '__main__':
    main()
