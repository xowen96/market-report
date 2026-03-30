"""
국내 증시 시황 보고서 PDF 생성 모듈 (fpdf2 사용)
한국어 폰트: NanumGothic (GitHub Actions에서 fonts-nanum 패키지로 설치)
"""
import os
from fpdf import FPDF

from kr_fetcher import TICKER_NAMES

# 폰트 경로
FONT_PATHS = [
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
    '/Library/Fonts/NanumGothic.ttf',
    '/Library/Fonts/NanumGothicBold.ttf',
]

# 색상
C_BG      = (18, 18, 18)
C_CARD    = (30, 30, 30)
C_ACCENT  = (52, 152, 219)
C_UP      = (46, 204, 113)
C_DOWN    = (231, 76, 60)
C_TEXT    = (220, 220, 220)
C_SUBTEXT = (160, 160, 160)
C_WHITE   = (255, 255, 255)
C_ORANGE  = (230, 126, 34)


def _find_font(bold=False):
    idx = 1 if bold else 0
    candidates = [FONT_PATHS[idx], FONT_PATHS[idx + 2]] if bold else [FONT_PATHS[0], FONT_PATHS[2]]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _arrow(pct):
    return '▲' if pct > 0 else '▼' if pct < 0 else '━'


def _pct_color(pct):
    if pct > 0:
        return C_UP
    elif pct < 0:
        return C_DOWN
    return C_SUBTEXT


class KrReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)

        font_regular = _find_font(bold=False)
        font_bold = _find_font(bold=True)

        if font_regular:
            self.add_font('Nanum', '', font_regular)
        if font_bold:
            self.add_font('Nanum', 'B', font_bold)

        self._has_font = bool(font_regular)

    def _set(self, bold=False, size=10, color=C_TEXT):
        style = 'B' if bold else ''
        if self._has_font:
            self.set_font('Nanum', style, size)
        else:
            self.set_font('Helvetica', style, size)
        self.set_text_color(*color)

    def _fill_bg(self):
        self.set_fill_color(*C_BG)
        self.rect(0, 0, 210, 297, 'F')

    def _card(self, x, y, w, h, color=None):
        self.set_fill_color(*(color or C_CARD))
        self.rect(x, y, w, h, 'F')

    def _section_title(self, title):
        self.ln(3)
        self.set_fill_color(*C_ACCENT)
        self.rect(15, self.get_y(), 3, 6, 'F')
        self._set(bold=True, size=11, color=C_WHITE)
        self.set_x(20)
        self.cell(0, 6, title, ln=True)
        self.ln(2)

    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self._set(size=7, color=C_SUBTEXT)
        self.cell(0, 5, '투자 권유 아님  |  출처: Yahoo Finance · RSS · Claude AI', align='C')


