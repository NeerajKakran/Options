# import kiteapp as kt
import pandas as pd
# import talib
import os
import requests
import pandas_ta as ta
from datetime import datetime, timedelta

from kiteconnect import KiteConnect

with open(r'D:\zerodha_data\access token.txt', 'r') as wr:
    token = wr.read()
    
api_key = 'g0inasdoj9nit657'
kite = KiteConnect(api_key=api_key)
access_token=token
kite.set_access_token(access_token)

# # Reading Encrypted token
# with open(r'D:\zerodha_data\enctoken.txt', 'r') as wr:
#     token = wr.read()

# # Setting kite session
# kite = kt.KiteApp("Aabr", "ZZ1010", token) # ZZ1010 / ZV1592

url = 'https://api.telegram.org/bot6836700490:AAESEKKQmE_15H8vtLFHYLaDzZ5vfBvmyFM/sendMessage?chat_id=-4188870599&text="{}"'

to_date = datetime.now().date()
days = timedelta(days=4)
from_date = (to_date - days)
to_date = (to_date)
back_date = (to_date - timedelta(days=1))
year = to_date.strftime('%Y')
month_name = to_date.strftime('%b')

scrips = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
NSE_name = ['NIFTY 50', 'NIFTY BANK', 'NIFTY FIN SERVICE']

current_time = datetime.now()
rounded_time = (current_time - timedelta(minutes=current_time.minute % 5, seconds=current_time.second, microseconds=current_time.microsecond)).strftime('%H:%M')


instrument_dump = kite.instruments("NFO")
instrument_df = pd.DataFrame(instrument_dump)

NSE = pd.DataFrame(kite.instruments('NSE'))

msg_nifty =[]
msg_banknifty =[]
msg_finnifty =[]

order_type = []
ins = []
strike = []
opt_type = []
time = []
price = []
band = []
outcum = []
 
# prev_df = pd.read_csv(r'D:\Data-with-Indicators\options_trigger\2024\Mar\option_triggers_{0}.csv'.format(to_date))

directory = r'D:\Data-with-Indicators\options_trigger\{}\{}'.format(year, month_name)
file_path = os.path.join(directory, 'option_triggers_{0}.csv'.format(to_date))

if not os.path.exists(directory):
    os.makedirs(directory)

if not os.path.exists(file_path):
    prev_df = pd.DataFrame({'Order Type': order_type, 'Instrument': ins, 'Strike': strike, 'Option Type': opt_type, 'Time': time, 'Price': price, 'Band': band, 'Outcome': outcum})
    prev_df.to_csv(file_path, index=False)
else:
    prev_df = pd.read_csv(file_path)


