"""
Claude API를 사용한 국내 증시 시황 분석 생성 모듈
"""
import anthropic
import json
import os

from kr_fetcher import INDICES, TICKER_NAMES


def generate_analysis(index_data, stock_data, weekly_data, news):
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    # 지수 요약
    index_lines = []
    for ticker, d in index_data.items():
        index_lines.append(f"- {d['name']}: {d['close']:,.2f} ({d['pct']:+.2f}%, {d['change']:+.0f}pt)")
    index_summary = "\n".join(index_lines)

    # 종목 요약
    stock_lines = []
    for ticker, d in stock_data.items():
        name = d.get('name', ticker)
        vol_str = f"{d['volume'] / 1_000_000:.1f}M주" if d['volume'] >= 1_000_000 else f"{d['volume']:,}주"
        stock_lines.append(f"- {name}({ticker}): {d['close']:,.0f}원 ({d['pct']:+.2f}%), 거래량 {vol_str}")
    stock_summary = "\n".join(stock_lines)

    # 주간 수익률
    weekly_label_map = {'^KS11': '코스피', '^KQ11': '코스닥', '^KS200': '코스피200'}
    weekly_lines = []
    for ticker, pct in weekly_data.items():
        label = weekly_label_map.get(ticker, TICKER_NAMES.get(ticker, ticker))
        weekly_lines.append(f"- {label}: {pct:+.2f}%")
    weekly_summary = "\n".join(weekly_lines) if weekly_lines else "데이터 없음"

    # 뉴스
    news_text = "\n".join(news) if news else "뉴스 피드 없음"

    prompt = f"""당신은 국내 증시 전문 애널리스트입니다. 아래 데이터를 분석하여 한국 투자자를 위한 시황 보고서를 작성해주세요.

## 당일 시장 데이터

### 주요 지수 (장 마감 기준)
{index_summary}

### 주요 종목 현황
{stock_summary}

### 주간 성과 (최근 5거래일)
{weekly_summary}

### 국내 금융 뉴스 헤드라인
{news_text}

## 작성 지침
아래 JSON 형식으로 정확히 응답해주세요. JSON 외 다른 텍스트는 포함하지 마세요.

{{
  "headline": "오늘 국내 시장을 대표하는 한 줄 요약 (20자 이내, 예: '코스피 반등 성공·외국인 순매수 전환')",
  "issues": [
    {{
      "title": "이슈 제목 (이모지 포함, 15자 이내)",
      "content": "핵심 내용 2~3문장. 구체적 수치와 원인 포함."
    }}
  ],
  "outlook": [
    {{
      "title": "주목 포인트 제목 (이모지 포함)",
      "content": "향후 주목해야 할 내용 1~2문장."
    }}
  ],
  "sentiment": {{
    "label": "공포 지배 또는 하락 우세 또는 중립 관망 또는 상승 기대 또는 강세 지속 중 하나만 선택",
    "summary": "전체 시장 분위기 2~3문장 요약."
  }},
  "key_message": "국내 투자자를 위한 오늘의 핵심 메시지 1문장.",
  "issue_tickers": ["TICKER1.KS", "TICKER2.KS"]
}}

규칙:
- issues 정확히 4개, outlook 정확히 4개
- issue_tickers: 오늘 뉴스/시황에서 가장 주목받은 국내 주식 티커 1~2개 (yfinance 형식, 예: ["005930.KS", "000660.KS"]). 없으면 빈 배열 []
- 실제 뉴스/수치 기반 작성. 뉴스 없으면 지수 움직임 기반으로 합리적 추론
- 환율, 외국인/기관 수급, 섹터별 동향, 미국 증시 영향 등 국내 시장 특성 반영
- 한국어로 작성
- JSON만 출력, 코드블록(```) 없이"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    try:
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError as e:
        print(f"  [kr_analyzer] JSON 파싱 오류: {e}\n  Raw: {raw[:200]}")

    # 폴백
    return {
        "headline": "국내 시장 데이터 분석 완료",
        "issues": [
            {"title": "📊 지수 동향", "content": index_summary or "데이터 처리 중"},
            {"title": "📈 종목 현황", "content": stock_summary or "데이터 처리 중"},
            {"title": "🔍 뉴스 동향", "content": news[0] if news else "뉴스 없음"},
            {"title": "⚠️ 분석 오류", "content": "상세 분석 생성 중 오류가 발생했습니다."},
        ],
        "outlook": [
            {"title": "📌 추후 업데이트", "content": "분석을 재시도합니다."} for _ in range(4)
        ],
        "sentiment": {"label": "중립 관망", "summary": "분석 생성 중 오류가 발생했습니다."},
        "key_message": "오늘의 시황 분석을 완료하지 못했습니다. 로그를 확인해주세요.",
        "issue_tickers": [],
    }
