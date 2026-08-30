const CLUSTER_COLORS = ["#1B1D1F", "#6E7579", "#B9BEC1", "#00C08B", "#00755C", "#A5EFD3"];

const topicInput = document.getElementById("topic-input");
const rankSelect = document.getElementById("rank-select");
const searchBtn = document.getElementById("search-btn");
const banner = document.getElementById("result-banner");
const statCluster = document.getElementById("stat-cluster");
const statCount = document.getElementById("stat-count");
const statOrgs = document.getElementById("stat-orgs");
const taskBody = document.getElementById("task-table-body");
const taskNote = document.getElementById("task-table-note");
const researcherBody = document.getElementById("researcher-table-body");
const researcherNote = document.getElementById("researcher-note");
const svg = document.getElementById("cluster-svg");
const legendEl = document.getElementById("cluster-legend");
const dupCard = document.getElementById("dup-card");
const dupSub = document.getElementById("dup-sub");
const dupCount = document.getElementById("dup-count");
const dupInst = document.getElementById("dup-inst");
const dupRes = document.getElementById("dup-res");
const dupList = document.getElementById("dup-list");

// A.2 위험도 배지
const riskCard = document.getElementById("risk-card");
const riskBadge = document.getElementById("risk-badge");
const riskReason = document.getElementById("risk-reason");
const RISK_CLASS = { "높음": "high", "중간": "mid", "낮음": "low", "판단 보류": "hold" };

// A.2 에고 그래프
const egoSvg = document.getElementById("ego-svg");
const egoLegend = document.getElementById("ego-legend");

// A.3 지역 기술편중
const regionRatio = document.getElementById("region-ratio");
const regionRatioSub = document.getElementById("region-ratio-sub");
const regionDonut = document.getElementById("region-donut");
const regionDist = document.getElementById("region-dist");
const regionDistEmpty = document.getElementById("region-dist-empty");
const regionConcBody = document.getElementById("region-conc-body");
const regionScaleNote = document.getElementById("region-scale-note");
const NODE_STYLE = {
  query:      { fill: "#1B1D1F", r: 11, label: "입력 주제" },
  task:       { fill: "#00C08B", r: 7,  label: "유사 과제" },
  researcher: { fill: "#6E7579", r: 6,  label: "연구책임자" },
  subfield:   { fill: "#B9BEC1", r: 6,  label: "세부사업" },
};

let clusterPoints = [];
let xScale = (x) => x, yScale = (y) => y;

function fitScales(points) {
  const xs = points.map(p => p.x), ys = points.map(p => p.y);
  const [xMin, xMax] = [Math.min(...xs), Math.max(...xs)];
  const [yMin, yMax] = [Math.min(...ys), Math.max(...ys)];
  const pad = 40;
  xScale = (x) => pad + ((x - xMin) / (xMax - xMin || 1)) * (880 - pad * 2);
  yScale = (y) => pad + ((y - yMin) / (yMax - yMin || 1)) * (520 - pad * 2);
}

function renderClusterMap(highlight) {
  svg.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const p of clusterPoints) {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", xScale(p.x)); c.setAttribute("cy", yScale(p.y));
    c.setAttribute("r", "4"); c.setAttribute("fill", CLUSTER_COLORS[p.cluster] || "#999");
    c.setAttribute("opacity", "0.75");
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${p.과제명} | ${p.주관기관명} | ${p.특구지역} | 클러스터 ${p.cluster}`;
    c.appendChild(title);
    frag.appendChild(c);
  }
  svg.appendChild(frag);

  if (highlight) {
    const hx = xScale(highlight.x), hy = yScale(highlight.y);
    const star = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    star.setAttribute("cx", hx); star.setAttribute("cy", hy); star.setAttribute("r", "9");
    star.setAttribute("fill", "#1B1D1F"); star.setAttribute("stroke", "#fff"); star.setAttribute("stroke-width", "2");
    svg.appendChild(star);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", hx + 14); label.setAttribute("y", hy + 4);
    label.setAttribute("fill", "#1B1D1F"); label.setAttribute("font-size", "13"); label.setAttribute("font-weight", "800");
    label.textContent = `내 주제 (클러스터 ${highlight.cluster})`;
    svg.appendChild(label);
  }
}

function renderCrosstab(ct) {
  const el = document.getElementById("crosstab");
  if (!el || !ct || !ct.regions) return;
  const cols = ct.regions.length;
  el.style.gridTemplateColumns = `64px repeat(${cols}, 1fr) 56px`;
  const maxCell = Math.max(1, ...ct.matrix.flat());
  let html = `<div class="ct-h"></div>`;
  for (const r of ct.regions) html += `<div class="ct-h">${r}</div>`;
  html += `<div class="ct-h">합계</div>`;
  ct.clusters.forEach((c, ci) => {
    html += `<div class="ct-rowlabel"><span class="cluster-badge">${c}</span></div>`;
    ct.matrix[ci].forEach(v => {
      const a = v / maxCell;
      html += `<div class="ct-cell" style="background:rgba(0,192,139,${(a * 0.85).toFixed(3)});color:${a > 0.5 ? "#fff" : "#1B1D1F"}">${v || ""}</div>`;
    });
    html += `<div class="ct-cell ct-total">${ct.row_totals[ci]}</div>`;
  });
  html += `<div class="ct-rowlabel ct-total">합계</div>`;
  ct.col_totals.forEach(v => { html += `<div class="ct-cell ct-total">${v}</div>`; });
  html += `<div class="ct-cell ct-total ct-grand">${ct.grand_total}</div>`;
  el.innerHTML = html;
}

