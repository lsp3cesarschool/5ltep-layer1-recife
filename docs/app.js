// 5L-TEP Layer 1 dashboard: reads data/layer1.json (written by `python main.py report`).
// Two languages: every label of the page is in I18N; data values (dataset titles, column
// names) are shown as published. Everything from the data is escaped before it is shown.
"use strict";

const I18N = {
  en: {
    back: "← Back to the repository", eyebrow: "5L-TEP · Layer 1 · Structural Contracts", loading: "Loading…",
    run: "Run Layer 1 now ↗", issues: "Drift issues ↗", prs: "Suggested schemas ↗",
    maturity_h: "Schema maturity", findings_h: "Documentation findings", datasets_h: "Datasets",
    maturity_note: "How verifiable is the structure the portal declares for each file? A dataset is as verifiable as its least documented file.",
    findings_note: "The dictionaries themselves, measured every week: what format they come in, why some cannot be read, how the portal links them to the files, how many ways it spells a type, and how often dictionary and file disagree.",
    search: "Search datasets or files", all_levels: "All levels", only_failing: "only files that do not conform",
    col_dataset: "Dataset", col_level: "Level", col_files: "Files", col_conform: "Conform", col_dicts: "Dictionaries",
    privacy_note: "Only counts and row numbers are kept: no cell value is ever stored or shown.",
    subtitle: "Census of {date} · report of {gen}",
    t_datasets: "Datasets", t_files: "Tabular files", t_checked: "Files checked", t_conf: "Files that conform",
    t_drift: "Schema drift events", of_total: "{n} of {t}", conf_note: "{n} of {t} files with a declared schema",
    pass: "Layer 1 passes", fail: "Layer 1 does not pass", threshold: "threshold {t}",
    drift_note: "{o} in files · {d} in declared schemas",
    u_datasets: "Datasets", u_files: "Files",
    lv: ["0 · no dictionary", "1 · for people only", "2 · machine-readable", "3 · types in the API", "4 · level 3 and conforms"],
    tip_level: "Level {l}: {n} ({p})",
    p_dicts: "Dictionaries", p_unread: "Why dictionaries cannot be read", p_links: "How files are linked to a dictionary",
    p_types: "Declared types", p_vs: "Files against their dictionaries", p_files: "The files", p_pdf: "PDF dictionaries",
    k_total: "dictionaries", k_machine: "machine-readable", k_read: "read by the toolkit", k_human: "for people only (PDF, HTML)",
    k_orphans: "describe no file", k_ids: "name the files they describe", k_broken: "name a file that does not exist", k_other_ds: "cite another dataset's address",
    k_fields: "declared fields", k_spell: "different spellings of a type", k_recog: "fields with a recognised type",
    k_dates: "date fields with a declared format", k_unrec: "Spellings not recognised",
    k_checked: "files checked against a schema", k_missing: "lack declared fields", k_undecl: "have undeclared columns",
    k_spelling: "spell a column differently", k_typos: "have probable typos (declared ≈ file column)",
    k_pdftypos: "PDFs with probable typos, by the oracle", f_typos: "probable typos (declared → file)", k_inferred: "formats inferred from the data (not declared)",
    k_validated: "files read", k_encodings: "encodings", k_delims: "delimiters", k_decode: "with bytes that do not decode",
    k_ragged: "with rows of the wrong width", k_multi: "zips whose members have different headers",
    k_nottab: "not a CSV behind the link", k_unreach: "Files that could not be downloaded",
    k_pdflinked: "PDF dictionaries linked to a file", k_processed: "processed", k_stage: "Stage", k_n: "n",
    k_recall: "recall", k_precision: "precision", k_em: "exact match", k_ls: "Levenshtein",
    stage_det: "deterministic", stage_llm: "LLM", outcomes: "Outcomes",
    m_name: "by name", m_single: "only dictionary", "m_declared-id": "declared by the dictionary", m_header: "by columns",
    m_description: "list in the description", m_none: "no dictionary",
    r_html: "an HTML page instead of the file", "r_html-page": "an HTML page instead of the file", r_malformed: "malformed file",
    "r_no-field-table": "no field table recognised", "r_format-not-read": "format not read yet", "r_too-large": "too large",
    "r_download-failed": "download failed", r_other: "other",
    none: "none", f_rows: "rows", f_schema: "schema", f_status: "status", f_dict: "dictionary", f_conf: "conforms",
    f_missing: "declared, not in the file", f_undecl: "in the file, not declared", f_spelling: "spelled differently",
    f_errors: "cells that break the declared type or constraints", f_drift: "drift events", yes: "yes", no: "no",
    s_ok: "read", s_error: "could not be read", "s_not-tabular": "not a CSV", s_empty: "empty", s_pending: "not checked yet",
    footer: "Method: {m}. Summary for Layer 5:",
  },
  pt: {
    back: "← Voltar ao repositório", eyebrow: "5L-TEP · Camada 1 · Contratos Estruturais", loading: "Carregando…",
    run: "Rodar a Camada 1 agora ↗", issues: "Issues de deriva ↗", prs: "Esquemas sugeridos ↗",
    maturity_h: "Maturidade do esquema", findings_h: "Achados de documentação", datasets_h: "Conjuntos de dados",
    maturity_note: "Quão verificável é a estrutura que o portal declara para cada arquivo? Um conjunto é tão verificável quanto o seu arquivo menos documentado.",
    findings_note: "Os próprios dicionários, medidos toda semana: em que formato vêm, por que alguns não podem ser lidos, como o portal os liga aos arquivos, de quantos jeitos escreve um tipo e com que frequência dicionário e arquivo discordam.",
    search: "Buscar conjuntos ou arquivos", all_levels: "Todos os níveis", only_failing: "só arquivos não conformes",
    col_dataset: "Conjunto", col_level: "Nível", col_files: "Arquivos", col_conform: "Conformes", col_dicts: "Dicionários",
    privacy_note: "Só contagens e números de linha são guardados: nenhum valor de célula é armazenado ou exibido.",
    subtitle: "Censo de {date} · relatório de {gen}",
    t_datasets: "Conjuntos de dados", t_files: "Arquivos tabulares", t_checked: "Arquivos verificados",
    t_conf: "Arquivos conformes", t_drift: "Eventos de deriva de esquema", of_total: "{n} de {t}",
    conf_note: "{n} de {t} arquivos com esquema declarado",
    pass: "A Camada 1 passa", fail: "A Camada 1 não passa", threshold: "limiar {t}",
    drift_note: "{o} nos arquivos · {d} nos esquemas declarados",
    u_datasets: "Conjuntos", u_files: "Arquivos",
    lv: ["0 · sem dicionário", "1 · só para pessoas", "2 · legível por máquina", "3 · tipos na API", "4 · nível 3 e conforme"],
    tip_level: "Nível {l}: {n} ({p})",
    p_dicts: "Dicionários", p_unread: "Por que dicionários não podem ser lidos", p_links: "Como os arquivos são ligados a um dicionário",
    p_types: "Tipos declarados", p_vs: "Arquivos contra seus dicionários", p_files: "Os arquivos", p_pdf: "Dicionários em PDF",
    k_total: "dicionários", k_machine: "legíveis por máquina", k_read: "lidos pela ferramenta", k_human: "só para pessoas (PDF, HTML)",
    k_orphans: "não descrevem nenhum arquivo", k_ids: "nomeiam os arquivos que descrevem", k_broken: "nomeiam um arquivo que não existe", k_other_ds: "citam o endereço de outro conjunto",
    k_fields: "campos declarados", k_spell: "grafias diferentes de um tipo", k_recog: "campos com tipo reconhecido",
    k_dates: "campos de data com formato declarado", k_unrec: "Grafias não reconhecidas",
    k_checked: "arquivos verificados contra um esquema", k_missing: "não têm campos declarados", k_undecl: "têm colunas não declaradas",
    k_spelling: "grafam uma coluna de outro jeito", k_typos: "têm prováveis erros de digitação (declarado ≈ coluna)",
    k_pdftypos: "PDFs com prováveis erros de digitação, pelo oráculo", f_typos: "prováveis erros de digitação (declarado → arquivo)", k_inferred: "formatos inferidos dos dados (não declarados)",
    k_validated: "arquivos lidos", k_encodings: "codificações", k_delims: "delimitadores", k_decode: "com bytes que não decodificam",
    k_ragged: "com linhas de largura errada", k_multi: "zips com membros de cabeçalhos diferentes",
    k_nottab: "sem CSV por trás do link", k_unreach: "Arquivos que não puderam ser baixados",
    k_pdflinked: "dicionários em PDF ligados a um arquivo", k_processed: "processados", k_stage: "Etapa", k_n: "n",
    k_recall: "revocação", k_precision: "precisão", k_em: "correspondência exata", k_ls: "Levenshtein",
    stage_det: "determinística", stage_llm: "LLM", outcomes: "Resultados",
    m_name: "pelo nome", m_single: "único dicionário", "m_declared-id": "declarado pelo dicionário", m_header: "pelas colunas",
    m_description: "lista na descrição", m_none: "sem dicionário",
    "r_html-page": "uma página HTML no lugar do arquivo", r_malformed: "arquivo malformado",
    "r_no-field-table": "nenhuma tabela de campos reconhecida", "r_format-not-read": "formato ainda não lido",
    "r_too-large": "grande demais", "r_download-failed": "download falhou", r_other: "outro",
    none: "nenhum", f_rows: "linhas", f_schema: "esquema", f_status: "situação", f_dict: "dicionário", f_conf: "conforme",
    f_missing: "declarados, ausentes do arquivo", f_undecl: "no arquivo, não declarados", f_spelling: "grafados de outro jeito",
    f_errors: "células que violam o tipo ou as restrições declaradas", f_drift: "eventos de deriva", yes: "sim", no: "não",
    s_ok: "lido", s_error: "não pôde ser lido", "s_not-tabular": "não é CSV", s_empty: "vazio", s_pending: "ainda não verificado",
    footer: "Método: {m}. Resumo para a Camada 5:",
  },
};