for scrip, name in zip(scrips, NSE_name):
    filtered_df = instrument_df[(instrument_df['name'].str.fullmatch(scrip, case=False)) & (instrument_df['segment'] ==  'NFO-OPT')]
    min_expiry = filtered_df['expiry'].min()
    filtered_df = filtered_df[(filtered_df['expiry'] ==  min_expiry)]
    
    if len(filtered_df) > 0:
        inst_list = filtered_df['tradingsymbol'].tolist()
        inst_token = NSE[NSE['tradingsymbol']==name]['instrument_token'].values[0]
        df_day = pd.DataFrame(kite.historical_data(inst_token, from_date, to_date, 'day'))
        
        last_close = df_day['close'].iloc[-1]
        mid_strike = round(last_close/100)*100
        strike_list = [mid_strike-500, mid_strike-400, mid_strike-300, mid_strike-200, mid_strike-100, mid_strike, mid_strike+100, mid_strike+200, mid_strike+300, mid_strike+400, mid_strike+500]
        instruments = [inst for strike in strike_list for inst in inst_list if str(strike) in inst[-7:]]
        
        for inst in instruments:
            inst_token = filtered_df[filtered_df['tradingsymbol']==inst]['instrument_token'].values[0]
            df = pd.DataFrame(kite.historical_data(inst_token, from_date, to_date, '5minute', oi=True))
            if len(df) > 0:
                df.rename(columns = {'date':'datetime'}, inplace = True)
                df['datetime'] = df['datetime'].dt.tz_localize(None)
                bins_close = [0, 25, 50, 100, 200, 300, 400, 500, 1000000]
                labels_close = ['0-25', '25-50', '50-100', '100-200', '200-300', '300-400', '400-500', '>500']
                df['Close_Group'] = pd.cut(df['close'], bins=bins_close, labels=labels_close, include_lowest=True)
                df['instrument'] = inst
                df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                df['time'] = pd.to_datetime(df['datetime']).dt.strftime('%H:%M')
                df['symbol'] = df['instrument'].str.extract(r'^([A-Za-z]+)')
                df['option_type'] = df['instrument'].str[-2:]
                df['strike_price'] = df['instrument'].str[-7:-2].astype('int')
                df['expiry_date'] = min_expiry
                # df['EMA_8'] = talib.EMA(df['close'], timeperiod=8)
                df['EMA_8'] = ta.ema(df['close'], length=8)
                # df['EMA_20'] = talib.EMA(df['close'], timeperiod=20)
                df['EMA_20'] = ta.ema(df['close'], length=20)
                df.set_index('datetime', inplace=True)
                df['VWAP'] = round(ta.vwap(high=df['high'], low=df['low'], close=df['close'], volume=df['volume']), 2)
                df.reset_index(inplace=True)
            
                df1 = df.tail(1).copy().reset_index(drop=True)
                prev_dff = prev_df[(prev_df['Instrument']==df1['symbol'][0]) & (prev_df['Strike'] == df1['strike_price'][0]) & 
                                   (prev_df['Option Type'] == df1['option_type'][0])].reset_index(drop=True)[-1:]
                if (df1['close'][0] > df1['EMA_8'][0]) & (df1['close'][0] > df1['EMA_20'][0]) & (df1['EMA_8'][0] > df1['EMA_20'][0]) & (df1['close'][0] > df1['VWAP'][0]):
                    text = 'Buy' + ' ' + df1['symbol'][0] + ' ' + str(df1['strike_price'][0]) + df1['option_type'][0] + ' at "' + str(df1['close'][0]) + '" -- ' + df1['time'][0]
                    t = 'Buy'
                    order_type.append('Buy')
                    ins.append(df1['symbol'][0])
                    strike.append(df1['strike_price'][0])
                    opt_type.append(df1['option_type'][0])
                    time.append(df1['time'][0])
                    price.append(df1['close'][0])
                    band.append(df1['Close_Group'][0])
                    if df1['option_type'][0] == 'CE':
                        outcum.append('Up')
                    elif df1['option_type'][0] == 'PE':
                        outcum.append('Down')
                        
                    if len(prev_dff) > 0:
                        if prev_dff['Order Type'].values[0] != t:
                            if scrip == 'NIFTY':
                                msg_nifty.append(text)
                            elif scrip == 'BANKNIFTY':
                                msg_banknifty.append(text)
                            elif scrip == 'FINNIFTY':
                                msg_finnifty.append(text)
                    else:
                        if scrip == 'NIFTY':
                            msg_nifty.append(text)
                        elif scrip == 'BANKNIFTY':
                            msg_banknifty.append(text)
                        elif scrip == 'FINNIFTY':
                            msg_finnifty.append(text)
                elif (df1['close'][0] < df1['EMA_8'][0]) & (df1['close'][0] < df1['EMA_20'][0]) & (df1['EMA_8'][0] < df1['EMA_20'][0]) & (df1['close'][0] < df1['VWAP'][0]):
                    text = 'Sell' + ' ' + df1['symbol'][0] + ' ' + str(df1['strike_price'][0]) + df1['option_type'][0] + ' at "' + str(df1['close'][0]) + '" -- ' + df1['time'][0]
                    t = 'Sell'
                    order_type.append('Sell')
                    ins.append(df1['symbol'][0])
                    strike.append(df1['strike_price'][0])
                    opt_type.append(df1['option_type'][0])
                    time.append(df1['time'][0])
                    price.append(df1['close'][0])
                    band.append(df1['Close_Group'][0])
                    if df1['option_type'][0] == 'CE':
                        outcum.append('Down')
                    elif df1['option_type'][0] == 'PE':
                        outcum.append('Up')
                    
                    if len(prev_dff) > 0:
                        if prev_dff['Order Type'].values[0] != t:
                            if (scrip == 'NIFTY') & (df1['close'][0] > 10):
                                msg_nifty.append(text)
                            elif (scrip == 'BANKNIFTY') & (df1['close'][0] > 10):
                                msg_banknifty.append(text)
                            elif (scrip == 'FINNIFTY') & (df1['close'][0] > 10):
                                msg_finnifty.append(text)
                    else:
                        if (scrip == 'NIFTY') & (df1['close'][0] > 10):
                            msg_nifty.append(text)
                        elif (scrip == 'BANKNIFTY') & (df1['close'][0] > 10):
                            msg_banknifty.append(text)
                        elif (scrip == 'FINNIFTY') & (df1['close'][0] > 10):
                            msg_finnifty.append(text)
trigger_df = pd.DataFrame({'Order Type': order_type, 'Instrument': ins, 'Strike': strike, 'Option Type': opt_type, 'Time': time, 'Price': price, 'Band': band, 'Outcome': outcum})

nifty_up  = trigger_df[trigger_df['Instrument']=='NIFTY']['Outcome'].value_counts().get('Up', 0)
nifty_buy  = trigger_df[trigger_df['Instrument']=='NIFTY']['Order Type'].value_counts().get('Buy', 0)
nifty_down  = trigger_df[trigger_df['Instrument']=='NIFTY']['Outcome'].value_counts().get('Down', 0)
nifty_sell  = trigger_df[trigger_df['Instrument']=='NIFTY']['Order Type'].value_counts().get('Sell', 0)
nifty_net = nifty_up - nifty_down