function renderLegend(nClusters) {
  legendEl.innerHTML = "";
  for (let i = 0; i < nClusters; i++) {
    const row = document.createElement("div");
    row.className = "legend-row";
    row.innerHTML = `<span class="legend-dot" style="background:${CLUSTER_COLORS[i]}"></span><span class="legend-label">클러스터 ${i}</span>`;
    legendEl.appendChild(row);
  }
}

async function loadClusters() {
  try {
    const res = await fetch("/api/clusters");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    clusterPoints = data.points;
    fitScales(clusterPoints);
    renderLegend(data.n_clusters);
    renderClusterMap(null);
    renderCrosstab(data.region_crosstab);
  } catch (e) {
    console.error("클러스터 지도를 불러오지 못했습니다.", e);
  }
}

function renderBanner(state) {
  banner.className = "";
  banner.style.display = "";
  if (state === "blank") {
    banner.textContent = "검색어를 입력해주세요.";
    banner.className = "blank";
  } else if (state === "empty_corpus") {
    banner.textContent = "특구 소속 기관이 수행한 과제 데이터가 없습니다.";
    banner.className = "blank";
  } else if (state === "reference") {
    banner.textContent = "정확히 일치하는 유사 과제를 찾지 못했습니다. 아래는 유사도가 가장 높았던 3건입니다(참고용).";
    banner.className = "reference";
  } else if (state === "error") {
    banner.textContent = "결과를 불러오지 못했습니다. 서버 상태를 확인해주세요.";
    banner.className = "blank";
  }
}