// Language: ?lang= > the visitor's last choice > the browser's language.
const LANG = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "en" || q === "pt") {
    try { localStorage.setItem("l1-lang", q); } catch (e) { /* storage blocked: fine */ }
    return q;
  }
  try {
    const saved = localStorage.getItem("l1-lang");
    if (saved === "en" || saved === "pt") return saved;
  } catch (e) { /* storage blocked: fine */ }
  return (navigator.language || "").toLowerCase().startsWith("pt") ? "pt" : "en";
})();
const T = I18N[LANG];
const t = (key, vars = {}) => String(T[key] ?? I18N.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
const el = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString(LANG === "pt" ? "pt-BR" : "en"));
const pct = (x) => (x == null ? "—" : (x * 100).toLocaleString(LANG === "pt" ? "pt-BR" : "en", { maximumFractionDigits: 1 }) + "%");
const levelColor = (l) => `var(--level-${l})`;

function repo() {
  // On GitHub Pages (<owner>.github.io/<repo>/) the repository is github.com/<owner>/<repo>.
  const m = location.hostname.match(/^([^.]+)\.github\.io$/);
  const name = location.pathname.split("/").filter(Boolean)[0];
  return m && name ? `https://github.com/${m[1]}/${name}` : "https://github.com/lsp3cesarschool/5ltep-layer1";
}