banknifty_up  = trigger_df[trigger_df['Instrument']=='BANKNIFTY']['Outcome'].value_counts().get('Up', 0)
banknifty_buy  = trigger_df[trigger_df['Instrument']=='BANKNIFTY']['Order Type'].value_counts().get('Buy', 0)
banknifty_down  = trigger_df[trigger_df['Instrument']=='BANKNIFTY']['Outcome'].value_counts().get('Down', 0)
banknifty_sell  = trigger_df[trigger_df['Instrument']=='BANKNIFTY']['Order Type'].value_counts().get('Sell', 0)
banknifty_net = banknifty_up - banknifty_down

finnifty_up  = trigger_df[trigger_df['Instrument']=='FINNIFTY']['Outcome'].value_counts().get('Up', 0)
finnifty_buy  = trigger_df[trigger_df['Instrument']=='FINNIFTY']['Order Type'].value_counts().get('Buy', 0)
finnifty_down  = trigger_df[trigger_df['Instrument']=='FINNIFTY']['Outcome'].value_counts().get('Down', 0)
finnifty_sell  = trigger_df[trigger_df['Instrument']=='FINNIFTY']['Order Type'].value_counts().get('Sell', 0)
finnifty_net = finnifty_up - finnifty_down

time = trigger_df['Time'].max()

outcum_list = []
if nifty_net > 0:
    outcum_list.append('Nifty is ' + 'Up ' + '@ ' + str(rounded_time) + '. Net = ' + str(nifty_net) + '.  ' + str(nifty_up) + ' Up, ' + str(nifty_down) + ' Down Signals')
elif nifty_net < 0:
    outcum_list.append('Nifty is ' + 'Down ' + '@ ' + str(rounded_time) + '. Net = ' + str(nifty_net) + '.  ' + str(nifty_up) + ' Up, ' + str(nifty_down) + ' Down Signals')
if banknifty_net > 0:
    outcum_list.append('BankNifty is ' + 'Up ' + '@ ' + str(rounded_time) + '. Net = ' + str(banknifty_net) + '.  ' + str(banknifty_up) + ' Up, ' + str(banknifty_down) + ' Down Signals')
elif banknifty_net < 0:
    outcum_list.append('BankNifty is ' + 'Down ' + '@ ' + str(rounded_time) + '. Net = ' + str(banknifty_net) + '.  ' + str(banknifty_up) + ' Up, ' + str(banknifty_down) + ' Down Signals')
if finnifty_net > 0:
    outcum_list.append('FinNifty is ' + 'Up ' + '@ ' + str(rounded_time) + '. Net = ' + str(finnifty_net) + '.  ' + str(finnifty_up) + ' Up, ' + str(finnifty_down) + ' Down Signals')
elif finnifty_net < 0:
    outcum_list.append('FinNifty is ' + 'Down ' + '@ ' + str(rounded_time) + '. Net = ' + str(finnifty_net) + '.  ' + str(finnifty_up) + ' Up, ' + str(finnifty_down) + ' Down Signals')

def extract_info(msg):
    parts = msg.split()
    action = parts[0]
    option_type = parts[3][-2:]
    return (action, option_type)
msg_list = [msg_nifty, msg_banknifty, msg_finnifty]
# print(msg_list)
    
summary_df = pd.DataFrame({'Instrument': ['Nifty', 'BankNifty', 'FinNifty'], 'Time': [df1['time'][0], df1['time'][0],df1['time'][0]], 'Up': [nifty_up, banknifty_up, finnifty_up],
                           'Buy': [nifty_buy, banknifty_buy, finnifty_buy], 'Down': [nifty_down, banknifty_down, finnifty_down],
                           'Sell': [nifty_sell, banknifty_sell, finnifty_sell], 'Net': [nifty_net, banknifty_net, finnifty_net]})

path = r'D:\Data-with-Indicators\options_trigger\{}\{}'.format(year, month_name)
if not os.path.exists(path):
    os.makedirs(path)
    
path1 = r'D:\Data-with-Indicators\options_trigger\{}\{}\summary'.format(year, month_name)
if not os.path.exists(path1):
    os.makedirs(path1)

summary_file = os.path.join(path, 'summary', 'option_triggers_summary_{}.csv'.format(to_date))
if not os.path.exists(summary_file):
    summary_df.to_csv(summary_file, index=False, float_format='%.2f')
else:
    summary_df.to_csv(summary_file, index=False, float_format='%.2f', mode='a', header=False)

trigger_file = os.path.join(path, 'option_triggers_{}.csv'.format(to_date))
if not os.path.exists(trigger_file):
    trigger_df.to_csv(trigger_file, index=False, float_format='%.2f')
else:
    trigger_df.to_csv(trigger_file, index=False, float_format='%.2f', mode='a', header=False)
    
if (len(msg_list) > 0) and (len(outcum_list) > 0):
    for i, j in zip(msg_list, outcum_list):
        sorted_msg = sorted(i, key=extract_info, reverse=True)
        msg = '\n'.join(sorted_msg)
        requests.get(url.format(j))
        if len(msg) > 0:
            requests.get(url.format(msg))
