let selectedExchange = "NSE";
let currentSymbol = "";
let chart = null;
let candleSeries = null;
let volumeSeries = null;

document.querySelectorAll(".exchange").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".exchange").forEach(x => x.classList.remove("active"));
  btn.classList.add("active");
  selectedExchange = btn.dataset.exchange;
}));

document.getElementById("clearPrefs").addEventListener("click", () => {
  document.querySelectorAll("[data-pref]").forEach(x => x.checked = false);
});

function money(n) {
  return new Intl.NumberFormat("en-IN", {style:"currency", currency:"INR", maximumFractionDigits:2}).format(n);
}
function compact(n) {
  if (!n) return "—";
  return Intl.NumberFormat("en-IN", {notation:"compact", maximumFractionDigits:1}).format(n);
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function renderCard(s, index) {
  const up = s.change_pct >= 0;
  return `<article class="stock-card" style="animation-delay:${index*45}ms">
    <div class="stock-head"><div><div class="stock-name">${escapeHtml(s.symbol)}</div><div class="stock-meta">${escapeHtml(s.exchange)} · ${escapeHtml(s.ticker)} · ${escapeHtml(s.date)}</div></div>
    <span class="trend-pill ${s.trend==="Bullish"?"up":"down"}">${s.trend==="Bullish"?"↗":"↘"} ${s.trend}</span></div>
    <div class="stock-price-row"><div class="stock-price">${money(s.price)}</div><div class="stock-change ${up?"up":"down"}">${up?"+":""}${s.change_pct}% (${up?"+":""}${money(s.change)})</div></div>
    <div class="stock-metrics">
      <div><div class="metric-label">RSI (14)</div><div class="metric-value">${s.rsi ?? "—"}</div></div>
      <div><div class="metric-label">MACD BIAS</div><div class="metric-value">${s.macd_signal}</div></div>
      <div><div class="metric-label">VOLUME</div><div class="metric-value">${compact(s.volume)}</div></div>
    </div>
    <div class="stock-bottom"><div class="pattern">PATTERN · ${escapeHtml(s.pattern)}</div><button class="view-btn" data-symbol="${escapeHtml(s.symbol)}">VIEW CHART ↗</button></div>
  </article>`;
}

async function runScan() {
  const btn = document.getElementById("scanBtn");
  const message = document.getElementById("message");
  const resultsEl = document.getElementById("results");
  const errorsEl = document.getElementById("errors");
  const symbols = document.getElementById("symbols").value.split(",").map(x => x.trim()).filter(Boolean);
  if (!symbols.length) {
    message.textContent = "Please enter at least one stock symbol.";
    return;
  }
  btn.disabled = true;
  btn.querySelector("span").textContent = "SCANNING…";
  message.classList.remove("hidden");
  message.textContent = "Fetching market history and calculating technical indicators…";
  resultsEl.innerHTML = "";
  errorsEl.textContent = "";
  const preferences = {};
  document.querySelectorAll("[data-pref]").forEach(x => preferences[x.dataset.pref] = x.checked);
  try {
    const response = await fetch("/api/scan", {method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({symbols, exchange:selectedExchange, preferences})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan failed.");
    document.getElementById("resultCount").textContent = data.count;
    document.getElementById("updated").textContent = `UPDATED ${data.updated} · ${selectedExchange}`;
    if (data.results.length) {
      message.classList.add("hidden");
      resultsEl.innerHTML = data.results.map(renderCard).join("");
      resultsEl.querySelectorAll(".view-btn").forEach(b => b.addEventListener("click", () => openChart(b.dataset.symbol)));
    } else {
      message.classList.remove("hidden");
      message.textContent = data.errors.length ? "No matching stocks returned. Check the symbols or filters below." : "No stocks match the selected preferences. Clear some filters and scan again.";
    }
    if (data.errors.length) errorsEl.innerHTML = data.errors.map(e => `${escapeHtml(e.ticker)}: ${escapeHtml(e.error)}`).join("<br>");
    if (data.notice) errorsEl.innerHTML += `<div style="color:#72869e;margin-top:8px">${escapeHtml(data.notice)}</div>`;
  } catch (err) {
    message.classList.remove("hidden");
    message.textContent = err.message || "Unable to complete scan. Is the Flask server running?";
  } finally {
    btn.disabled = false;
    btn.querySelector("span").textContent = "SCAN STOCKS";
  }
}
document.getElementById("scanBtn").addEventListener("click", runScan);
document.getElementById("symbols").addEventListener("keydown", e => { if (e.key === "Enter") runScan(); });

async function openChart(symbol, interval="1d") {
  currentSymbol = symbol;
  document.getElementById("chartTitle").textContent = symbol;
  document.getElementById("chartExchange").textContent = selectedExchange;
  document.getElementById("chartModal").classList.remove("hidden");
  document.getElementById("chartError").textContent = "";
  document.getElementById("chartNotice").textContent = "Loading historical candles…";
  document.querySelectorAll(".tf").forEach(b => b.classList.toggle("active", b.dataset.interval === interval));
  await loadChart(interval);
}
async function loadChart(interval) {
  const container = document.getElementById("chartContainer");
  if (chart) { chart.remove(); chart = null; candleSeries = null; volumeSeries = null; }
  container.innerHTML = "";
  try {
    const response = await fetch(`/api/chart/${selectedExchange}/${encodeURIComponent(currentSymbol)}?interval=${interval}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Chart data unavailable.");
    chart = LightweightCharts.createChart(container, {
      width:container.clientWidth, height:container.clientHeight,
      layout:{background:{type:"solid",color:"#0d1726"},textColor:"#91a4ba"},
      grid:{vertLines:{color:"#1b2a3c"},horzLines:{color:"#1b2a3c"}},
      rightPriceScale:{borderColor:"#29394c"}, timeScale:{borderColor:"#29394c",timeVisible:true},
      crosshair:{mode:LightweightCharts.CrosshairMode.Normal}
    });
    candleSeries = chart.addCandlestickSeries({
      upColor:"#42e6bd",downColor:"#ff7188",borderUpColor:"#42e6bd",borderDownColor:"#ff7188",
      wickUpColor:"#42e6bd",wickDownColor:"#ff7188"
    });
    candleSeries.setData(data.candles);
    volumeSeries = chart.addHistogramSeries({priceFormat:{type:"volume"},priceScaleId:""});
    volumeSeries.priceScale().applyOptions({scaleMargins:{top:.82,bottom:0}});
    volumeSeries.setData(data.candles.map(c => ({time:c.time,value:c.volume,color:c.close>=c.open?"#42e6bd66":"#ff718866"})));
    chart.timeScale().fitContent();
    new ResizeObserver(() => { if(chart) chart.applyOptions({width:container.clientWidth,height:container.clientHeight}); }).observe(container);
    document.getElementById("chartNotice").textContent = `${data.candles.length} candles · ${interval.toUpperCase()} · Historical data`;
  } catch(err) {
    document.getElementById("chartError").textContent = err.message;
    document.getElementById("chartNotice").textContent = "Chart unavailable";
  }
}
document.querySelectorAll(".tf").forEach(b => b.addEventListener("click", () => loadChart(b.dataset.interval)));
function closeChart() {
  document.getElementById("chartModal").classList.add("hidden");
  if (chart) { chart.remove(); chart = null; }
}
document.getElementById("closeChart").addEventListener("click", closeChart);
document.getElementById("modalBackdrop").addEventListener("click", closeChart);
document.addEventListener("keydown", e => { if(e.key==="Escape") closeChart(); });
