/* Financial ratios derived only from the published SEC dataset. */
function renderAnalysis(dataset) {
  const status = document.getElementById('status');
  const cards = document.getElementById('analysis-cards');
  const chartArea = document.getElementById('analysis-charts');
  const table = document.getElementById('analysis-table');
  const annual = sorted(dataset.annual);
  const half = sorted(dataset.half_year);
  const quarterly = sorted(dataset.quarterly);
  if (!annual.length && !half.length && !quarterly.length) {
    status.hidden = false;
    status.textContent = 'SEC 원자료가 아직 수집되지 않았습니다. 아래 표와 분석은 첫 수집이 성공하면 자동으로 표시됩니다.';
    cards.innerHTML = '<article class="card"><h2>분석 대기 중</h2><p class="small">현재 저장소 데이터는 비어 있습니다.</p></article>';
    table.innerHTML = '<tbody><tr><td class="empty">분석 가능한 수치가 없습니다.</td></tr></tbody>';
    return;
  }
  status.hidden = true;
  const q = quarterly[0] || {};
  const a = annual[0] || {};
  const prevQ = priorYear(quarterly, q);
  const prevA = priorYear(annual, a);
  const items = [
    ['최근 분기 매출 성장률', growth(q.revenue, prevQ?.revenue), q.end, '동일 분기 전년 대비'],
    ['최근 연간 매출 성장률', growth(a.revenue, prevA?.revenue), a.end, '회계연도 전년 대비'],
    ['최근 분기 매출총이익률', ratio(q.gross_profit, q.revenue), q.end, '매출총이익 ÷ 매출'],
    ['최근 분기 영업이익률', ratio(q.operating_income, q.revenue), q.end, '영업이익 ÷ 매출'],
    ['최근 분기 순이익률', ratio(q.net_income, q.revenue), q.end, '순이익 ÷ 매출'],
    ['최근 분기 잉여현금흐름률', ratio(q.free_cash_flow, q.revenue), q.end, '잉여현금흐름 ÷ 매출'],
    ['최근 연간 현금전환율', ratio(a.operating_cash_flow, a.net_income), a.end, '영업현금흐름 ÷ 순이익'],
    ['최근 연간 자본적지출률', ratio(a.capex, a.revenue), a.end, '자본적지출 ÷ 매출'],
    ['최근 연간 연구개발비율', ratio(a.research_and_development, a.revenue), a.end, '연구개발비 ÷ 매출'],
    ['최근 연간 EPS 성장률', growth(a.eps_diluted, prevA?.eps_diluted), a.end, '희석 EPS 전년 대비'],
    ['부채비율 (자산 대비)', ratio(q.liabilities ?? a.liabilities, q.assets ?? a.assets), q.end || a.end, '부채총계 ÷ 자산총계'],
    ['현금 대비 부채', ratio(q.cash ?? a.cash, q.liabilities ?? a.liabilities), q.end || a.end, '현금 및 현금성자산 ÷ 부채총계'],
    ['유동비율', ratio(q.current_assets ?? a.current_assets, q.current_liabilities ?? a.current_liabilities), q.end || a.end, '유동자산 ÷ 유동부채']
  ].filter(x => x[1] != null && Number.isFinite(x[1]));
  cards.innerHTML = items.map(([label, value, end, note]) =>
    `<article class="card"><div class="small">${label}</div><strong class="${value < 0 ? 'negative' : ''}">${pct(value)}</strong><p class="small">${end || '—'} · ${note}</p></article>`
  ).join('') || '<article class="card"><h2>계산 가능한 지표가 없습니다</h2></article>';

  const series = [
    ['연간 수익성 추이', annual.slice(0, 10).reverse(), [
      ['매출총이익률', 'gross_profit', '#3767e8'],
      ['영업이익률', 'operating_income', '#18a7a1'],
      ['순이익률', 'net_income', '#a376d2']
    ]],
    ['분기 성장률 추이', quarterly.slice(0, 16).reverse(), [
      ['매출 성장률', 'revenue', '#3767e8'],
      ['순이익 성장률', 'net_income', '#18a7a1']
    ]]
  ];
  chartArea.innerHTML = series.map((s, i) => `<article class="card"><h2>${s[0]}</h2><div class="small">${i ? '동일 분기 전년 대비' : '매출 대비 비율'} · %</div><div class="chartbox"><canvas id="analysis-chart-${i}"></canvas></div></article>`).join('');
  if (window.Chart) series.forEach(([title, rows, metrics], i) => {
    if (!rows.length) return;
    const full = i ? quarterly : annual;
    new Chart(document.getElementById(`analysis-chart-${i}`), {
      type: 'line',
      data: {
        labels: rows.map(r => r.end || r.period),
        datasets: metrics.map(([label, field, color]) => ({
          label, data: rows.map(r => i ? growth(r[field], priorYear(full, r)?.[field]) : ratio(r[field], r.revenue)),
          borderColor: color, backgroundColor: color, spanGaps: false, tension: .25
        }))
      },
      options: {maintainAspectRatio:false, plugins:{legend:{position:'bottom'}}, scales:{y:{ticks:{callback:v=>v+'%'}},x:{grid:{display:false}}}}
    });
  });

  const rows = [
    ...annual.slice(0, 8).map(r => derived('연간', r, priorYear(annual, r))),
    ...half.slice(0, 8).map(r => derived('반기', r, priorYear(half, r))),
    ...quarterly.slice(0, 12).map(r => derived('분기', r, priorYear(quarterly, r)))
  ];
  const cols = [['kind','구분'], ['period','기간'], ['revenue_growth','매출 성장률'], ['net_growth','순이익 성장률'], ['gross_margin','매출총이익률'], ['operating_margin','영업이익률'], ['net_margin','순이익률'], ['fcf_margin','잉여현금흐름률'], ['cash_conversion','현금전환율'], ['research_intensity','연구개발비율'], ['liabilities_assets','부채/자산'], ['current_ratio','유동비율']];
  table.innerHTML = `<thead><tr>${cols.map(([, label])=>`<th>${label}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(([key])=>`<td>${key === 'kind' || key === 'period' ? escapeHtml(r[key]) : pct(r[key])}</td>`).join('')}</tr>`).join('')}</tbody>`;
}
function sorted(rows) { return [...(rows || [])].sort((a,b)=>(b.end || '').localeCompare(a.end || '')); }
function ratio(a,b) { return a == null || b == null || Number(b) === 0 ? null : 100 * Number(a) / Number(b); }
function growth(a,b) { return b == null || Number(b) === 0 || a == null ? null : 100 * (Number(a) / Number(b) - 1); }
function priorYear(rows, row) {
  if (!row?.end) return null;
  const target = Date.parse(row.end);
  return rows.filter(x => x !== row && x.end && Math.abs((target - Date.parse(x.end)) / 86400000 - 365) <= 35)
    .sort((a,b)=>Math.abs((target-Date.parse(a.end))/86400000-365)-Math.abs((target-Date.parse(b.end))/86400000-365))[0] || null;
}
function derived(kind, r, p) {
  return {kind, period:r.period || r.end || '—', revenue_growth:growth(r.revenue,p?.revenue), net_growth:growth(r.net_income,p?.net_income), gross_margin:ratio(r.gross_profit,r.revenue), operating_margin:ratio(r.operating_income,r.revenue), net_margin:ratio(r.net_income,r.revenue), fcf_margin:ratio(r.free_cash_flow,r.revenue), cash_conversion:ratio(r.operating_cash_flow,r.net_income), research_intensity:ratio(r.research_and_development,r.revenue), liabilities_assets:ratio(r.liabilities,r.assets), current_ratio:ratio(r.current_assets,r.current_liabilities)};
}
function pct(v) { return v == null || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`; }
function escapeHtml(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
