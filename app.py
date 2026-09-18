# ==========================================
# THE ULTIMATE QUEEN TRADING SUITE (ALL-IN-ONE)
# ==========================================

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gradio as gr
import requests

def fetch_market_data(ticker_symbol, interval="1h", period="1mo"):
    """Fetches clean market data from Yahoo Finance."""
    try:
        df = yf.download(ticker_symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        return df
    except Exception as e:
        return None

def detect_fair_value_gaps(df):
    """Detects institutional Fair Value Gaps (FVGs) in price action."""
    fvgs = []
    if df is None or len(df) < 3:
        return fvgs
        
    for i in range(1, len(df) - 1):
        prev_high = df.iloc[i-1]['High']
        prev_low = df.iloc[i-1]['Low']
        next_low = df.iloc[i+1]['Low']
        next_high = df.iloc[i+1]['High']
        
        # Bullish FVG
        if next_low > prev_high:
            fvgs.append({
                'type': 'BULLISH FVG',
                'zone_low': prev_high,
                'zone_high': next_low,
                'index': df.index[i]
            })
        # Bearish FVG
        elif next_high < prev_low:
            fvgs.append({
                'type': 'BEARISH FVG',
                'zone_low': next_high,
                'zone_high': prev_low,
                'index': df.index[i]
            })
    return fvgs

def send_telegram_alert(token, chat_id, message):
    """Sends real-time push notifications to your phone via Telegram."""
    if not token or not chat_id:
        return "Telegram credentials not provided (App alerts active)."
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        return "Telegram Push Sent Successfully!" if response.status_code == 200 else f"Telegram Error: {response.text}"
    except Exception as e:
        return f"Alert Dispatch Failed: {str(e)}"

def queen_ultimate_scanner_with_profit(execution_timeframe, account_size, leverage, tele_token, tele_chat_id, user_command):
    watchlist = {
        "Gold (XAU/USD)": "GC=F",
        "EUR/USD (Euro Major)": "EURUSD=X",
        "GBP/USD (Cable Major)": "GBPUSD=X",
        "USD/JPY (Japanese Yen)": "USDJPY=X"
    }
    
    greeting_reply = f"👑 Queen: Ultimate scan active on [{execution_timeframe}]. Calculating lot size, timing, and projected profit."
    
    master_report = "==================================================\n"
    master_report += "ULTIMATE INSTITUTIONAL SCANNER + PROFIT TARGET\n"
    master_report += f"Execution Frame: {execution_timeframe} | Capital: ${account_size:,.2f}\n"
    master_report += "==================================================\n\n"
    
    valid_setups = 0
    first_valid_df = None
    first_valid_fvg = None
    scanned_asset_name = "No Asset"
    
    higher_tf_map = {"1m": "15m", "5m": "1h", "15m": "4h", "1h": "1d", "4h": "1d", "1d": "1wk"}
    higher_tf = higher_tf_map.get(execution_timeframe, "1d")
    tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    candle_mins = tf_minutes.get(execution_timeframe, 60)
    
    dispatch_log = "No alerts triggered."
    
    for asset_name, ticker in watchlist.items():
        df_higher = fetch_market_data(ticker, interval=higher_tf, period="3mo")
        higher_bias = "NEUTRAL"
        if df_higher is not None and not df_higher.empty:
            if df_higher.iloc[-1]['Close'] > df_higher.iloc[-5]['Close']:
                higher_bias = "BULLISH"
            else:
                higher_bias = "BEARISH"
                
        df = fetch_market_data(ticker, interval=execution_timeframe, period="1mo")
        if df is None or df.empty:
            continue
            
        fvgs = detect_fair_value_gaps(df)
        if not fvgs:
            continue
            
        latest_fvg = fvgs[-1]
        current_price = df.iloc[-1]['Close']
        
        setup_type = latest_fvg['type']
        if higher_bias == "BULLISH" and setup_type != "BULLISH FVG":
            continue
        if higher_bias == "BEARISH" and setup_type != "BEARISH FVG":
            continue
            
        valid_setups += 1
        
        if first_valid_df is None:
            first_valid_df = df
            first_valid_fvg = latest_fvg
            scanned_asset_name = asset_name
            
        if setup_type == "BULLISH FVG":
            entry = latest_fvg['zone_low']
            sl = entry - (entry * 0.003)
            risk_unit = entry - sl
            tp = entry + (risk_unit * 3.0)
            bias = "LONG / BUY"
        else:
            entry = latest_fvg['zone_high']
            sl = entry + (entry * 0.003)
            risk_unit = sl - entry
            tp = entry - (risk_unit * 3.0)
            bias = "SHORT / SELL"
            
        allowed_risk_dollars = account_size * 0.01  
        projected_profit_dollars = allowed_risk_dollars * 3.0  
        
        price_risk_distance = abs(entry - sl)
        if price_risk_distance <= 0:
            lots = 0.01
        else:
            if "USDJPY=X" in ticker:
                pip_risk = price_risk_distance * 100
                lots = allowed_risk_dollars / (pip_risk * 10)
            elif "GC=F" in ticker:
                lots = allowed_risk_dollars / (price_risk_distance * 100)
            else:
                pip_risk = price_risk_distance * 10000
                lots = allowed_risk_dollars / (pip_risk * 10)
        lots = max(0.01, round(lots, 2))
        
        avg_range = (df['High'] - df['Low']).mean() if not df.empty else 0.0010
        if avg_range <= 0: avg_range = 0.0010
        
        dist_to_entry = abs(current_price - entry)
        entry_candles = max(1, int(dist_to_entry / avg_range))
        entry_mins = entry_candles * candle_mins
        
        tp_distance = risk_unit * 3.0
        tp_candles = max(1, int(tp_distance / avg_range))
        tp_mins = tp_candles * candle_mins
        
        def format_time(mins):
            if mins < 60: return f"~{mins} Mins"
            elif mins < 1440: return f"~{round(mins / 60, 1)} Hours"
            else: return f"~{round(mins / 1440, 1)} Days"
            
        is_at_entry = latest_fvg['zone_low'] <= current_price <= latest_fvg['zone_high']
        is_at_tp = (bias == "LONG / BUY" and current_price >= tp) or (bias == "SHORT / SELL" and current_price <= tp)
        is_at_sl = (bias == "LONG / BUY" and current_price <= sl) or (bias == "SHORT / SELL" and current_price >= sl)
        
        if is_at_tp or is_at_sl:
            status_label = "TRADE COMPLETED / HIT TARGET OR STOP"
            dispatch_log = send_telegram_alert(tele_token, tele_chat_id, f"🏁 *QUEEN EXIT ALERT!*\nAsset: {asset_name}\nTrade completed at price: `{current_price:.5f}`")
        elif is_at_entry:
            status_label = "ACTIVE / ZONE REACHED"
            dispatch_log = send_telegram_alert(tele_token, tele_chat_id, f"🚨 *QUEEN ENTRY ALERT!*\nAsset: {asset_name}\nTapped Entry: `{entry:.5f}` | Lots: {lots}")
        else:
            status_label = "PENDING / MONITORING"
            dispatch_log = send_telegram_alert(tele_token, tele_chat_id, f"⏳ *QUEEN SETUP MONITOR*\nAsset: {asset_name}\nEst. Time to Entry: {format_time(entry_mins)}")

        master_report += f"📍 ASSET: {asset_name.upper()}\n"
        master_report += f"   Top-Down Bias ({higher_tf}) : {higher_bias}\n"
        master_report += f"   Execution Structure      : {setup_type} ({bias})\n"
        master_report += f"   Entry Limit              : {entry:.5f} | SL: {sl:.5f} | TP (1:3): {tp:.5f}\n"
        master_report += f"   Position Sizing          : {lots} Lots\n"
        
        master_report += f"   ⏱️ Est. Time-to-Entry     : {format_time(entry_mins)}\n"
        master_report += f"   ⏱️ Est. Time-to-Target (TP): {format_time(tp_mins)}\n"
        master_report += f"   🔔 Lifecycle Status      : {status_label}\n"
        master_report += "--------------------------------------------------\n"
        
    if valid_setups == 0:
        master_report += "Status: STAND ASIDE. No aligned setups found on Core Four.\n"
        fig = go.Figure()
        fig.update_layout(template="plotly_white", title="No Aligned Setups Found")
        return greeting_reply, master_report, fig
        
    master_report += f"\nScan Complete. Notification Log: {dispatch_log}"
    
    fig = go.Figure(data=[go.Candlestick(
        x=first_valid_df.index, open=first_valid_df['Open'], high=first_valid_df['High'], 
        low=first_valid_df['Low'], close=first_valid_df['Close'], name="Price Action"
    )])
    
    color = "rgba(40, 167, 69, 0.15)" if first_valid_fvg['type'] == "BULLISH FVG" else "rgba(220, 53, 69, 0.15)"
    line_col = "green" if first_valid_fvg['type'] == "BULLISH FVG" else "red"
    
    fig.add_shape(
        type="rect", x0=first_valid_df.index[0], y0=first_valid_fvg['zone_low'], 
        x1=first_valid_df.index[-1], y1=first_valid_fvg['zone_high'],
        fillcolor=color, line=dict(color=line_col, width=1, dash="dot"), layer="below"
    )
    
    if first_valid_fvg['type'] == "BULLISH FVG":
        e_val = first_valid_fvg['zone_low']
        s_val = e_val - (e_val * 0.003)
        t_val = e_val + ((e_val - s_val) * 3.0)
    else:
        e_val = first_valid_fvg['zone_high']
        s_val = e_val + (e_val * 0.003)
        t_val = e_val - ((s_val - e_val) * 3.0)
        
    fig.add_hline(y=e_val, line_dash="solid", line_color="blue", annotation_text=f"ENTRY: {e_val:.5f}", annotation_position="top left")
    fig.add_hline(y=s_val, line_dash="dash", line_color="red", annotation_text=f"STOP LOSS: {s_val:.5f}", annotation_position="bottom left")
    fig.add_hline(y=t_val, line_dash="dash", line_color="green", annotation_text=f"TAKE PROFIT (1:3): {t_val:.5f}", annotation_position="top left")

    fig.update_layout(
        title=f"👑 Queen Ultimate Lifecycle: {scanned_asset_name} [{execution_timeframe}]",
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=600,
        font=dict(family="Arial", size=12, color="black")
    )
    
    return greeting_reply, master_report, fig

with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 👑 Queen: Ultimate Institutional Trading Suite + Profit Projection")
    gr.Markdown("Core Four scanner featuring corrected lot sizing, exact projected profit targets, entry/exit timing, and push notifications.")
    
    with gr.Row():
        with gr.Column(scale=1):
            user_command = gr.Textbox(label="Operational Command", value="Run scan with profit and timing breakdown.")
            execution_timeframe = gr.Dropdown(label="Execution Timeframe", choices=["1m", "5m", "15m", "1h", "4h", "1d"], value="1h")
            account_size = gr.Number(label="Account Balance ($)", value=10000.0)
            leverage = gr.Slider(label="Account Leverage", minimum=1, maximum=500, value=100, step=1)
            
            with gr.Accordion("Telegram Push Settings (Optional)", open=False):
                tele_token = gr.Textbox(label="Bot Token", placeholder="Bot token...")
                tele_chat_id = gr.Textbox(label="Chat ID", placeholder="Chat ID...")
                
            submit_btn = gr.Button("Run Ultimate Scan", variant="primary")
            
        with gr.Column(scale=2):
            chat_response = gr.Textbox(label="Queen's Voice Response")
            output_display = gr.Textbox(label="Master Lifecycle Report", lines=15)
            
    with gr.Row():
        chart_output = gr.Plot(label="Spotlight Visual Chart")
        
    submit_btn.click(
        fn=queen_ultimate_scanner_with_profit, 
        inputs=[execution_timeframe, account_size, leverage, tele_token, tele_chat_id, user_command], 
        outputs=[chat_response, output_display, chart_output]
    )

demo.launch(inline=True)
