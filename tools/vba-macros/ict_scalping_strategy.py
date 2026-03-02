import os
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
import quandl
import backtrader as bt

# Set your API keys
ALPHA_VANTAGE_API_KEY = 'B2Q8P1OLW3Y2UD3X'
QUANDL_API_KEY = 'kj8FMwvc8ihTtCAfY9f4'

# Step 1: Fetch S&P 500 data from Alpha Vantage
def fetch_data_from_alpha_vantage():
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        data, _ = ts.get_daily(symbol='SPY', outputsize='full')
        data.dropna(inplace=True)
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        print("Data successfully fetched from Alpha Vantage")
        return data
    except Exception as e:
        print(f"Alpha Vantage Error: {e}")
        return None

# Step 2: Fetch S&P 500 data from Quandl as backup
def fetch_data_from_quandl():
    try:
        quandl.ApiConfig.api_key = QUANDL_API_KEY
        data = quandl.get("EOD/SPY", start_date="2020-01-01", end_date="2025-01-01")
        data.dropna(inplace=True)
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        print("Data successfully fetched from Quandl")
        return data
    except Exception as e:
        print(f"Quandl Error: {e}")
        return None

# Fetch the data from Alpha Vantage, fallback to Quandl if necessary
data = fetch_data_from_alpha_vantage()
if data is None:
    data = fetch_data_from_quandl()

# Ensure the data is a pandas DataFrame
if isinstance(data, pd.DataFrame):
    data.index = pd.to_datetime(data.index)
else:
    print("Error: No valid data retrieved from either Alpha Vantage or Quandl.")
    exit()

# Step 3: Convert the downloaded data to the format that Backtrader can understand
data_feed = bt.feeds.PandasData(dataname=data)

# Step 4: Define the ICT Scalping strategy with logging
class ICTScalping(bt.Strategy):
    params = (
        ("stop_loss", 0.02),  # 2% Stop loss
        ("take_profit", 0.04),  # 4% Take profit
    )

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)  # 20-period SMA

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def next(self):
        self.log(f'Close: {self.data.close[0]}')

        if not self.position and self.data.close[0] > self.sma[0]:
            self.buy(size=1)
            self.log(f'BUY executed at {self.data.close[0]}')

        elif self.position and self.data.close[0] < self.sma[0]:
            self.sell(size=1)
            self.log(f'SELL executed at {self.data.close[0]}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price}, Size: {order.executed.size}, Portfolio: {self.broker.getvalue()}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price}, Size: {order.executed.size}, Portfolio: {self.broker.getvalue()}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'Trade Profit: {trade.pnl}, Net Profit: {trade.pnlcomm}')

    def stop(self):
        self.log(f'Final Portfolio Value: {self.broker.getvalue()}')

# Step 5: Create the Backtrader engine
cerebro = bt.Cerebro()
cerebro.addstrategy(ICTScalping)
cerebro.adddata(data_feed)
cerebro.broker.set_cash(100000)
cerebro.broker.setcommission(commission=0.001)

print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")
results = cerebro.run()
final_value = cerebro.broker.getvalue()
print(f"Final Portfolio Value: {final_value}")

if not pd.isna(final_value) and final_value > 0:
    cerebro.plot(style='candlestick')
else:
    print("Final portfolio value is NaN or zero, skipping plot.")