def generate_pdf(index_data, stock_data, weekly_data, analysis, report_time):
    pdf = KrReportPDF()
    pdf.add_page()
    pdf._fill_bg()

    weekday_kr = ['월', '화', '수', '목', '금', '토', '일'][report_time.weekday()]
    date_str = report_time.strftime(f'%Y년 %m월 %d일 ({weekday_kr})')
    time_str = report_time.strftime('%H:%M KST')
    headline = analysis.get('headline', '국내 증시 시황')

    # ── 헤더 타이틀 ──────────────────────────────────
    pdf._card(0, 0, 210, 38, C_CARD)
    pdf._set(bold=True, size=18, color=C_WHITE)
    pdf.set_xy(15, 8)
    pdf.cell(0, 10, '국내 증시 시황 보고서', ln=True)

    pdf._set(size=9, color=C_SUBTEXT)
    pdf.set_x(15)
    pdf.cell(0, 5, f'{date_str} 장 마감 기준  ·  {time_str}', ln=True)

    pdf.set_fill_color(*C_ACCENT)
    pdf.set_xy(15, pdf.get_y() + 1)
    pdf._set(bold=True, size=9, color=C_WHITE)
    pdf.cell(len(headline) * 2.5 + 6, 6, f'  {headline}  ', fill=True, ln=True)
    pdf.ln(5)

    # ── 주요 지수 ──────────────────────────────────────
    pdf._section_title('주요 지수 종가')

    indices = list(index_data.items())
    card_w = 55
    card_h = 18
    gap = 5
    start_x = 15

    for i, (ticker, d) in enumerate(indices):
        x = start_x + i * (card_w + gap)
        y = pdf.get_y()
        pdf._card(x, y, card_w, card_h)

        pdf._set(size=8, color=C_SUBTEXT)
        pdf.set_xy(x + 3, y + 2)
        pdf.cell(card_w - 6, 5, d['name'])

        pdf._set(bold=True, size=11, color=C_WHITE)
        pdf.set_xy(x + 3, y + 7)
        pdf.cell(card_w - 6, 7, f"{d['close']:,.2f}")

        pct_col = _pct_color(d['pct'])
        pdf._set(bold=True, size=9, color=pct_col)
        pdf.set_xy(x + 3, y + 13)
        pdf.cell(card_w - 6, 5, f"{_arrow(d['pct'])} {abs(d['pct']):.2f}%")

    pdf.ln(card_h + 6)

    # ── 주요 종목 ──────────────────────────────────────
    pdf._section_title('주요 종목 현황')

    headers = ['종목명', '종가(원)', '등락', '등락률', '거래량']
    col_w = [35, 28, 22, 22, 28]
    row_h = 7

    pdf.set_fill_color(*C_ACCENT)
    pdf.set_x(15)
    for h, w in zip(headers, col_w):
        pdf._set(bold=True, size=8, color=C_WHITE)
        pdf.set_fill_color(*C_ACCENT)
        pdf.cell(w, row_h, h, border=0, fill=True, align='C')
    pdf.ln()

    for i, (ticker, d) in enumerate(stock_data.items()):
        row_color = (35, 35, 35) if i % 2 == 0 else (28, 28, 28)
        pdf.set_fill_color(*row_color)
        pdf.set_x(15)

        name = d.get('name', TICKER_NAMES.get(ticker, ticker))
        vol_str = f"{d['volume']/1_000_000:.1f}M" if d['volume'] >= 1_000_000 else f"{d['volume']/1_000:.0f}K"
        pct_col = _pct_color(d['pct'])

        pdf._set(bold=True, size=8, color=C_WHITE)
        pdf.cell(col_w[0], row_h, name[:8], fill=True, align='L')

        pdf._set(size=8, color=C_TEXT)
        pdf.cell(col_w[1], row_h, f"{d['close']:,.0f}", fill=True, align='R')

        pdf._set(size=8, color=pct_col)
        pdf.cell(col_w[2], row_h, f"{d['change']:+,.0f}", fill=True, align='R')
        pdf.cell(col_w[3], row_h, f"{_arrow(d['pct'])} {abs(d['pct']):.2f}%", fill=True, align='C')

        pdf._set(size=8, color=C_SUBTEXT)
        pdf.cell(col_w[4], row_h, vol_str, fill=True, align='R')
        pdf.ln()

    pdf.ln(4)

    # ── 핵심 경제 이슈 ─────────────────────────────────
    pdf._section_title('핵심 경제 이슈')

    issues = analysis.get('issues', [])
    for issue in issues:
        if pdf.get_y() > 250:
            pdf.add_page()
            pdf._fill_bg()

        y_start = pdf.get_y()
        pdf._card(15, y_start, 180, 4, C_CARD)

        pdf._set(bold=True, size=9, color=C_ORANGE)
        pdf.set_xy(18, y_start + 2)
        pdf.cell(0, 5, issue['title'], ln=True)

        pdf._set(size=8, color=C_TEXT)
        pdf.set_x(18)
        pdf.multi_cell(174, 4.5, issue['content'])
        pdf.ln(2)

    # ── 향후 흐름 ──────────────────────────────────────
    if pdf.get_y() > 230:
        pdf.add_page()
        pdf._fill_bg()

    pdf._section_title('향후 흐름 및 주목 포인트')

    outlook = analysis.get('outlook', [])
    for item in outlook:
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf._fill_bg()

        pdf._set(bold=True, size=9, color=C_ACCENT)
        pdf.set_x(15)
        pdf.cell(4, 5, '▸')
        pdf.set_x(20)
        pdf.cell(0, 5, item['title'], ln=True)

        pdf._set(size=8, color=C_TEXT)
        pdf.set_x(20)
        pdf.multi_cell(172, 4.5, item['content'])
        pdf.ln(1)

    # ── 2페이지: 주간 성과 + 시장 분위기 ──────────────
    pdf.add_page()
    pdf._fill_bg()

    pdf._section_title('주간 성과 요약 (최근 5거래일)')

    weekly_labels = {'^KS11': '코스피', '^KQ11': '코스닥', '^KS200': '코스피200'}
    for ticker, pct in weekly_data.items():
        label = weekly_labels.get(ticker, TICKER_NAMES.get(ticker, ticker))
        y = pdf.get_y()
        pdf._card(15, y, 180, 10)

        pdf._set(bold=True, size=9, color=C_TEXT)
        pdf.set_xy(18, y + 2)
        pdf.cell(80, 6, label)

        pct_col = _pct_color(pct)
        pdf._set(bold=True, size=10, color=pct_col)
        pdf.set_xy(100, y + 2)
        pdf.cell(0, 6, f'{_arrow(pct)} {abs(pct):.2f}%')
        pdf.ln(13)

    pdf.ln(4)
    pdf._section_title('시장 분위기 종합')

    sentiment = analysis.get('sentiment', {})
    key_msg = analysis.get('key_message', '')

    pdf._card(15, pdf.get_y(), 180, 28)
    y = pdf.get_y()

    pdf._set(bold=True, size=11, color=C_WHITE)
    pdf.set_xy(18, y + 4)
    pdf.cell(0, 7, sentiment.get('label', ''), ln=True)

    pdf._set(size=9, color=C_TEXT)
    pdf.set_x(18)
    pdf.multi_cell(174, 5, sentiment.get('summary', ''))

    pdf.ln(5)
    pdf._card(15, pdf.get_y(), 180, 16)
    y = pdf.get_y()

    pdf._set(bold=True, size=9, color=C_ACCENT)
    pdf.set_xy(18, y + 3)
    pdf.cell(0, 5, '핵심 메시지', ln=True)

    pdf._set(size=9, color=C_WHITE)
    pdf.set_x(18)
    pdf.multi_cell(174, 5, key_msg)

    return bytes(pdf.output())