function translatePage() {
  document.documentElement.lang = LANG === "pt" ? "pt-BR" : "en";
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => { n.placeholder = t(n.dataset.i18nPlaceholder); });
  for (const lang of ["en", "pt"]) {
    const link = el(`lang-${lang}`);
    const u = new URL(location.href);
    u.searchParams.set("lang", lang);
    link.href = u.search;
    link.classList.toggle("current", lang === LANG);
  }
  const r = repo();
  el("repo-link").href = r;
  el("readme-link").href = `${r}#readme`;
  el("leiame-link").href = `${r}/blob/main/LEIAME.md`;
  el("run-link").href = `${r}/actions/workflows/layer1.yml`;
  el("issues-link").href = `${r}/issues?q=is%3Aissue+label%3Alayer1`;
  el("prs-link").href = `${r}/pulls?q=is%3Apr+schemas+suggested`;
}

// --- tooltip ---------------------------------------------------------------------
const tip = el("tooltip");
function bindTip(node, html) {
  const show = (ev) => {
    tip.innerHTML = html;
    tip.hidden = false;
    const x = Math.min(ev.clientX + 12, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = `${x}px`;
    tip.style.top = `${ev.clientY + 14}px`;
  };
  node.addEventListener("mousemove", show);
  node.addEventListener("mouseleave", () => { tip.hidden = true; });
  node.addEventListener("focus", (ev) => show({ clientX: node.getBoundingClientRect().left, clientY: node.getBoundingClientRect().bottom }));
  node.addEventListener("blur", () => { tip.hidden = true; });
}

// --- tiles -------------------------------------------------------------------------
function tile(label, value, note = "", meter = null, extra = "") {
  return `<div class="tile"><div class="label">${esc(label)}</div><div class="value">${value}</div>`
    + (meter == null ? "" : `<div class="meter"><span style="width:${Math.max(0, Math.min(1, meter)) * 100}%"></span></div>`)
    + `<div class="note">${note}</div>${extra}</div>`;
}

function renderTiles(s) {
  const status = s.l1_rate == null ? "" : s.l1_pass
    ? `<div class="status good">✓ ${esc(t("pass"))}</div>`
    : `<div class="status bad">✗ ${esc(t("fail"))}</div>`;
  el("tiles").innerHTML = [
    tile(t("t_datasets"), fmt(s.datasets.total)),
    tile(t("t_files"), fmt(s.tables.total)),
    tile(t("t_checked"), pct(s.tables.validation_coverage),
      esc(t("of_total", { n: fmt(s.tables.validated), t: fmt(s.tables.total) })), s.tables.validation_coverage ?? 0),
    tile(t("t_conf"), pct(s.l1_rate), esc(t("conf_note", { n: fmt(s.conformant), t: fmt(s.verifiable) }))
      + ` · ${esc(t("threshold", { t: pct(s.method.l1_pass_threshold) }))}`, s.l1_rate ?? 0, status),
    tile(t("t_drift"), fmt(s.drift.observed + s.drift.declared),
      esc(t("drift_note", { o: fmt(s.drift.observed), d: fmt(s.drift.declared) }))),
  ].join("");
}

// --- maturity: one stacked bar per unit --------------------------------------------
function renderMaturity(s) {
  const rows = [[t("u_datasets"), s.datasets.by_level], [t("u_files"), s.tables.by_level]];
  const box = el("maturity");
  box.innerHTML = "";
  for (const [name, counts] of rows) {
    const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
    const row = document.createElement("div");
    row.className = "stack-row";
    row.innerHTML = `<div class="name">${esc(name)}</div><div class="stack" role="img" aria-label="${esc(name)}"></div>`;
    const stack = row.querySelector(".stack");
    for (let l = 0; l <= 4; l++) {
      const n = counts[String(l)] || 0;
      if (!n) continue;
      const seg = document.createElement("div");
      seg.style.flex = `${n} 0 0`;
      seg.style.background = levelColor(l);
      seg.style.color = `var(--ink-${l})`;
      seg.tabIndex = 0;
      if (n / total >= 0.06) seg.textContent = fmt(n);        // direct label only where it fits
      bindTip(seg, esc(t("tip_level", { l, n: fmt(n), p: pct(n / total) })) + `<br><span class="muted">${esc(T.lv[l])}</span>`);
      stack.appendChild(seg);
    }
    box.appendChild(row);
  }
  el("maturity-legend").innerHTML = T.lv.map((label, l) =>
    `<li><span class="swatch" style="background:${levelColor(l)}"></span>${esc(label)}`
    + ` (${fmt(s.datasets.by_level[l])} · ${fmt(s.tables.by_level[l])})</li>`).join("");
}

// --- findings ----------------------------------------------------------------------
function kv(pairs) {
  return `<div class="kv">${pairs.map(([k, v]) => `<span>${esc(k)}</span><span class="v">${v}</span>`).join("")}</div>`;
}

function bars(obj, labelOf = (k) => k) {
  const entries = Object.entries(obj || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return `<p class="muted small">${esc(t("none"))}</p>`;
  const max = Math.max(...entries.map(([, n]) => n));
  return `<div class="bars">${entries.map(([k, n]) =>
    `<span class="lbl" title="${esc(labelOf(k))}">${esc(labelOf(k))}</span>`
    + `<span class="bar"><span style="width:${(n / max) * 100}%"></span></span><span class="n">${fmt(n)}</span>`).join("")}</div>`;
}

function renderFindings(f) {
  const d = f.dictionaries, ty = f.types, vs = f.files_vs_dictionaries, fi = f.files, pdf = f.pdf_extraction;
  const label = (prefix) => (k) => T[`${prefix}_${k}`] || I18N.en[`${prefix}_${k}`] || k;
  const panels = [
    [t("p_dicts"), kv([[t("k_total"), fmt(d.total)], [t("k_machine"), fmt(d.machine_readable)],
      [t("k_read"), fmt(d.machine_readable_and_read)], [t("k_human"), fmt(d.human_readable)],
      [t("k_orphans"), fmt(d.orphans)], [t("k_ids"), fmt(d.declaring_resource_ids)],
      [t("k_broken"), fmt(d.broken_declared_links)], [t("k_other_ds"), fmt(d.naming_another_dataset)]]) + bars(d.by_format)],
    [t("p_unread"), bars(d.unreadable_by_reason, label("r"))],
    [t("p_links"), bars(f.links.by_method, label("m"))],
    [t("p_types"), kv([[t("k_fields"), fmt(ty.fields_declared)], [t("k_spell"), fmt(ty.distinct_spellings)],
      [t("k_recog"), pct(ty.fields_with_recognised_type)], [t("k_dates"), pct(ty.date_fields_with_declared_format)]])
      + `<div class="chips">${Object.entries(ty.top_spellings || {}).map(([k, n]) => `<span class="chip">${esc(k || "∅")} · ${fmt(n)}</span>`).join("")}</div>`
      + (ty.unrecognised_spellings?.length ? `<p class="small muted">${esc(t("k_unrec"))}: ${ty.unrecognised_spellings.map((x) => `<code>${esc(x)}</code>`).join(" ")}</p>` : "")],
    [t("p_vs"), kv([[t("k_checked"), fmt(vs.checked)], [t("k_missing"), fmt(vs.with_declared_fields_missing)],
      [t("k_undecl"), fmt(vs.with_undeclared_columns)], [t("k_spelling"), fmt(vs.with_spelling_differences)],
      [t("k_typos"), fmt(vs.with_probable_typos)]])
      + `<p class="small muted">${esc(t("k_inferred"))}</p>` + bars(vs.formats_inferred_from_data)],
    [t("p_files"), kv([[t("k_validated"), fmt(fi.validated)], [t("k_decode"), fmt(fi.with_decode_errors)],
      [t("k_ragged"), fmt(fi.with_ragged_rows)], [t("k_multi"), fmt(fi.zips_with_several_headers)],
      [t("k_nottab"), fmt(fi.not_tabular)]])
      + `<p class="small muted">${esc(t("k_encodings"))}: ${Object.entries(fi.encodings || {}).map(([k, n]) => `<code>${esc(k)}</code> ${fmt(n)}`).join(" · ") || "—"}<br>`
      + `${esc(t("k_delims"))}: ${Object.entries(fi.delimiters || {}).map(([k, n]) => `<code>${esc(k === "\t" ? "TAB" : k)}</code> ${fmt(n)}`).join(" · ") || "—"}</p>`
      + `<p class="small muted">${esc(t("k_unreach"))}</p>` + bars(fi.unreachable_by_reason)],
    [t("p_pdf"), kv([[t("k_pdflinked"), fmt(pdf.pdf_dictionaries_linked)], [t("k_processed"), fmt(pdf.processed)],
      [t("k_pdftypos"), fmt(pdf.with_probable_typos)]])
      + `<table class="mini"><thead><tr><th>${esc(t("k_stage"))}</th><th>${esc(t("k_n"))}</th><th>${esc(t("k_recall"))}</th>`
      + `<th>${esc(t("k_precision"))}</th><th>${esc(t("k_em"))}</th><th>${esc(t("k_ls"))}</th></tr></thead><tbody>`
      + [["stage_det", pdf.deterministic], ["stage_llm", pdf.llm]].map(([k, r]) =>
        `<tr><td>${esc(t(k))}</td><td>${fmt(r.with_oracle)}</td><td>${pct(r.recall)}</td><td>${pct(r.precision)}</td>`
        + `<td>${pct(r.exact_match)}</td><td>${pct(r.levenshtein)}</td></tr>`).join("") + "</tbody></table>"
      + `<p class="small muted">${esc(t("outcomes"))}: ${Object.entries(pdf.by_outcome || {}).map(([k, n]) => `${esc(k)} ${fmt(n)}`).join(" · ") || "—"}</p>`],
  ];
  el("findings").innerHTML = panels.map(([h, body]) => `<div class="panel"><h3>${esc(h)}</h3>${body}</div>`).join("");
}

// --- datasets ----------------------------------------------------------------------
function levelBadge(l) {
  return l == null ? "—" : `<span class="level"><span class="swatch" style="background:${levelColor(l)}"></span>${l}</span>`;
}

function fileDetail(f) {
  const c = f.conformance;
  const status = f.status ? t(`s_${f.status}`) : t("s_pending");
  const dict = f.dictionary ? `${esc(f.dictionary.format || "")} · ${esc(t(`m_${f.dictionary.method}`))}` : esc(t("m_none"));
  let conf = "—";
  let more = "";
  if (c) {
    conf = c.pass ? `<span class="status good">✓ ${esc(t("yes"))}</span>` : `<span class="status bad">✗ ${esc(t("no"))}</span>`;
    conf += ` <span class="muted">${pct(c.error_rate)}</span>`;
    const list = (key, items) => (items && items.length
      ? `<div class="small"><span class="muted">${esc(t(key))}:</span> ${items.slice(0, 30).map((x) => `<code>${esc(x)}</code>`).join(" ")}${items.length > 30 ? " …" : ""}</div>` : "");
    more += list("f_missing", c.missing) + list("f_undecl", c.undeclared)
      + list("f_spelling", Object.entries(c.spelling || {}).map(([a, b]) => `${a} → ${b}`))
      + list("f_typos", Object.entries(c.probable_typos || {}).map(([a, b]) => `${a} → ${b}`));
    const errs = Object.entries(c.errors_by_field || {}).map(([field, kinds]) =>
      [field, Object.entries(kinds).map(([k, n]) => `${k} ${fmt(n)}`).join(", "), Object.values(kinds).reduce((a, b) => a + b, 0)])
      .sort((a, b) => b[2] - a[2]).slice(0, 8);
    if (errs.length) {
      more += `<div class="small muted">${esc(t("f_errors"))}:</div><ul class="errs small">`
        + errs.map(([field, kinds]) => `<li><code>${esc(field)}</code>: ${esc(kinds)}</li>`).join("") + "</ul>";
    }
  }
  if (f.error) more += `<div class="small muted">${esc(f.error)}</div>`;
  return `<tr id="file-${esc(f.id)}"><td><a href="${esc(f.url)}" rel="noopener">${esc(f.name || f.id)}</a>${more}</td>`
    + `<td>${levelBadge(f.level)}</td><td>${dict}</td><td>${esc(f.schema_kind || "—")}</td>`
    + `<td>${esc(status)}</td><td class="num">${fmt(f.rows)}</td><td>${conf}</td><td class="num">${fmt(f.drift_events)}</td></tr>`;
}

let DATA = null;
const OPEN = new Set();

function renderDatasets() {
  const q = el("search").value.trim().toLowerCase();
  const level = el("level-filter").value;
  const failing = el("only-failing").checked;
  const body = document.querySelector("#datasets tbody");
  const rows = [];
  for (const ds of DATA.datasets) {
    let files = ds.tables;
    if (failing) files = files.filter((f) => f.conformance && !f.conformance.pass);
    const hit = !q || ds.name.toLowerCase().includes(q) || (ds.title || "").toLowerCase().includes(q)
      || files.some((f) => (f.name || "").toLowerCase().includes(q));
    if (!hit || (level !== "" && String(ds.level) !== level) || (failing && !files.length)) continue;
    const ver = ds.tables.filter((f) => f.conformance);
    const ok = ver.filter((f) => f.conformance.pass);
    const dicts = ds.dictionaries.map((d) => `${esc(d.format)}${d.readable === false ? " ✗" : ""}`).join(", ") || "—";
    rows.push(`<tr class="ds" data-name="${esc(ds.name)}" tabindex="0"><td><strong>${esc(ds.title)}</strong><br>`
      + `<a class="small" href="${esc(ds.url)}" rel="noopener">${esc(ds.name)}</a></td><td>${levelBadge(ds.level)}</td>`
      + `<td class="num">${fmt(ds.tables.length)}</td><td class="num">${ver.length ? `${fmt(ok.length)}/${fmt(ver.length)}` : "—"}</td>`
      + `<td class="small">${dicts}</td></tr>`);
    if (OPEN.has(ds.name)) {
      rows.push(`<tr class="detail"><td colspan="5"><div class="table-wrap"><table class="files"><thead><tr>`
        + [t("col_files"), t("col_level"), t("f_dict"), t("f_schema"), t("f_status"), t("f_rows"), t("f_conf"), t("f_drift")]
          .map((h) => `<th>${esc(h)}</th>`).join("")
        + `</tr></thead><tbody>${files.map(fileDetail).join("")}</tbody></table></div></td></tr>`);
    }
  }
  body.innerHTML = rows.join("");
  body.querySelectorAll("tr.ds").forEach((tr) => {
    const toggle = () => {
      const n = tr.dataset.name;
      OPEN.has(n) ? OPEN.delete(n) : OPEN.add(n);
      renderDatasets();
    };
    tr.addEventListener("click", (ev) => { if (ev.target.tagName !== "A") toggle(); });
    tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter") toggle(); });
  });
}

async function main() {
  translatePage();
  try {
    DATA = await (await fetch("data/layer1.json", { cache: "no-cache" })).json();
  } catch (e) {
    el("title").textContent = "No data yet: the first run has not finished.";
    return;
  }
  const s = DATA.summary;
  el("title").textContent = s.portal.title || s.portal.name;
  const day = (x) => (x || "").slice(0, 10);
  el("subtitle").textContent = t("subtitle", { date: day(s.census_at), gen: day(s.generated_at) });
  renderTiles(s);
  renderMaturity(s);
  renderFindings(s.findings);
  // ?resource=<id> (links in the drift issues) opens its dataset and highlights the file
  const wanted = new URLSearchParams(location.search).get("resource");
  if (wanted) {
    const ds = DATA.datasets.find((d) => d.tables.some((f) => f.id === wanted));
    if (ds) OPEN.add(ds.name);
  }
  renderDatasets();
  if (wanted) {
    const row = document.getElementById(`file-${wanted}`);
    if (row) { row.classList.add("highlight"); row.scrollIntoView({ block: "center" }); }
  }
  ["search", "level-filter", "only-failing"].forEach((id) => el(id).addEventListener("input", renderDatasets));
  const m = s.method || {};
  el("footer").innerHTML = esc(t("footer", { m: `L1_MAX_ERROR_RATE=${m.l1_max_error_rate}, L1_PASS_THRESHOLD=${m.l1_pass_threshold}, ROTATION_DAYS=${m.rotation_days}, LLM=${m.llm_model}` }))
    + ` <a href="${repo()}/blob/main/results/layer1_summary.json">results/layer1_summary.json</a>`;
}

main();
