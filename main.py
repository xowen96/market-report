#!/usr/bin/env python3
"""
미국 증시 시황 보고서 자동 발송 시스템
매주 평일 오전 8시 KST (GitHub Actions 스케줄: 23:00 UTC)
"""
import sys
from datetime import datetime
import pytz

from fetcher import get_index_data, get_stock_data, get_top_volume_stocks, get_weekly_data, get_news
from analyzer import generate_analysis
from sender import send_report


def main():
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    print(f"\n{'='*50}")
    print(f"미국 증시 시황 보고서 생성 시작")
    print(f"실행 시각: {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*50}\n")

    # 1. 주요 지수 데이터
    print("[1/5] 주요 지수 데이터 수집 중...")
    index_data = get_index_data()
    print(f"  수집 완료: {list(index_data.keys())}")

    # 2. 거래량 상위 종목 탐색 (QLD 제외 후 8개)
    print("[2/5] 거래량 상위 종목 탐색 중...")
    top_stocks = get_top_volume_stocks(n=8, exclude=['QLD'])
    all_tickers = ['QLD'] + top_stocks
    print(f"  종목 확정: {all_tickers}")

    # 3. 종목 데이터
    print("[3/5] 종목 데이터 수집 중...")
    stock_data = get_stock_data(all_tickers)
    print(f"  수집 완료: {list(stock_data.keys())}")

    # 4. 주간 성과 데이터
    print("[4/5] 주간 성과 데이터 수집 중...")
    # QLD + 지수 주간 성과
    weekly_tickers = ['^NDX', '^GSPC', 'QLD']
    if 'NVDL' in stock_data:
        weekly_tickers.append('NVDL')
    weekly_data = get_weekly_data(weekly_tickers)

    # 5. 뉴스 수집
    print("[4.5/5] 뉴스 수집 중...")
    news = get_news(max_items=12)
    print(f"  뉴스 {len(news)}건 수집 완료")

    # 6. Claude API 분석 생성
    print("[5/5] Claude API 시황 분석 생성 중...")
    analysis = generate_analysis(index_data, stock_data, weekly_data, news)
    print(f"  헤드라인: {analysis.get('headline', '-')}")

    # 7. Discord 전송
    print("\nDiscord 전송 중...")
    send_report(index_data, stock_data, weekly_data, analysis, now)

    print(f"\n{'='*50}")
    print("보고서 발송 완료!")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[오류] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
