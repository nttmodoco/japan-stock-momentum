import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# ---------------------------------------------------------
# ページの基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="日本株モメンタム & 出来高ダッシュボード"
    ,
    page_icon="📈",
    layout="wide"
)

st.title("📈 日本株モメンタム & 出来高ダッシュボード")
st.markdown("直近のモメンタム指標（移動平均乖離・出来高増加）を算出し、アラート発動銘柄を一覧表示します。")

# 監視対象銘柄
TARGET_TICKERS = {
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニーグループ",
    "9984.T": "ソフトバンクグループ",
    "8306.T": "三菱UFJフィナンシャルG",
    "6857.T": "アドバンテスト",
    "8035.T": "東京エレクトロン",
    "6501.T": "日立製作所",
    "7011.T": "三菱重工業",
    "9983.T": "ファーストリテイリング",
    "4063.T": "信越化学工業"
}

# 判定閾値
SMA5_DEV_THRESHOLD = 2.0
SMA20_DEV_THRESHOLD = 3.0
VOL_RATIO_THRESHOLD = 1.3

# ---------------------------------------------------------
# モメンタム算出関数
# ---------------------------------------------------------
@st.cache_data(ttl=3600) # 1時間キャッシュして動作を高速化
def fetch_and_calculate_momentum():
    results = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days=60)
    
    for ticker, name in TARGET_TICKERS.items():
        try:
            df = yf.Ticker(ticker).history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
            if len(df) < 20:
                continue
                
            latest_close = df['Close'].iloc[-1]
            
            # 5日・20日移動平均と乖離率
            df['SMA5'] = df['Close'].rolling(window=5).mean()
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            sma5_dev = ((latest_close - df['SMA5'].iloc[-1]) / df['SMA5'].iloc[-1]) * 100
            sma20_dev = ((latest_close - df['SMA20'].iloc[-1]) / df['SMA20'].iloc[-1]) * 100
            
            # 出来高増加率 (直近5日平均 / 直近20日平均)
            df['Vol_SMA5'] = df['Volume'].rolling(window=5).mean()
            df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
            vol_ratio = df['Vol_SMA5'].iloc[-1] / df['Vol_SMA20'].iloc[-1] if df['Vol_SMA20'].iloc[-1] > 0 else 0.0
            
            # 判定
            is_alert = (sma5_dev >= SMA5_DEV_THRESHOLD) and (sma20_dev >= SMA20_DEV_THRESHOLD) and (vol_ratio >= VOL_RATIO_THRESHOLD)
            
            results.append({
                "コード": ticker.replace(".T", ""),
                "銘柄名": name,
                "株価": round(latest_close, 1),
                "5日乖離率(%)": round(sma5_dev, 2),
                "20日乖離率(%)": round(sma20_dev, 2),
                "出来高倍率": round(vol_ratio, 2),
                "アラート発動": "🚨 発動" if is_alert else "正常",
                "YahooTicker": ticker
            })
        except Exception as e:
            print(f"Error {ticker}: {e}")
            
    return pd.DataFrame(results)

# データの読み込み実行
with st.spinner("株価データを取得してモメンタムを計算中..."):
    df_results = fetch_and_calculate_momentum()

# ---------------------------------------------------------
# 画面レイアウト：上段（モメンタム一覧テーブル）
# ---------------------------------------------------------
st.subheader("📋 監視銘柄モメンタム一覧")
if not df_results.empty:
    # アラート発動行を強調するなどのカスタマイズも可能
    st.dataframe(df_results.drop(columns=["YahooTicker"]), use_container_width=True)
else:
    st.warning("データを取得できませんでした。")

st.markdown("---")

# ---------------------------------------------------------
# 画面レイアウト：下段（個別銘柄の過去20日グラフ）
# ---------------------------------------------------------
st.subheader("📊 銘柄別 過去20営業日の出来高＆株価推移")

if not df_results.empty:
    # セレクトボックスで銘柄を選択
    selected_name = st.selectbox(
        "詳細を確認する銘柄を選択してください", 
        df_results["銘柄名"].tolist()
    )
    
    # 選択された銘柄のTickerを取得
    selected_row = df_results[df_results["銘柄名"] == selected_name].iloc[0]
    ticker_symbol = selected_row["YahooTicker"]
    
    # 該当銘柄の詳細データを取得（直近35日＝約20営業日＋α）
    stock_detail = yf.Ticker(ticker_symbol)
    df_hist = stock_detail.history(period="2mo").tail(20)
    
    # 2カラムに分けてグラフを配置
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{selected_name} - 出来高推移 (直近20営業日)**")
        # Streamlit標準の棒グラフ機能
        st.bar_chart(df_hist['Volume'])
        
    with col2:
        st.markdown(f"**{selected_name} - 株価終値推移 (直近20営業日)**")
        # Streamlit標準の折れ線グラフ機能
        st.line_chart(df_hist['Close'])