function renderTaskTable(result) {
  taskBody.innerHTML = "";
  taskNote.textContent = result.reference_only ? "참고용 상위 3건" : "유사도 상위 5건";
  for (const t of result.tasks) {
    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
      <div>${t.과제명}</div>
      <div>${t.주관기관명}</div>
      <div>${t.선정년도}</div>
      <div>${t.유사도.toFixed(3)}</div>
      <div><span class="cluster-badge">${t.클러스터}</span></div>`;
    taskBody.appendChild(row);
  }
}

function renderResearcherTable(result) {
  researcherBody.innerHTML = "";
  researcherNote.textContent = result.researchers_reference_only
    ? "참고용 — 임계값 미달"
    : `정렬 기준: ${rankSelect.value}`;
  for (const p of result.researchers) {
    const row = document.createElement("div");
    row.className = "researcher-row";
    row.innerHTML = `
      <div class="researcher-name-cell"><span class="avatar">${p.연구책임자명.slice(0, 1)}</span><span>${p.연구책임자명}</span></div>
      <div>${p.주관기관명}</div>
      <div>${p.특구지역}</div>
      <div>${p.대표유사과제명}</div>
      <div>${p.유사도.toFixed(3)}</div>
      <div>${p.과제수}</div>`;
    researcherBody.appendChild(row);
  }
}

function renderDuplicationRisk(result) {
  if (!result || !result.duplication_risk) {
    dupCard.style.display = "none";
    dupList.innerHTML = "";
    return;
  }
  dupCard.style.display = "block";
  dupSub.textContent = `유사도 높은 과제가 ${result.institution_count}개 기관에서 수행 중`;
  dupCount.textContent = result.risk_count;
  dupInst.textContent = result.institution_count;
  dupRes.textContent = result.researcher_count;
  dupList.innerHTML = "";
  for (const t of result.duplication_tasks) {
    const row = document.createElement("div");
    row.className = "dup-row";
    row.innerHTML = `
      <div>${t.과제명}</div>
      <div>${t.주관기관명}</div>
      <div>${t.선정년도}</div>
      <div>${t.유사도.toFixed(3)}</div>
      <div>${t.연구책임자명}</div>`;
    dupList.appendChild(row);
  }
}

// A.2 위험도 배지 — 화면에 이미 나온 숫자의 요약(예측 아님), 근거 문구 상시 노출
function renderRisk(rb) {
  if (!rb) { riskCard.style.display = "none"; return; }
  riskCard.style.display = "flex";
  riskBadge.className = "risk-badge " + (RISK_CLASS[rb.level] || "hold");
  riskBadge.textContent = rb.level;
  riskReason.textContent = rb.reason || "";
}

// ── A.2 에고 그래프 (바닐라 SVG 방사형 배치, 외부 라이브러리 0개) ──────────
function svgEl(name, attrs) {
  const e = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

function renderEgoLegend() {
  egoLegend.innerHTML = "";
  for (const t of ["query", "task", "researcher", "subfield"]) {
    const row = document.createElement("div");
    row.className = "legend-row";
    row.innerHTML = `<span class="legend-dot" style="background:${NODE_STYLE[t].fill}"></span><span>${NODE_STYLE[t].label}</span>`;
    egoLegend.appendChild(row);
  }
  const weak = document.createElement("div");
  weak.className = "legend-row";
  weak.innerHTML = `<span class="legend-dot" style="background:${NODE_STYLE.subfield.fill};opacity:.4"></span><span>소수 수행 사업유형 (매칭 ≤2건)</span>`;
  egoLegend.appendChild(weak);
}

function renderEgoGraph(data) {
  egoSvg.innerHTML = "";
  if (!data || data.blank_query || !data.nodes || data.nodes.length <= 1) {
    const msg = svgEl("text", { x: 440, y: 280, "text-anchor": "middle", fill: "#8B9296", "font-size": 13, "font-weight": 700 });
    msg.textContent = "검색하면 관계망이 표시됩니다.";
    egoSvg.appendChild(msg);
    return;
  }
  const CX = 440, CY = 280;
  const pos = { q: { x: CX, y: CY } };
  const angle = {};

  const tasks = data.nodes.filter(n => n.type === "task");
  tasks.forEach((n, i) => {
    const a = (i / Math.max(tasks.length, 1)) * 2 * Math.PI - Math.PI / 2;
    angle[n.id] = a;
    pos[n.id] = { x: CX + 150 * Math.cos(a), y: CY + 150 * Math.sin(a) };
  });

  // 연구자/세부사업 노드의 각도 = 연결된 과제들의 평균 각도
  const connTasks = {};
  for (const e of data.edges) {
    if (e.kind === "수행") (connTasks[e.src] = connTasks[e.src] || []).push(e.dst);   // 연구자→과제
    if (e.kind === "소속") (connTasks[e.dst] = connTasks[e.dst] || []).push(e.src);   // 과제→세부사업
  }
  const avgAngle = (id, fb) => {
    const as = (connTasks[id] || []).map(t => angle[t]).filter(a => a !== undefined);
    return as.length ? as.reduce((s, a) => s + a, 0) / as.length : fb;
  };
  let k = 0;
  for (const n of data.nodes) {
    if (n.type === "researcher") { const a = avgAngle(n.id, (k++ / data.nodes.length) * 2 * Math.PI) - 0.05; pos[n.id] = { x: CX + 255 * Math.cos(a), y: CY + 255 * Math.sin(a) }; }
    if (n.type === "subfield")   { const a = avgAngle(n.id, (k++ / data.nodes.length) * 2 * Math.PI) + 0.05; pos[n.id] = { x: CX + 255 * Math.cos(a), y: CY + 255 * Math.sin(a) }; }
  }

  const frag = document.createDocumentFragment();
  for (const e of data.edges) {
    const s = pos[e.src], d = pos[e.dst];
    if (!s || !d) continue;
    frag.appendChild(svgEl("line", { x1: s.x, y1: s.y, x2: d.x, y2: d.y, stroke: "#D8DCDE", "stroke-width": e.kind === "유사도" ? 1.5 : 0.9, opacity: 0.7 }));
  }
  for (const n of data.nodes) {
    const p = pos[n.id]; if (!p) continue;
    const st = NODE_STYLE[n.type] || NODE_STYLE.subfield;
    const weak = n.type === "subfield" && n.weak;
    const c = svgEl("circle", { cx: p.x, cy: p.y, r: st.r, fill: st.fill, opacity: weak ? 0.4 : 1, stroke: weak ? "#B9BEC1" : "#fff", "stroke-width": 1.5 });
    if (weak) c.setAttribute("stroke-dasharray", "2 2");
    const title = svgEl("title", {});
    title.textContent = `${st.label}: ${n.label}` + (weak ? " (소수 수행 사업유형 · ≤2건)" : "");
    c.appendChild(title);
    frag.appendChild(c);
    if (n.type === "query" || n.type === "task") {
      const t = svgEl("text", { x: p.x, y: p.y - st.r - 5, "text-anchor": "middle", fill: "#4A4F52", "font-size": n.type === "query" ? 12 : 10, "font-weight": n.type === "query" ? 800 : 700 });
      t.textContent = n.label.length > 14 ? n.label.slice(0, 13) + "…" : n.label;
      frag.appendChild(t);
    }
  }
  egoSvg.appendChild(frag);
}

async function loadEgoGraph(query) {
  if (!query || !query.trim()) { renderEgoGraph(null); return; }
  try {
    const res = await fetch(`/api/ego_graph?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    renderEgoGraph(await res.json());
  } catch (e) {
    console.error("에고 그래프를 불러오지 못했습니다.", e);
  }
}

