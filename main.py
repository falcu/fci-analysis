import pandas as pd
import statsmodels.api as sm

MARKET = 'Merval'
FCIS = ['1810 RVA', '1822 RVN', 'Alpha A', 'Alpha B', 'Axis A',
        'Axis B', 'Arpenta', 'FBA B', 'Fima PB A', 'Fima PB B',
        'Gainvest', 'Pellegrini A', 'Pellegrini B', 'SBS A', 'SBS B',
        'Superfondo A', 'Superfondo B']

def get_returns(fromDate='2015-09-15', dropLastRow=True, prefix='Monthly', fileName='FCIs Monthly.xlsx'):
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
    for aFCI in FCIS:
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
    result.set_index('Date', drop=True, inplace=True)
    return result

def alpha_jensen(returnsDF, risk_free=0.025):
    returnsDF = returnsDF.sub(risk_free)
    result = []
    for aFCI in FCIS:
        model = sm.OLS(returnsDF[aFCI], sm.add_constant(returnsDF['Merval'])).fit()
        result.append((aFCI,model.pvalues[0]))

    return _sortResult(result)

def sharpe_ratios(returnsDF, risk_free=0.025):
    def _sharpeRatio( fciReturn, riskFree):
        return (fciReturn.mean() - riskFree)/fciReturn.std()

    result = []
    for aFCI in FCIS:
        result.append((aFCI,_sharpeRatio(returnsDF[aFCI],risk_free)))

    return _sortResult(result, reverse=True)

def _sortResult(result, reverse=False):
    result.sort(key=lambda pair: pair[1], reverse=reverse)
    return result


def _filePath(*args):
    import os
    mainPath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(mainPath,*args)

def main():
    returnsDF = get_returns()
    print("Alpha Jensen")
    print(alpha_jensen(returnsDF))
    print("Sharpe Ratio")
    print(sharpe_ratios(returnsDF))
