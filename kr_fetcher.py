"""
국내 증시 데이터 및 뉴스 수집 모듈
- yfinance: 코스피/코스닥 지수 및 주가 데이터
- feedparser: 국내 금융 뉴스 RSS
"""
import yfinance as yf
import feedparser
from datetime import datetime

# 주요 지수
INDICES = {
    '^KS11':  '코스피',
    '^KQ11':  '코스닥',
    '^KS200': '코스피 200',
}

# 시가총액 상위 유니버스 (KOSPI + KOSDAQ 인기 종목)
UNIVERSE = [
    # KOSPI 대형주
    '005930.KS',  # 삼성전자
    '000660.KS',  # SK하이닉스
    '005490.KS',  # POSCO홀딩스
    '005380.KS',  # 현대차
    '000270.KS',  # 기아
    '035420.KS',  # NAVER
    '035720.KS',  # 카카오
    '051910.KS',  # LG화학
    '006400.KS',  # 삼성SDI
    '373220.KS',  # LG에너지솔루션
    '207940.KS',  # 삼성바이오로직스
    '068270.KS',  # 셀트리온
    '105560.KS',  # KB금융
    '055550.KS',  # 신한지주
    '086790.KS',  # 하나금융지주
    '003550.KS',  # LG
    '012330.KS',  # 현대모비스
    '028260.KS',  # 삼성물산
    '018260.KS',  # 삼성에스디에스
    '034020.KS',  # 두산에너빌리티
    # KOSDAQ 대형주
    '247540.KQ',  # 에코프로비엠
    '086520.KQ',  # 에코프로
    '323410.KS',  # 카카오뱅크
    '259960.KS',  # 크래프톤
    '293490.KS',  # 카카오페이
]

# 종목명 매핑
TICKER_NAMES = {
    '005930.KS': '삼성전자',
    '000660.KS': 'SK하이닉스',
    '005490.KS': 'POSCO홀딩스',
    '005380.KS': '현대차',
    '000270.KS': '기아',
    '035420.KS': 'NAVER',
    '035720.KS': '카카오',
    '051910.KS': 'LG화학',
    '006400.KS': '삼성SDI',
    '373220.KS': 'LG에너지솔루션',
    '207940.KS': '삼성바이오로직스',
    '068270.KS': '셀트리온',
    '105560.KS': 'KB금융',
    '055550.KS': '신한지주',
    '086790.KS': '하나금융지주',
    '003550.KS': 'LG',
    '012330.KS': '현대모비스',
    '028260.KS': '삼성물산',
    '018260.KS': '삼성에스디에스',
    '034020.KS': '두산에너빌리티',
    '247540.KQ': '에코프로비엠',
    '086520.KQ': '에코프로',
    '323410.KS': '카카오뱅크',
    '259960.KS': '크래프톤',
    '293490.KS': '카카오페이',
}

# 국내 금융 뉴스 RSS 피드
NEWS_FEEDS = [
    'https://www.yna.co.kr/rss/economy.xml',
    'https://www.hankyung.com/feed/all-news',
    'https://www.mk.co.kr/rss/30100041/',
    'https://rss.edaily.co.kr/edaily/finance.xml',
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
            'close': round(close, 0),
            'change': round(change, 0),
            'pct': round(pct, 2),
            'volume': volume,
        }
    except Exception as e:
        print(f"  [kr_fetcher] {ticker} 파싱 오류: {e}")
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
    """거래량 상위 N개 종목 반환."""
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
        print(f"  [kr_fetcher] 거래량 상위 오류: {e}")
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
            data['name'] = TICKER_NAMES.get(ticker, ticker.replace('.KS', '').replace('.KQ', ''))
            result[ticker] = data

    return result


def get_weekly_data(tickers=None):
    """최근 5 거래일 수익률 반환."""
    if tickers is None:
        tickers = ['^KS11', '^KQ11', '^KS200']

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
            print(f"  [kr_fetcher] 주간 데이터 오류 {ticker}: {e}")
    return result


def get_news(max_items=12):
    """국내 금융 뉴스 헤드라인 리스트 반환."""
    articles = []
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '').strip()[:150]
                if title:
                    articles.append(f"• {title}" + (f": {summary}" if summary else ""))
        except Exception as e:
            print(f"  [kr_fetcher] 뉴스 피드 오류: {e}")

    return articles[:max_items]