// ── A.3 지역 기술편중 렌더 ─────────────────────────────────────────
function renderRegionConc(conc, note) {
  regionScaleNote.textContent = note || "";
  regionConcBody.innerHTML = "";
  for (const r of conc || []) {
    const lq = r.집중도_LQ;
    let cls = "norm", tag = "보통";
    if (lq == null) { cls = "under"; tag = "—"; }
    else if (lq >= 1.15) { cls = "over"; tag = "과집중"; }
    else if (lq < 0.85) { cls = "under"; tag = "과소"; }
    const row = document.createElement("div");
    row.className = "conc-row";
    row.innerHTML = `
      <div class="conc-name">${r.특구}</div>
      <div>${r.과제수}</div>
      <div>${r.입주기업수.toLocaleString()}</div>
      <div class="conc-lq">${lq == null ? "—" : lq.toFixed(2)}</div>
      <div><span class="conc-tag ${cls}">${tag}</span></div>`;
    regionConcBody.appendChild(row);
  }
}

function renderRegionDonut(ratio) {
  const R = 48, C = 2 * Math.PI * R, off = C * (1 - Math.max(0, Math.min(1, ratio)));
  regionDonut.innerHTML = `
    <circle cx="60" cy="60" r="48" fill="none" stroke="#F1F3F3" stroke-width="14"/>
    <circle cx="60" cy="60" r="48" fill="none" stroke="#00C08B" stroke-width="14"
      stroke-dasharray="${C}" stroke-dashoffset="${off}" stroke-linecap="round"
      transform="rotate(-90 60 60)"/>
    <text x="60" y="67" text-anchor="middle" font-size="22" font-weight="800" fill="#1B1D1F">${Math.round(ratio * 100)}%</text>`;
}

function renderRegionInline(data) {
  const card = document.getElementById("region-inline");
  const txt = document.getElementById("ri-text");
  const top3 = document.getElementById("ri-top3");
  if (!card) return;
  if (data.status === "blank_query" || data.status === "empty_corpus") { card.style.display = "none"; return; }
  card.style.display = "flex";
  top3.innerHTML = "";
  if (data.status === "reference_only") {
    txt.className = "ri-text muted";
    txt.textContent = "임계값 이상 유사 과제가 없어 특구 집계를 낼 수 없습니다.";
    return;
  }
  const total = data.total_matched, tukku = data.특구소속_matched;
  if (tukku === 0) {
    txt.className = "ri-text muted";
    txt.textContent = `전체 유사 과제 ${total}건 중 특구소속은 없습니다.`;
    return;
  }
  const pct = Math.round((data.특구소속_비율 || 0) * 100);
  txt.className = "ri-text";
  txt.innerHTML = `전체 유사 과제 <b>${total}</b>건 중 특구소속 <b>${tukku}</b>건 <span class="ri-pct">${pct}%</span>`;
  const regs = data.top3 || [];
  const max = Math.max(1, ...regs.map(r => r.count));
  regs.forEach((r, i) => {
    const chip = document.createElement("div");
    chip.className = "ri-chip" + (i === 0 ? " lead" : "");
    chip.innerHTML = `
      <span class="ri-chip-name">${r.특구}</span>
      <span class="ri-chip-bar"><span style="width:${Math.max(8, (r.count / max) * 100)}%"></span></span>
      <span class="ri-chip-val">${r.count}</span>`;
    top3.appendChild(chip);
  });
}

