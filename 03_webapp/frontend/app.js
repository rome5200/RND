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
  const res = await fetch("/api/clusters");
  const data = await res.json();
  clusterPoints = data.points;
  fitScales(clusterPoints);
  renderLegend(data.n_clusters);
  renderClusterMap(null);
}

function renderBanner(state) {
  banner.className = "";
  if (state === "blank") {
    banner.textContent = "검색어를 입력해주세요.";
    banner.className = "blank";
  } else if (state === "empty_corpus") {
    banner.textContent = "특구 소속 기관이 수행한 과제 데이터가 없습니다.";
    banner.className = "blank";
  } else if (state === "reference") {
    banner.textContent = "정확히 일치하는 유사 과제를 찾지 못했습니다. 아래는 유사도가 가장 높았던 3건입니다(참고용).";
    banner.className = "reference";
  } else {
    banner.style.display = "none";
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

async function runSearch() {
  const query = topicInput.value;
  const rankBy = rankSelect.value;
  const url = `/api/search?query=${encodeURIComponent(query)}&rank_by=${encodeURIComponent(rankBy)}`;
  const res = await fetch(url);
  const result = await res.json();

  if (result.blank_query) { renderBanner("blank"); taskBody.innerHTML = ""; researcherBody.innerHTML = ""; statCluster.textContent = "–"; statCount.textContent = "–"; statOrgs.innerHTML = ""; renderClusterMap(null); return; }
  if (result.empty_corpus) { renderBanner("empty_corpus"); return; }

  renderBanner(result.reference_only ? "reference" : null);
  statCluster.textContent = result.cluster;
  statCount.textContent = result.reference_only ? "0" : result.count;
  statOrgs.innerHTML = (result.orgs || []).map(o => `<span class="org-tag">${o}</span>`).join("");
  renderTaskTable(result);
  renderResearcherTable(result);
  renderClusterMap({ ...result.query_coord, cluster: result.cluster });
}

searchBtn.addEventListener("click", runSearch);
rankSelect.addEventListener("change", () => { if (topicInput.value.trim()) runSearch(); });
topicInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });

loadClusters();
