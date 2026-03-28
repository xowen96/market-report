"""
시장 데이터 및 뉴스 수집 모듈
- yfinance: 주가/지수 데이터 (무료)
- feedparser: 금융 뉴스 RSS (무료)
"""
import yfinance as yf
import feedparser
from datetime import datetime

# 주요 지수
INDICES = {
    '^NDX': '나스닥 100',
    '^GSPC': 'S&P 500',
    '^DJI': '다우존스',
    '^RUT': '러셀 2000',
}

# 거래량 상위 탐색용 유니버스 (S&P500 대형주 + 인기 종목)
UNIVERSE = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AMD',
    'AVGO', 'INTC', 'MU', 'QCOM', 'NFLX', 'DIS', 'PLTR',
    'TSM', 'SMCI', 'ARM', 'MSTR', 'COIN', 'HOOD',
    'JPM', 'BAC', 'GS', 'XOM', 'CVX',
    'UBER', 'SNAP', 'RIVN', 'NIO',
    'SPY', 'QQQ', 'SOXX', 'SOXL', 'TQQQ', 'NVDL',
    'V', 'PYPL', 'SHOP', 'RBLX', 'DKNG', 'ROKU',
    'F', 'GM', 'BABA', 'JD', 'PDD',
]

# 금융 뉴스 RSS 피드
NEWS_FEEDS = [
    'https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EIXIC&region=US&lang=en-US',
    'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    'https://www.marketwatch.com/rss/topstories',
    'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
]


def _extract_ticker(df, ticker, is_list=True):
    """DataFrame에서 단일 티커 데이터 추출."""
    try:
        if is_list:
            closes = df['Close'][ticker].dropna()
            volumes = df['Volume'][ticker].dropna()
        else:
            closes = df['Close'].dropna()
            volumes = df['Volume'].dropna()

        if len(closes) < 2:
            return None

        close = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        volume = int(volumes.iloc[-1]) if len(volumes) > 0 else 0
        change = close - prev
        pct = (change / prev) * 100

        return {
            'close': round(close, 2),
            'change': round(change, 2),
            'pct': round(pct, 2),
            'volume': volume,
        }
    except Exception as e:
        print(f"  [fetcher] {ticker} 파싱 오류: {e}")
        return None


def get_index_data():
    """주요 지수 데이터 반환."""
    tickers = list(INDICES.keys())
    df = yf.download(tickers, period='5d', progress=False, auto_adjust=True)
    result = {}
    for ticker, name in INDICES.items():
        data = _extract_ticker(df, ticker, is_list=True)
        if data:
            data['name'] = name
            result[ticker] = data
    return result


def get_top_volume_stocks(n=8, exclude=None):
    """거래량 상위 N개 종목 티커 리스트 반환."""
    if exclude is None:
        exclude = []
    universe = [t for t in UNIVERSE if t not in exclude]

    try:
        df = yf.download(universe, period='2d', progress=False, auto_adjust=True)
        volume_row = df['Volume'].iloc[-1].dropna()
        top = volume_row.nlargest(n + len(exclude)).index.tolist()
        top = [t for t in top if t not in exclude]
        return top[:n]
    except Exception as e:
        print(f"  [fetcher] 거래량 상위 오류: {e}")
        return universe[:n]


def get_stock_data(tickers):
    """종목 리스트의 당일 데이터 반환."""
    if not tickers:
        return {}

    df = yf.download(tickers, period='5d', progress=False, auto_adjust=True)
    result = {}
    is_list = len(tickers) > 1

    for ticker in tickers:
        data = _extract_ticker(df, ticker, is_list=is_list)
        if data:
            result[ticker] = data

    return result


def get_weekly_data(tickers=None):
    """최근 5 거래일 수익률 반환."""
    if tickers is None:
        tickers = ['^NDX', '^GSPC', 'QLD', 'NVDL']

    df = yf.download(tickers, period='10d', progress=False, auto_adjust=True)
    result = {}
    for ticker in tickers:
        try:
            closes = df['Close'][ticker].dropna() if len(tickers) > 1 else df['Close'].dropna()
            if len(closes) >= 5:
                start = float(closes.iloc[-5])
                end = float(closes.iloc[-1])
                result[ticker] = round((end - start) / start * 100, 2)
        except Exception as e:
            print(f"  [fetcher] 주간 데이터 오류 {ticker}: {e}")
    return result


def get_news(max_items=12):
    """금융 뉴스 헤드라인 리스트 반환."""
    articles = []
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '').strip()[:200]
                if title:
                    articles.append(f"• {title}" + (f": {summary}" if summary else ""))
        except Exception as e:
            print(f"  [fetcher] 뉴스 피드 오류: {e}")

    return articles[:max_items]
