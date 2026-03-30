#!/usr/bin/env python3
"""
국내 증시 시황 보고서 자동 발송 시스템
매주 평일 오후 4시 KST (장 마감 후, GitHub Actions 스케줄: 07:00 UTC)
"""
import sys
from datetime import datetime
import pytz

from kr_fetcher import get_index_data, get_stock_data, get_top_volume_stocks, get_weekly_data, get_news
from kr_analyzer import generate_analysis
from kr_sender import send_report
from kr_pdf_generator import generate_pdf


def main():
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    print(f"\n{'='*50}")
    print(f"국내 증시 시황 보고서 생성 시작")
    print(f"실행 시각: {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*50}\n")

    # 1. 주요 지수 데이터
    print("[1/5] 주요 지수 데이터 수집 중...")
    index_data = get_index_data()
    print(f"  수집 완료: {list(index_data.keys())}")

    # 2. 거래량 상위 종목 탐색 (삼성전자 고정 포함)
    print("[2/5] 거래량 상위 종목 탐색 중...")
    top_stocks = get_top_volume_stocks(n=7, exclude=['005930.KS'])
    all_tickers = ['005930.KS'] + top_stocks  # 삼성전자 항상 포함
    print(f"  종목 확정: {all_tickers}")

    # 3. 종목 데이터
    print("[3/5] 종목 데이터 수집 중...")
    stock_data = get_stock_data(all_tickers)
    print(f"  수집 완료: {list(stock_data.keys())}")

    # 4. 주간 성과 데이터
    print("[4/5] 주간 성과 데이터 수집 중...")
    weekly_tickers = ['^KS11', '^KQ11', '^KS200']
    weekly_data = get_weekly_data(weekly_tickers)

    # 5. 뉴스 수집
    print("[4.5/5] 뉴스 수집 중...")
    news = get_news(max_items=12)
    print(f"  뉴스 {len(news)}건 수집 완료")

    # 6. Claude API 분석 생성
    print("[5/5] Claude API 시황 분석 생성 중...")
    analysis = generate_analysis(index_data, stock_data, weekly_data, news)
    print(f"  헤드라인: {analysis.get('headline', '-')}")

    # 6.5 이슈 종목 데이터 추가 수집
    issue_tickers = analysis.get('issue_tickers', [])
    if issue_tickers:
        print(f"  이슈 종목 추가 수집: {issue_tickers}")
        issue_data = get_stock_data(issue_tickers)
        for ticker, data in issue_data.items():
            if ticker not in stock_data:
                stock_data[ticker] = data

    # 7. PDF 생성
    print("\nPDF 생성 중...")
    try:
        pdf_bytes = generate_pdf(index_data, stock_data, weekly_data, analysis, now)
        print(f"  PDF 생성 완료 ({len(pdf_bytes):,} bytes)")
    except Exception as e:
        print(f"  PDF 생성 실패 (Discord 텍스트만 전송): {e}")
        pdf_bytes = None

    # 8. Discord 전송
    print("Discord 전송 중...")
    send_report(index_data, stock_data, weekly_data, analysis, now, pdf_bytes=pdf_bytes)

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
