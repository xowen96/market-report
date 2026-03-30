"""
Discord Webhook으로 시황 보고서 전송 모듈
"""
import requests
import json
import os
from datetime import datetime


# Discord embed 색상
COLOR_UP = 0x2ECC71       # 초록 (상승)
COLOR_DOWN = 0xE74C3C     # 빨강 (하락)
COLOR_NEUTRAL = 0x95A5A6  # 회색 (보합)
COLOR_BLUE = 0x3498DB     # 파랑 (헤더)
COLOR_ORANGE = 0xE67E22   # 주황 (이슈)

INDEX_NAMES_KR = {
    '^NDX': '나스닥 100',
    '^GSPC': 'S&P 500',
    '^DJI': '다우존스',
    '^RUT': '러셀 2000',
}


def _pct_color(pct):
    if pct > 0:
        return COLOR_UP
    elif pct < 0:
        return COLOR_DOWN
    return COLOR_NEUTRAL


def _arrow(pct):
    return "▲" if pct > 0 else "▼" if pct < 0 else "━"


def _fmt_pct(pct, change=None):
    base = f"{_arrow(pct)} {abs(pct):.2f}%"
    if change is not None:
        base += f" ({change:+.2f})"
    return base


def _fmt_vol(volume):
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M주"
    elif volume >= 1_000:
        return f"{volume / 1_000:.0f}K주"
    return f"{volume:,}주"


def send_report(index_data, stock_data, weekly_data, analysis, report_time, pdf_bytes=None):
    webhook_url = os.environ['DISCORD_WEBHOOK_URL_US']

    date_str = report_time.strftime('%Y년 %m월 %d일')
    weekday_kr = ['월', '화', '수', '목', '금', '토', '일'][report_time.weekday()]
    time_str = report_time.strftime(f'%H:%M KST ({weekday_kr})')

    headline = analysis.get('headline', '미국 증시 시황')

    # 전체 시장 색상 기준: S&P 500
    sp = index_data.get('^GSPC', {})
    main_color = _pct_color(sp.get('pct', 0))

    embeds = []

    # ── Embed 1: 헤더 + 주요 지수 ──────────────────────────────────
    index_fields = []
    for ticker, d in index_data.items():
        value = (
            f"**{d['close']:,.2f}**\n"
            f"{_fmt_pct(d['pct'], d['change'])}"
        )
        index_fields.append({"name": d['name'], "value": value, "inline": True})

    embeds.append({
        "title": "📊 미국 증시 시황 보고서",
        "description": f"**{date_str} 마감 기준**  ·  {time_str}\n\n> **{headline}**",
        "color": main_color,
        "fields": index_fields,
    })

    # ── Embed 2: 주요 종목 현황 ──────────────────────────────────────
    stock_fields = []
    for ticker, d in stock_data.items():
        value = (
            f"**${d['close']}**\n"
            f"{_fmt_pct(d['pct'], d['change'])}\n"
            f"거래량 {_fmt_vol(d['volume'])}"
        )
        stock_fields.append({"name": ticker, "value": value, "inline": True})

    embeds.append({
        "title": "📈 주요 종목 현황",
        "color": COLOR_BLUE,
        "fields": stock_fields,
    })

    # ── Embed 3: 핵심 경제 이슈 ─────────────────────────────────────
    issues = analysis.get('issues', [])
    issues_lines = []
    for issue in issues:
        issues_lines.append(f"**{issue['title']}**\n{issue['content']}")
    issues_text = "\n\n".join(issues_lines)

    embeds.append({
        "title": "🔍 핵심 경제 이슈",
        "description": issues_text[:4000],
        "color": COLOR_ORANGE,
    })

    # ── Embed 4: 향후 흐름 및 주목 포인트 ──────────────────────────
    outlook = analysis.get('outlook', [])
    outlook_lines = []
    for item in outlook:
        outlook_lines.append(f"**{item['title']}**\n{item['content']}")
    outlook_text = "\n\n".join(outlook_lines)

    embeds.append({
        "title": "🔭 향후 흐름 및 주목 포인트",
        "description": outlook_text[:4000],
        "color": COLOR_BLUE,
    })

    # ── Embed 5: 주간 성과 + 시장 분위기 ───────────────────────────
    weekly_lines = []
    weekly_label_map = {'^NDX': '나스닥 100', '^GSPC': 'S&P 500', 'QLD': 'QLD', 'NVDL': 'NVDL'}
    for ticker, pct in weekly_data.items():
        label = weekly_label_map.get(ticker, ticker)
        weekly_lines.append(f"**{label}**: {_fmt_pct(pct)}")
    weekly_text = "\n".join(weekly_lines) if weekly_lines else "데이터 없음"

    sentiment = analysis.get('sentiment', {})
    key_msg = analysis.get('key_message', '')

    embeds.append({
        "title": "📅 주간 성과 요약",
        "description": weekly_text,
        "color": _pct_color(weekly_data.get('^GSPC', 0)),
        "fields": [
            {
                "name": f"시장 분위기: **{sentiment.get('label', '-')}**",
                "value": sentiment.get('summary', '-')[:1000],
                "inline": False,
            },
            {
                "name": "💡 핵심 메시지",
                "value": key_msg[:1000] if key_msg else "-",
                "inline": False,
            },
        ],
        "footer": {
            "text": "투자 권유 아님  |  출처: Yahoo Finance · RSS · Claude AI"
        },
    })

    payload = {
        "username": "미국 증시 시황봇",
        "embeds": embeds,
    }

    if pdf_bytes:
        # PDF 파일과 함께 전송 (multipart)
        filename = f"시황보고서_{report_time.strftime('%Y%m%d')}.pdf"
        files = {
            'payload_json': (None, json.dumps(payload), 'application/json'),
            'file': (filename, pdf_bytes, 'application/pdf'),
        }
        resp = requests.post(webhook_url, files=files, timeout=30)
    else:
        resp = requests.post(webhook_url, json=payload, timeout=10)

    if resp.status_code in (200, 204):
        print("  [sender] Discord 전송 성공!")
    else:
        print(f"  [sender] Discord 전송 실패: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
