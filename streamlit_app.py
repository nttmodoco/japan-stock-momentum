import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# ---------------------------------------------------------
# ページの基本設定　ブラッシュアップ版
# ---------------------------------------------------------
st.set_page_config(
    page_title="日本株モメンタム分析ダッシュボード",
    page_icon="📈",
    layout="wide"
)

st.title("📈 日本株モメンタム & 出来高ダッシュボード")
st.markdown("直近の株価モメンタムと出来高の増加をリアルタイムでスクリーニングします。")

# ---------------------------------------------------------
# サイドバー：ユーザーによる判定パラメータの動的調整
# ---------------------------------------------------------
st.sidebar.header("⚙️ 判定パラメータ設定")
st.sidebar.markdown("スライダーを動かすと、リアルタイムで判定結果が再計算されます。")

SMA5_DEV_THRESHOLD = st.sidebar.slider("5日移動平均乖離率の閾値 (%)", 0.0, 5.0, 2.0, 0.5)
SMA20_DEV_THRESHOLD = st.sidebar.slider("20日移動平均乖離率の閾値 (%)", 0.0, 5.0, 3.0, 0.5)
VOL_RATIO_THRESHOLD = st.sidebar.slider("出来高増加倍率の閾値", 1.0, 2.5, 1.3, 0.1)

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

# ---------------------------------------------------------
# モメンタム算出関数
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_and_calculate_momentum(sma5_th, sma20_th, vol_th):
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
            
            # 出来高増加率
            df['Vol_SMA5'] = df['Volume'].rolling(window=5).mean()
            df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
            vol_ratio = df['Vol_SMA5'].iloc[-1] / df['Vol_SMA20'].iloc[-1] if df['Vol_SMA20'].iloc[-1] > 0 else 0.0
            
            # パラメータを用いた判定
            is_alert = (sma5_dev >= sma5_th) and (sma20_dev >= sma20_th) and (vol_ratio >= vol_th)
            
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

# データ取得・計算実行（サイドバーのスライダー値連動）
with st.spinner("リアルタイム株価データを取得・解析中..."):
    df_results = fetch_and_calculate_momentum(SMA5_DEV_THRESHOLD, SMA20_DEV_THRESHOLD, VOL_RATIO_THRESHOLD)

# ---------------------------------------------------------
# 上段：KPIメトリクス表示
# ---------------------------------------------------------
if not df_results.empty:
    total_stocks = len(df_results)
    alert_count = len(df_results[df_results["アラート発動"] == "🚨 発動"])
    
    col_kpi1, col_kpi2 = st.columns(2)
    col_kpi1.metric("監視対象銘柄数", f"{total_stocks} 銘柄")
    col_kpi2.metric("アラート発動銘柄数", f"{alert_count} 銘柄", delta=f"{alert_count} 該当" if alert_count > 0 else "なし", delta_color="inverse" if alert_count > 0 else "off")

st.markdown("---")

# ---------------------------------------------------------
# 中段：モメンタム一覧テーブル ＆ CSVダウンロード
# ---------------------------------------------------------
st.subheader("📋 監視銘柄モメンタム一覧")

if not df_results.empty:
    # テーブル表示
    st.dataframe(df_results.drop(columns=["YahooTicker"]), use_container_width=True)
    
    # ワンクリックCSVダウンロードボタン
    csv_data = df_results.drop(columns=["YahooTicker"]).to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 現在のスクリーニング結果をCSVでダウンロード",
        data=csv_data,
        file_name=f"momentum_report_{datetime.today().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("データを取得できませんでした。")

st.markdown("---")

# ---------------------------------------------------------
# 下段：個別銘柄の過去20日グラフ
# ---------------------------------------------------------
st.subheader("📊 銘柄別 過去20営業日の出来高＆株価推移")

if not df_results.empty:
    selected_name = st.selectbox(
        "詳細グラフを確認する銘柄を選択してください", 
        df_results["銘柄名"].tolist()
    )
    
    selected_row = df_results[df_results["銘柄名"] == selected_name].iloc[0]
    ticker_symbol = selected_row["YahooTicker"]
    
    stock_detail = yf.Ticker(ticker_symbol)
    df_hist = stock_detail.history(period="2mo").tail(20)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{selected_name} - 出来高推移**")
        st.bar_chart(df_hist['Volume'])
        
    with col2:
        st.markdown(f"**{selected_name} - 株価終値推移**")
        st.line_chart(df_hist['Close'])
