import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import random
import pandas as pd
import numpy as np
from datetime import datetime

# ================= 設定 =================
STOCK_POOL = ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2881.TW", "2882.TW", "2382.TW"]
VISIBLE_DAYS = 30  # 初始顯示天數
TOTAL_DAYS = 80   # 總模擬天數 (根據要求延長至 80 天)

st.set_page_config(page_title="台股K線實戰模擬器 Pro", layout="wide")

# CSS 優化按鈕與佈局
st.markdown("""
    <style>
    div.stButton > button {
        height: 2em;
        padding-top: 0px;
        padding-bottom: 0px;
        font-size: 14px;
    }
    .stMetric {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 初始化 Session State
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'START'
if 'current_data' not in st.session_state:
    st.session_state.current_data = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = VISIBLE_DAYS
if 'position' not in st.session_state:
    st.session_state.position = None
if 'entry_price' not in st.session_state:
    st.session_state.entry_price = 0.0
if 'total_return' not in st.session_state:
    st.session_state.total_return = 0.0
if 'history' not in st.session_state:
    st.session_state.history = []

def get_random_slice():
    """隨機選擇一隻股票並截取 80 天數據"""
    ticker_symbol = random.choice(STOCK_POOL)
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="5y") # 增加抓取範圍確保足夠數據

    if len(df) < TOTAL_DAYS + 20:
        return get_random_slice()

    max_start = len(df) - TOTAL_DAYS
    start_idx = random.randint(0, max_start)
    slice_df = df.iloc[start_idx : start_idx + TOTAL_DAYS].copy()
    return ticker_symbol, slice_df

def draw_chart(df, current_step, history):
    """繪製K線圖，並標記買賣點"""
    plot_df = df.iloc[:current_step].copy()

    # 準備標記買賣點
    buy_x, buy_y = [], []
    sell_x, sell_y = [], []

    # 從歷史記錄中提取買賣點 (將相對天數轉為索引日期)
    # 注意：history 記錄的是 "第 X 天"，對應 df 的索引是 start_idx + (X-1)
    # 但因為 plot_df 是從 0 開始，所以直接用 X-1
    for log in history:
        if "買入" in log:
            day = int(log.split(" ")[1].replace("第", "").replace("天:", ""))
            # 檢查該天是否在目前顯示範圍內
            if day <= current_step:
                buy_x.append(plot_df.index[day-1])
                buy_y.append(plot_df.iloc[day-1]['Low'] * 0.98)
        elif "賣出" in log or "強制平倉" in log:
            day = int(log.split(" ")[1].replace("第", "").replace("天:", ""))
            if day <= current_step:
                sell_x.append(plot_df.index[day-1])
                sell_y.append(plot_df.iloc[day-1]['High'] * 1.02)

    fig = go.Figure()

    # K線圖
    fig.add_trace(go.Candlestick(
        x=plot_df.index,
        open=plot_df['Open'],
        high=plot_df['High'],
        low=plot_df['Low'],
        close=plot_df['Close'],
        name="K線"
    ))

    # 買入標記 (綠色箭頭)
    fig.add_trace(go.Scatter(
        x=buy_x, y=buy_y,
        mode='markers',
        marker=dict(symbol='triangle-up', size=12, color='lime'),
        name='買入'
    ))

    # 賣出標記 (紅色箭頭)
    fig.add_trace(go.Scatter(
        x=sell_x, y=sell_y,
        mode='markers',
        marker=dict(symbol='triangle-down', size=12, color='red'),
        name='賣出'
    ))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10),
        height=600,
        title=f"目前進度: 第 {current_step}/{TOTAL_DAYS} 天",
        yaxis=dict(fixedrange=False)
    )
    return fig

# ================= UI 介面 =================
st.title("📉 台股K線實戰模擬器 Pro")

# 遊戲邏輯控制
if st.session_state.game_state == 'START':
    if st.button("🚀 開始模擬交易", use_container_width=True):
        ticker, data = get_random_slice()
        st.session_state.current_data = (ticker, data)
        st.session_state.game_state = 'TRADING'
        st.session_state.current_step = VISIBLE_DAYS
        st.session_state.position = 'CASH'
        st.session_state.history = []
        st.rerun()

elif st.session_state.game_state == 'TRADING':
    ticker_symbol, df = st.session_state.current_data

    # 標出股票名稱與時間區間
    start_date = df.index[0].strftime('%Y-%m-%d')
    end_date = df.index[-1].strftime('%Y-%m-%d')
    st.markdown(f"### 股票: `{ticker_symbol}` | 模擬區間: `{start_date}` $\rightarrow$ `{end_date}`")

    # 頂部狀態欄
    stat_col1, stat_col2, stat_col3 = st.columns([1, 1, 2])
    with stat_col1:
        pos_text = "🟢 持倉中" if st.session_state.position == 'LONG' else "⚪ 空倉"
        st.metric("交易狀態", pos_text)
    with stat_col2:
        st.metric("買入價", f"{st.session_state.entry_price:.2f}" if st.session_state.position == 'LONG' else "-")
    with stat_col3:
        st.metric("目前累積收益", f"{st.session_state.total_return:.2f}%")

    # 顯示圖表
    chart = draw_chart(df, st.session_state.current_step, st.session_state.history)
    st.plotly_chart(chart, use_container_width=True)

    # 交易控制區
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5 = st.columns([1, 1, 1, 1, 2])
    current_price = df.iloc[st.session_state.current_step - 1]['Close']

    with ctrl_col1:
        if st.button("🟢 買入", use_container_width=True, disabled=(st.session_state.position == 'LONG')):
            st.session_state.position = 'LONG'
            st.session_state.entry_price = current_price
            st.session_state.history.append(f"第 {st.session_state.current_step} 天: 買入 @ {current_price:.2f}")
            st.rerun()
    with ctrl_col2:
        if st.button("⚪ 觀望", use_container_width=True):
            st.session_state.history.append(f"第 {st.session_state.current_step} 天: 觀望")
            st.session_state.current_step += 1
            if st.session_state.current_step > TOTAL_DAYS:
                st.session_state.game_state = 'RESULT'
            st.rerun()
    with ctrl_col3:
        if st.button("🔴 賣出", use_container_width=True, disabled=(st.session_state.position == 'CASH')):
            profit = (current_price - st.session_state.entry_price) / st.session_state.entry_price * 100
            st.session_state.total_return += profit
            st.session_state.position = 'CASH'
            st.session_state.history.append(f"第 {st.session_state.current_step} 天: 賣出 @ {current_price:.2f} (損益: {profit:.2f}%)")
            st.rerun()
    with ctrl_col4:
        if st.button("⏭️ 下一天", use_container_width=True):
            st.session_state.current_step += 1
            if st.session_state.current_step > TOTAL_DAYS:
                if st.session_state.position == 'LONG':
                    final_price = df.iloc[-1]['Close']
                    profit = (final_price - st.session_state.entry_price) / st.session_state.entry_price * 100
                    st.session_state.total_return += profit
                    st.session_state.history.append(f"第 {TOTAL_DAYS} 天: 強制平倉 @ {final_price:.2f} (損益: {profit:.2f}%)")
                st.session_state.game_state = 'RESULT'
            st.rerun()
    with ctrl_col5:
        st.markdown(f"<div style='text-align: center; font-weight: bold;'>現價: {current_price:.2f}</div>", unsafe_allow_html=True)

    with st.expander("📜 交易日誌"):
        for log in st.session_state.history:
            st.write(log)

elif st.session_state.game_state == 'RESULT':
    ticker_symbol, df = st.session_state.current_data
    # 最終結果顯示包含所有買賣標記
    chart = draw_chart(df, TOTAL_DAYS, st.session_state.history)
    st.plotly_chart(chart, use_container_width=True)

    st.divider()
    st.header("🏁 模擬結果")
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        color = "green" if st.session_state.total_return >= 0 else "red"
        st.markdown(f"### 總累計收益率: <span style='color:{color}'>{st.session_state.total_return:.2f}%</span>", unsafe_allow_html=True)
    with res_col2:
        st.write(f"模擬股票: **{ticker_symbol}**")
        st.write(f"區間: {df.index[0].strftime('%Y-%m-%d')} $\rightarrow$ {df.index[-1].strftime('%Y-%m-%d')}")

    st.subheader("交易過程回顧")
    for log in st.session_state.history:
        st.write(log)

    if st.button("🔄 再玩一次", use_container_width=True):
        st.session_state.game_state = 'START'
        st.session_state.current_data = None
        st.session_state.total_return = 0.0
        st.rerun()