function renderRegion(data) {
  renderRegionInline(data);
  renderRegionConc(data.concentration, data.scale_note);
  if (data.status !== "ok") {
    regionRatio.textContent = "–";
    regionDonut.innerHTML = "";
    regionRatioSub.textContent = data.status === "reference_only"
      ? "임계값 이상 유사 과제가 없어 비율을 낼 수 없습니다."
      : "검색하면 표시됩니다.";
    regionDist.innerHTML = "";
    regionDistEmpty.style.display = "block";
    regionDistEmpty.textContent = data.status === "reference_only"
      ? "임계값 이상 유사 과제가 없어 분포를 낼 수 없습니다(참고용 검색과 별개)."
      : "검색하면 특구별 분포가 표시됩니다.";
    return;
  }
  const ratio = data.특구소속_비율 || 0;
  regionRatio.textContent = Math.round(ratio * 100) + "%";
  regionRatioSub.textContent = `전체 유사 과제 ${data.total_matched}건 중 특구소속 ${data.특구소속_matched}건`;
  renderRegionDonut(ratio);

  regionDist.innerHTML = "";
  const regs = data.regions || [];
  if (regs.length === 0) {
    regionDistEmpty.style.display = "block";
    regionDistEmpty.textContent = "이 주제의 유사 과제 중 특구소속은 없습니다.";
    return;
  }
  regionDistEmpty.style.display = "none";
  const max = Math.max(...regs.map(r => r.count));
  regs.forEach((r, i) => {
    const row = document.createElement("div");
    row.className = "region-bar-row" + (i < 3 ? " top" : "");
    const w = Math.max(4, (r.count / max) * 100);
    row.innerHTML = `
      <div class="region-bar-name">${r.특구}</div>
      <div class="region-bar-track"><div class="region-bar-fill" style="width:${w}%"></div></div>
      <div class="region-bar-val">${r.count}</div>`;
    regionDist.appendChild(row);
  });
}

async function loadRegion(query) {
  try {
    const res = await fetch(`/api/region?query=${encodeURIComponent(query || "")}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    renderRegion(await res.json());
  } catch (e) {
    console.error("지역 편중 분석을 불러오지 못했습니다.", e);
  }
}

async function runSearch() {
  const query = topicInput.value;
  const rankBy = rankSelect.value;
  const url = `/api/search?query=${encodeURIComponent(query)}&rank_by=${encodeURIComponent(rankBy)}`;
  let result;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    result = await res.json();
  } catch (e) {
    renderBanner("error");
    return;
  }

   if (result.blank_query) { renderBanner("blank"); taskBody.innerHTML = ""; researcherBody.innerHTML = "";
    statCluster.textContent = "–"; statCount.textContent = "–"; statOrgs.innerHTML = "";
    renderRisk(null); renderDuplicationRisk(null); renderClusterMap(null); renderEgoGraph(null); loadRegion(query); return; }

  if (result.empty_corpus) { renderBanner("empty_corpus"); renderRisk(null); renderDuplicationRisk(null); renderEgoGraph(null); loadRegion(query); return; }

  renderBanner(result.reference_only ? "reference" : null);
  renderRisk(result.risk_bucket);
  statCluster.textContent = result.cluster;
  statCount.textContent = result.reference_only ? "0" : result.count;
  statOrgs.innerHTML = (result.orgs || []).map(o => `<span class="org-tag">${o}</span>`).join("");
  renderTaskTable(result);
  renderResearcherTable(result);
  renderDuplicationRisk(result);
  renderClusterMap({ ...result.query_coord, cluster: result.cluster });
  loadEgoGraph(query);
  loadRegion(query);
}

searchBtn.addEventListener("click", runSearch);
rankSelect.addEventListener("change", () => { if (topicInput.value.trim()) runSearch(); });
topicInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });

renderEgoLegend();
loadClusters();
loadRegion("");
