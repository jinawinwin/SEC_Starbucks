<p align="center"><a href="https://jinawinwin.github.io/SEC_Starbucks/"><img src="assets/dashboard-badge.svg" alt="🔗 대시보드 바로가기" width="320"></a></p>

# Starbucks SEC 재무 분석 대시보드

SEC EDGAR에 제출된 Starbucks Corporation 공시 데이터를 수집하고 연간·반기·분기 실적과 주요 재무비율을 시각화합니다.

## 자동 업데이트

GitHub Actions는 매월 5일 00:00 UTC (한국시간 09:00)에 SEC Company Facts API를 조회해 원자료와 정제 데이터를 저장하고 GitHub Pages를 배포합니다. SEC의 요청 정책에 맞는 연락 이메일을 저장소 **Settings → Secrets and variables → Actions**에서 `SEC_CONTACT_EMAIL` secret으로 등록하세요. 이메일은 코드나 로그에 노출하지 않습니다. 설정 후 **Actions → Update Starbucks SEC dashboard → Run workflow**로 첫 수집과 배포를 시작할 수 있습니다.

- 원자료: `data/companyfacts.json` (SEC Company Facts JSON)
- 분석 데이터: `data/financials.json` (USD millions, EPS in USD)
- 수집기: `scripts/update_data.py`
- 수치의 출처: [SEC Company Facts API](https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json), [Starbucks SEC filings](https://www.sec.gov/edgar/browse/?CIK=829224&owner=exclude)

반기 수치는 6개월 누적 공시를 우선 사용하고, 해당 값이 없으면 두 분기 합으로 계산합니다. 분기 수치는 분기 공시를 우선하며, 4분기는 연간 누계에서 앞선 분기 누계를 차감해 산출합니다. 공시·XBRL 태그에 값이 없는 항목은 추정하지 않습니다. 회사 회계연도와 달력연도가 다르므로 기간 표기를 함께 확인하세요.

## 분석 지표

매출·매출총이익·영업이익·순이익, EPS, 현금·자산·부채, 영업현금흐름과 자본지출을 표시합니다. 매출/이익 성장률, 매출총이익률, 영업이익률, 순이익률, 잉여현금흐름률, 현금전환율, 부채/자산 비율도 공시 수치에서 계산합니다. 대시보드 오른쪽 메뉴에서 화면을 인쇄하거나 PDF로 저장하고, 기간을 선택해 Excel 파일로 받을 수 있습니다.

## Global Peer Firms

| 기업 | 종목 코드 | 지역 | 비교 관점 |
|---|---|---|---|
| McDonald's Corporation | MCD | 미국 / 글로벌 | 대규모 글로벌 외식 브랜드 및 가맹 모델 |
| Restaurant Brands International | QSR | 캐나다 / 글로벌 | Tim Hortons, Burger King 등 다국가 QSR 브랜드 |
| Yum! Brands, Inc. | YUM | 미국 / 글로벌 | KFC, Pizza Hut, Taco Bell 등 글로벌 브랜드 운영 |
| Domino's Pizza, Inc. | DPZ | 미국 / 글로벌 | 국제 매장망을 가진 글로벌 외식 체인 |
| Dutch Bros Inc. | BROS | 미국 | 음료 중심 전문점 운영 및 매장 성장 |
| Nestlé S.A. | NESN (SIX) | 스위스 / 글로벌 | 글로벌 커피·음료 및 소비재 사업 |
| JDE Peet's N.V. | JDEP (Euronext Amsterdam) | 네덜란드 / 글로벌 | 커피 중심 글로벌 브랜드 제품 사업 |

Peer firms는 사업·브랜드 참고 대상이며 직접적인 회계 비교군은 아닙니다. 가맹 비중, 제품 포트폴리오, 회계연도와 보고 기준의 차이를 고려해야 합니다. 대시보드에는 기업 링크와 선정 이유를 함께 제공합니다.

