// 5L-TEP Layer 1 dashboard: reads data/layer1.json (written by `python main.py report`).
// Two languages: every label of the page is in I18N; data values (dataset titles, column
// names) are shown as published. Everything from the data is escaped before it is shown.
"use strict";

const I18N = {
  en: {
    back: "← Back to the repository", eyebrow: "5L-TEP · Layer 1 · Structural Contracts", loading: "Loading…",
    run: "Run Layer 1 now ↗", issues: "Drift issues ↗", prs: "Suggested schemas ↗",
    maturity_h: "Schema maturity", findings_h: "Documentation findings", datasets_h: "Datasets",
    maturity_note: "Each dataset is a page of the portal and can publish several data files (CSV, ZIP, spreadsheet, Parquet, JSON or XML), for example one per year or one per table; the same table published in several formats counts once. Each file gets a level for how well the portal describes its structure, from 0 (no dictionary) to 4 (types in the API and the file conforms); a dataset gets the level of its least documented file. This shows where documentation work pays off first. Click a band to see its items.",
    progress_h: "Progress over time",
    progress_note: "One row per weekly run: how many files the portal publishes, reads, declares and gets right, and what changed since the run before (files fixed or broken, new or removed, drift).",
    pg_first: "History starts on {d}: the next weekly run ({next}) adds the first comparison.",
    pg_conform: "conform (of the files with a declared schema)", pg_checkable: "files with a declared schema (of all)",
    pg_date: "Run", pg_files: "Files", pg_read: "Read", pg_checked: "With schema", pg_conf: "Conform",
    pg_fixed: "Fixed", pg_broken: "Broke", pg_new: "New", pg_gone: "Removed", pg_drift: "Drift",
    filter_d: "datasets at level {l}", filter_f: "files at level {l}", dict_page: "page on the portal ↗",
    m_description_sibling: "list in the description of another format", "m_description-sibling": "list in the description of another format",
    findings_note: "The dictionaries themselves, measured every week: what format they come in, why some cannot be read, how the portal links them to the files, how many ways it spells a type, and how often dictionary and file disagree.",
    search: "Search datasets or files", all_levels: "All levels", only_failing: "only files that do not conform",
    col_dataset: "Dataset", col_level: "Level", col_files: "Files", col_conform: "Conform", col_dicts: "Dictionaries",
    privacy_note: "Only counts and row numbers are kept: no cell value is ever stored or shown.",
    subtitle: "Survey of {date} · report of {gen}",
    read_note: "{n} of {t} · not downloaded {nd} · empty {e} · a page or PDF instead of the table {nt} · larger than the machine holds {tl}",
    "rk_no URL": "no URL", "rk_redirect loop": "redirect loop (the link points to itself)",
    "rk_batch time limit": "did not finish within a batch", rk_other: "other error",
    "rk_not-tabular": "a page or PDF instead of the table", rk_empty: "empty file",
    "rk_not-a-table": "not a table (zip of documents or maps; outside the tabular universe)",
    conf_tile_note: "{c} of {k} files with a declared schema · {w} read without one",
    drift_baseline: "first run: baseline of {n} files on {d}; next comparison {next}",
    drift_since: "baseline since {d} · {o} in files · {dd} in declared schemas",
    details: "details ↓",
    coverage_h: "Reading and conformance", unreadable_h: "Files that could not be read", drift_h: "Schema drift",
    coverage_note: "From every tabular file of the portal to the ones that follow their declared schema, with the reason at each step.",
    f_all: "tabular files", f_read: "read", f_with_schema: "read, with a declared schema", f_conform: "conform",
    p_notread: "Why files were not read", p_notconform: "Why checked files do not conform",
    nc_missing: "declared fields missing from the file", nc_undeclared: "columns not declared",
    nc_cells: "more than {r} of the cells break type or constraints", nc_only_cells: "of them, only because of the cells",
    nc_overlap: "A file can fail for more than one reason.",
    s_empty_f: "empty file", s_nottab: "a page or PDF instead of the table", s_toolarge: "larger than the machine holds (see the README, Size and time limits)",
    u_file: "File", u_reason: "Reason", u_host: "Server",
    drift_none_yet: "Drift needs two observations: the first run records each file's structure as its baseline ({n} files on {d}). The next weekly run ({next}) compares against it; any change opens an issue.",
    drift_none: "No change in structure since the baseline ({n} files, first observed on {d}).",
    d_kind: "Kind", d_changes: "What changed", d_when: "When",
    pdf_h: "PDF dictionaries turned into schemas",
    pdf_note: "Each PDF dictionary linked to a file, what the three stages made of it (deterministic reading, local LLM, people) and how well the file's own header confirms it. Schemas are Frictionless Table Schema files in this repository; suggested ones wait in a pull request.",
    x_pdf: "PDF", x_outcome: "Outcome", x_stage: "Stage", x_schema: "Schema", x_typos: "Similar names (dictionary ≈ file)", x_by_position: "Different names in the same place (PDF × file)", x_file: "file",
    o_extracted: "confirmed by the header", o_suggested: "suggested (pull request)", "o_llm-needed": "waiting for the LLM",
    o_failed: "not extracted", o_pending: "waiting for the file's header",
    open_pr: "pull request ↗", schemas_label: "schemas",
    t_datasets: "Datasets", t_files: "Tabular files", t_checked: "Files read", t_conf: "Files that conform",
    t_queue: "In the queue", queue_note: "{gb} GB declared on the portal", s_queued: "in the queue", queue_big: "largest in the queue",
    live_for: "{what} for {d}", live_since: "since {t}", live_run: "see the run",
    live_wait: "waiting for a GitHub machine", live_prep: "preparing", live_survey: "surveying the portal",
    live_pdf: "reading PDF dictionaries", live_llm: "reading PDF dictionaries with the local model",
    live_validate: "downloading and validating files", live_publish: "publishing the results",
    t_dicts: "Dictionaries", dicts_note: "{m} machine-readable ({r} read) · {p} PDF · {o} not linked to any file",
    files_size: "{gb} GB declared on the portal", files_unknown: "{n} without a declared size",
    files_copies: "{n} copies of another file of the same dataset ({gb} GB)",
    copies_checked: "SHA-256: {i} identical, {d} different",
    t_drift: "Schema drift events", of_total: "{n} of {t}", conf_note: "{n} of {t} files with a declared schema",
    pass: "This portal passes the 5L-TEP Layer 1 analysis", fail: "This portal does not pass the 5L-TEP Layer 1 analysis",
    threshold: "threshold {t}",
    verdict_fail: "because only {r} of its files with a declared schema conform to it ({c} of {k}), and Layer 1 requires at least {th}.",
    verdict_pass: "because {r} of its files with a declared schema conform to it ({c} of {k}), at least the {th} Layer 1 requires.",
    drift_note: "{o} in files · {d} in declared schemas",
    u_datasets: "Datasets", u_files: "Files",
    lv: ["0 · no dictionary", "1 · for people only", "2 · machine-readable", "3 · types in the API", "4 · level 3 and conforms"],
    tip_level: "Level {l}: {n} ({p})",
    delivery_h: "File delivery",
    delivery_note: "How each server the portal links its files to delivers them, measured every week: from the files validated, and from a request for the first 100 bytes of a few files per server. Each observation sets what was seen beside what HTTP provides for it, with the reference. It describes, it does not grade.",
    dv_host: "Linked to", dv_served: "Served by", dv_range: "Byte ranges", dv_validators: "No ETag or Last-Modified",
    dv_type: "Generic media type", dv_broken: "Broken links", dv_loops: "Redirect loops", dv_obs: "Observations",
    rg_honoured: "answered", rg_ignored: "whole file", rg_partly: "partly", rg_unknown: "not measured",
    dv_none: "Nothing to observe: the files are delivered as HTTP provides.",
    "sg_broken-links": "{host}: {n} of {of} files linked here answer 404 or 410 (not found). A link that stays where it was published keeps catalogs, citations and analyses working.",
    "sg_redirect-loops": "{host}: {n} of {of} download links redirect back to themselves and never reach the file.",
    "sg_byte-ranges": "{host}: asked for the first 100 bytes, the server sent the whole file ({n} of {of} files asked). HTTP lets a server send only the part asked for (206 Partial Content, Accept-Ranges: bytes), so that a download cut short is resumed instead of started again.",
    sg_validators: "{host}: {n} of {of} files come without ETag or Last-Modified. With them, whoever reuses the data can ask whether a file changed without downloading it again (conditional requests).",
    "sg_media-type": "{host}: {n} of {of} files come with a type that says nothing about the content ({types}). Declaring the format (text/csv, application/zip…) lets browsers and tools open the file as what it is.",
    sg_length: "{host}: {n} of {of} files come without Content-Length: whoever downloads cannot know the size beforehand nor check that the download is complete.",
    k_unreachable: "{n} dictionaries did not answer in this survey (the server, not the portal's documentation): asked again in the next run; their datasets keep the last reading.",
    p_dicts: "Dictionaries", p_unread: "Why dictionaries cannot be read", p_links: "How files are linked to a dictionary",
    p_types: "Declared types", p_vs: "Files against their dictionaries", p_files: "The files", p_pdf: "PDF dictionaries",
    k_total: "dictionaries", k_machine: "machine-readable", k_read: "read by the toolkit", k_human: "for people only (PDF, HTML)",
    k_orphans: "describe no file", k_ids: "name the files they describe", k_broken: "name a file that does not exist", k_other_ds: "cite another dataset's address",
    k_fields: "declared fields", k_spell: "different spellings of a type", k_recog: "fields with a recognised type",
    k_dates: "date fields with a declared format", k_unrec: "Spellings not recognised",
    k_checked: "files checked against a schema", k_missing: "lack declared fields", k_undecl: "have undeclared columns",
    k_spelling: "spell a column differently", k_typos: "with similar names (declared ≈ file column)",
    k_pdftypos: "PDFs with similar names, by the oracle", f_typos: "similar names (declared → file)", k_inferred: "formats inferred from the data (not declared)",
    k_validated: "files read", k_encodings: "encodings", k_delims: "delimiters", k_decode: "with bytes that do not decode",
    k_ragged: "with rows of the wrong width", k_multi: "zips whose members have different headers",
    k_noname: "with columns without a name in the header",
    k_nottables: "published as data, but not tables (zips of documents or maps)", k_formats: "formats read",
    k_dist: "other formats of the same table: compared · same columns · only spelling differs", f_dist: "other formats",
    d_same: "same columns", d_spelling: "same columns, other spelling", d_diff: "other columns", d_missing: "missing", d_extra: "extra", d_notchecked: "not compared",
    similar_h: "Similar names between dictionary and file", similar_search: "Filter by dataset, file or name",
    similar_note: "Pairs of a name the dictionary declares but the file lacks and a column the file has but the dictionary does not declare, whose names are alike (normalised Levenshtein similarity of at least 0.8). Often a typo on one side, but not always: two different fields can have alike names. A heuristic for people to check, not a verdict.",
    similar_count: "{n} pairs in {f} files", s_declared: "Declared in the dictionary", s_column: "Column in the file",
    s_similarity: "Similarity", s_source: "Schema source",
    k_nottab: "a page or PDF instead of the table", k_gb: "data downloaded (GB)", k_minutes: "time downloading and validating (min)",
    k_mbs: "throughput, download and validation (MB/s)", k_netshare: "share of that time waiting for the network", k_ttfb: "time to the server's first answer, median (s)",
    k_reqfail: "requests that failed (and were retried)", k_unreach: "Files that could not be downloaded",
    k_pdflinked: "PDF dictionaries linked to a file", k_processed: "processed", k_stage: "Stage", k_n: "n",
    k_recall: "recall", k_precision: "precision", k_em: "exact match", k_ls: "Levenshtein",
    stage_det: "deterministic", stage_llm: "LLM", outcomes: "Outcomes",
    m_name: "by name", m_single: "only dictionary", "m_declared-id": "declared by the dictionary", m_header: "by columns",
    m_description: "list in the description", m_none: "no dictionary",
    "r_html-page": "an HTML page instead of the file", r_malformed: "malformed file",
    "r_no-field-table": "no field table recognised", "r_format-not-read": "format not read yet", "r_too-large": "too large",
    "r_download-failed": "download failed", r_other: "other",
    none: "none", f_rows: "rows", f_schema: "schema", f_status: "status", f_dict: "dictionary", f_conf: "conforms",
    f_missing: "declared, not in the file", f_undecl: "in the file, not declared", f_spelling: "spelled differently",
    f_errors: "cells that break the declared type or constraints", f_drift: "drift events", yes: "yes", no: "no",
    s_ok: "read", s_error: "could not be read", "s_not-tabular": "not a table", s_empty: "empty", s_pending: "not checked yet", s_sampled: "by sample",
    f_copy: "copy of “{f}” (same name, declared size and file name): its result, since this one was not downloaded or its download failed",
    f_copy_failed: "the download of this copy failed",
    footer: "Method: {m}. Summary for Layer 5:",
  },
  pt: {
    back: "← Voltar ao repositório", eyebrow: "5L-TEP · Camada 1 · Contratos Estruturais", loading: "Carregando…",
    run: "Rodar a Camada 1 agora ↗", issues: "Issues de deriva ↗", prs: "Esquemas sugeridos ↗",
    maturity_h: "Maturidade do esquema", findings_h: "Achados de documentação", datasets_h: "Conjuntos de dados",
    maturity_note: "Cada conjunto de dados é uma página do portal e pode publicar vários arquivos de dados (CSV, ZIP, planilha, Parquet, JSON ou XML), por exemplo um por ano ou um por tabela; a mesma tabela publicada em vários formatos conta uma vez. Cada arquivo recebe um nível conforme o quanto o portal descreve a sua estrutura, de 0 (sem dicionário) a 4 (tipos na API e arquivo conforme); o conjunto fica com o nível do seu arquivo menos documentado. Assim fica claro onde documentar primeiro. Clique numa faixa para ver os itens.",
    progress_h: "Progresso ao longo do tempo",
    progress_note: "Uma linha por execução semanal: quantos arquivos o portal publica, quantos lemos, quantos têm esquema declarado e quantos estão conformes, e o que mudou desde a execução anterior (arquivos consertados ou quebrados, novos ou removidos, deriva).",
    pg_first: "O histórico começa em {d}: a próxima execução semanal ({next}) traz a primeira comparação.",
    pg_conform: "conformes (dos arquivos com esquema declarado)", pg_checkable: "arquivos com esquema declarado (de todos)",
    pg_date: "Execução", pg_files: "Arquivos", pg_read: "Lidos", pg_checked: "Com esquema", pg_conf: "Conformes",
    pg_fixed: "Consertados", pg_broken: "Quebrados", pg_new: "Novos", pg_gone: "Removidos", pg_drift: "Deriva",
    filter_d: "conjuntos no nível {l}", filter_f: "arquivos no nível {l}", dict_page: "página no portal ↗",
    m_description_sibling: "lista na descrição de outro formato", "m_description-sibling": "lista na descrição de outro formato",
    findings_note: "Os próprios dicionários, medidos toda semana: em que formato vêm, por que alguns não podem ser lidos, como o portal os liga aos arquivos, de quantos jeitos escreve um tipo e com que frequência dicionário e arquivo discordam.",
    search: "Buscar conjuntos ou arquivos", all_levels: "Todos os níveis", only_failing: "só arquivos não conformes",
    col_dataset: "Conjunto", col_level: "Nível", col_files: "Arquivos", col_conform: "Conformes", col_dicts: "Dicionários",
    privacy_note: "Só contagens e números de linha são guardados: nenhum valor de célula é armazenado ou exibido.",
    subtitle: "Levantamento de {date} · relatório de {gen}",
    read_note: "{n} de {t} · não baixados {nd} · vazios {e} · página ou PDF no lugar da tabela {nt} · maiores do que a máquina comporta {tl}",
    "rk_no URL": "sem URL", "rk_redirect loop": "redirecionamento em laço (o link aponta para si mesmo)",
    "rk_batch time limit": "não terminou dentro de um lote", rk_other: "outro erro",
    "rk_not-tabular": "página ou PDF no lugar da tabela", rk_empty: "arquivo vazio",
    "rk_not-a-table": "não é tabela (zip de documentos ou mapas; fora do universo tabular)",
    conf_tile_note: "{c} de {k} arquivos com esquema declarado · {w} lidos sem esquema",
    drift_baseline: "primeira execução: linha de base de {n} arquivos em {d}; próxima comparação {next}",
    drift_since: "linha de base desde {d} · {o} nos arquivos · {dd} nos esquemas declarados",
    details: "detalhes ↓",
    coverage_h: "Leitura e conformidade", unreadable_h: "Arquivos que não puderam ser lidos", drift_h: "Deriva de esquema",
    coverage_note: "De todos os arquivos tabulares do portal até os que seguem o esquema declarado, com o motivo em cada etapa.",
    f_all: "arquivos tabulares", f_read: "lidos", f_with_schema: "lidos, com esquema declarado", f_conform: "conformes",
    p_notread: "Por que arquivos não foram lidos", p_notconform: "Por que arquivos verificados não estão conformes",
    nc_missing: "campos declarados ausentes do arquivo", nc_undeclared: "colunas não declaradas",
    nc_cells: "mais de {r} das células violam tipo ou restrições", nc_only_cells: "destes, só por causa das células",
    nc_overlap: "Um arquivo pode falhar por mais de um motivo.",
    s_empty_f: "arquivo vazio", s_nottab: "página ou PDF no lugar da tabela", s_toolarge: "maior do que a máquina comporta (ver o LEIAME, Limites de tamanho e de tempo)",
    u_file: "Arquivo", u_reason: "Motivo", u_host: "Servidor",
    drift_none_yet: "A deriva precisa de duas observações: a primeira execução registra a estrutura de cada arquivo como linha de base ({n} arquivos em {d}). A próxima execução semanal ({next}) compara com ela; qualquer mudança abre uma issue.",
    drift_none: "Nenhuma mudança de estrutura desde a linha de base ({n} arquivos, primeira observação em {d}).",
    d_kind: "Tipo", d_changes: "O que mudou", d_when: "Quando",
    pdf_h: "Dicionários em PDF transformados em esquemas",
    pdf_note: "Cada dicionário em PDF ligado a um arquivo, o que as três etapas fizeram dele (leitura determinística, LLM local, pessoas) e quanto o próprio cabeçalho do arquivo o confirma. Os esquemas são arquivos Frictionless Table Schema neste repositório; os sugeridos aguardam num pull request.",
    x_pdf: "PDF", x_outcome: "Resultado", x_stage: "Etapa", x_schema: "Esquema", x_typos: "Nomes parecidos (dicionário ≈ arquivo)", x_by_position: "Nomes diferentes no mesmo lugar (PDF × arquivo)", x_file: "arquivo",
    o_extracted: "confirmado pelo cabeçalho", o_suggested: "sugerido (pull request)", "o_llm-needed": "aguardando o LLM",
    o_failed: "não extraído", o_pending: "aguardando o cabeçalho do arquivo",
    open_pr: "pull request ↗", schemas_label: "esquemas",
    t_datasets: "Conjuntos de dados", t_files: "Arquivos tabulares", t_checked: "Arquivos lidos",
    t_queue: "Na fila", queue_note: "{gb} GB declarados no portal", s_queued: "na fila", queue_big: "maiores na fila",
    live_for: "{what} há {d}", live_since: "desde {t}", live_run: "ver a execução",
    live_wait: "aguardando uma máquina do GitHub", live_prep: "preparando", live_survey: "levantamento do portal",
    live_pdf: "lendo dicionários em PDF", live_llm: "lendo dicionários em PDF com o modelo local",
    live_validate: "baixando e validando arquivos", live_publish: "publicando os resultados",
    t_dicts: "Dicionários", dicts_note: "{m} legíveis por máquina ({r} lidos) · {p} em PDF · {o} sem ligação com arquivo",
    files_size: "{gb} GB declarados no portal", files_unknown: "{n} sem tamanho declarado",
    files_copies: "{n} cópias de outro arquivo do mesmo conjunto ({gb} GB)",
    copies_checked: "SHA-256: {i} idênticas, {d} diferentes",
    t_conf: "Arquivos conformes", t_drift: "Eventos de deriva de esquema", of_total: "{n} de {t}",
    conf_note: "{n} de {t} arquivos com esquema declarado",
    pass: "Este portal passa na análise da Camada 1 do 5L-TEP", fail: "Este portal não passa na análise da Camada 1 do 5L-TEP",
    threshold: "limiar {t}",
    verdict_fail: "porque só {r} dos seus arquivos com esquema declarado estão conformes a ele ({c} de {k}), e a Camada 1 exige no mínimo {th}.",
    verdict_pass: "porque {r} dos seus arquivos com esquema declarado estão conformes a ele ({c} de {k}), pelo menos os {th} que a Camada 1 exige.",
    drift_note: "{o} nos arquivos · {d} nos esquemas declarados",
    u_datasets: "Conjuntos", u_files: "Arquivos",
    lv: ["0 · sem dicionário", "1 · só para pessoas", "2 · legível por máquina", "3 · tipos na API", "4 · nível 3 e conforme"],
    tip_level: "Nível {l}: {n} ({p})",
    delivery_h: "Entrega dos arquivos",
    delivery_note: "Como cada servidor para o qual o portal aponta seus arquivos os entrega, medido toda semana: pelos arquivos validados e por um pedido dos primeiros 100 bytes de alguns arquivos por servidor. Cada observação põe o que foi visto ao lado do que o HTTP prevê para isso, com a referência. Descreve, não dá nota.",
    dv_host: "Apontado para", dv_served: "Entregue por", dv_range: "Intervalos de bytes", dv_validators: "Sem ETag nem Last-Modified",
    dv_type: "Tipo de mídia genérico", dv_broken: "Links quebrados", dv_loops: "Redirecionamentos em laço", dv_obs: "Observações",
    rg_honoured: "atendidos", rg_ignored: "arquivo inteiro", rg_partly: "em parte", rg_unknown: "não medido",
    dv_none: "Nada a observar: os arquivos são entregues como o HTTP prevê.",
    "sg_broken-links": "{host}: {n} de {of} arquivos apontados para cá respondem 404 ou 410 (não encontrado). Um link que continua onde foi publicado mantém funcionando catálogos, citações e análises.",
    "sg_redirect-loops": "{host}: {n} de {of} links de download redirecionam para si mesmos e nunca chegam ao arquivo.",
    "sg_byte-ranges": "{host}: pedidos os primeiros 100 bytes, o servidor mandou o arquivo inteiro ({n} de {of} arquivos pedidos). O HTTP permite que o servidor mande só a parte pedida (206 Partial Content, Accept-Ranges: bytes), para que um download interrompido seja retomado em vez de recomeçado.",
    sg_validators: "{host}: {n} de {of} arquivos vêm sem ETag nem Last-Modified. Com eles, quem reutiliza os dados pode perguntar se um arquivo mudou sem baixá-lo de novo (pedidos condicionais).",
    "sg_media-type": "{host}: {n} de {of} arquivos vêm com um tipo que nada diz do conteúdo ({types}). Declarar o formato (text/csv, application/zip…) permite que navegadores e ferramentas abram o arquivo como o que ele é.",
    sg_length: "{host}: {n} de {of} arquivos vêm sem Content-Length: quem baixa não sabe o tamanho antes nem confere se o download veio completo.",
    k_unreachable: "{n} dicionários não responderam neste levantamento (o servidor, não a documentação do portal): pedidos de novo na próxima execução; os conjuntos ficam com a última leitura.",
    p_dicts: "Dicionários", p_unread: "Por que dicionários não podem ser lidos", p_links: "Como os arquivos são ligados a um dicionário",
    p_types: "Tipos declarados", p_vs: "Arquivos contra seus dicionários", p_files: "Os arquivos", p_pdf: "Dicionários em PDF",
    k_total: "dicionários", k_machine: "legíveis por máquina", k_read: "lidos pela ferramenta", k_human: "só para pessoas (PDF, HTML)",
    k_orphans: "não descrevem nenhum arquivo", k_ids: "nomeiam os arquivos que descrevem", k_broken: "nomeiam um arquivo que não existe", k_other_ds: "citam o endereço de outro conjunto",
    k_fields: "campos declarados", k_spell: "grafias diferentes de um tipo", k_recog: "campos com tipo reconhecido",
    k_dates: "campos de data com formato declarado", k_unrec: "Grafias não reconhecidas",
    k_checked: "arquivos verificados contra um esquema", k_missing: "não têm campos declarados", k_undecl: "têm colunas não declaradas",
    k_spelling: "grafam uma coluna de outro jeito", k_typos: "com nomes parecidos (declarado ≈ coluna)",
    k_pdftypos: "PDFs com nomes parecidos, pelo oráculo", f_typos: "nomes parecidos (declarado → arquivo)", k_inferred: "formatos inferidos dos dados (não declarados)",
    k_validated: "arquivos lidos", k_encodings: "codificações", k_delims: "delimitadores", k_decode: "com bytes que não decodificam",
    k_ragged: "com linhas de largura errada", k_multi: "zips com membros de cabeçalhos diferentes",
    k_noname: "com colunas sem nome no cabeçalho",
    k_nottables: "publicados como dados, mas não são tabelas (zips de documentos ou mapas)", k_formats: "formatos lidos",
    k_dist: "outros formatos da mesma tabela: comparados · mesmas colunas · só a grafia difere", f_dist: "outros formatos",
    d_same: "mesmas colunas", d_spelling: "mesmas colunas, outra grafia", d_diff: "colunas diferentes", d_missing: "faltam", d_extra: "sobram", d_notchecked: "não comparado",
    similar_h: "Nomes parecidos entre dicionário e arquivo", similar_search: "Filtrar por conjunto, arquivo ou nome",
    similar_note: "Pares formados por um nome que o dicionário declara mas o arquivo não tem e uma coluna que o arquivo tem mas o dicionário não declara, quando os nomes se parecem (similaridade de Levenshtein normalizada de pelo menos 0,8). Muitas vezes é erro de digitação de um dos lados, mas nem sempre: dois campos diferentes podem ter nomes parecidos. É uma heurística para pessoas conferirem, não um veredito.",
    similar_count: "{n} pares em {f} arquivos", s_declared: "Declarado no dicionário", s_column: "Coluna no arquivo",
    s_similarity: "Similaridade", s_source: "Fonte do esquema",
    k_nottab: "página ou PDF no lugar da tabela", k_gb: "dados baixados (GB)", k_minutes: "tempo baixando e validando (min)",
    k_mbs: "vazão, download e validação (MB/s)", k_netshare: "fração desse tempo esperando a rede", k_ttfb: "tempo até a primeira resposta do servidor, mediana (s)",
    k_reqfail: "pedidos que falharam (e foram repetidos)", k_unreach: "Arquivos que não puderam ser baixados",
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
    s_ok: "lido", s_error: "não pôde ser lido", "s_not-tabular": "não é tabela", s_empty: "vazio", s_pending: "ainda não verificado", s_sampled: "por amostra",
    f_copy: "cópia de “{f}” (mesmo nome, tamanho declarado e nome de arquivo): o resultado dele, porque esta não foi baixada ou o download dela falhou",
    f_copy_failed: "o download desta cópia falhou",
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
  document.querySelectorAll("[data-i18n-label]").forEach((n) => { n.label = t(n.dataset.i18nLabel); });
  document.querySelectorAll("#level-filter option[value^='d'], #level-filter option[value^='f']").forEach((o) => {
    o.textContent = t(o.value[0] === "d" ? "filter_d" : "filter_f", { l: o.value.slice(1) });
  });
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
    // one line per item: the notes join their parts with " · " (the same texts are used elsewhere)
    + `<div class="note">${note.split(" · ").join("<br>")}</div>${extra}</div>`;
}

function nextMonday(iso) {
  // The weekly run: Mondays 03:30 UTC (layer1.yml).
  const d = new Date(iso || Date.now());
  const n = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 3, 30));
  do { n.setUTCDate(n.getUTCDate() + 1); } while (n.getUTCDay() !== 1);
  return n.toISOString().slice(0, 10);
}

function renderTiles(s) {
  const c = s.coverage || {};
  const more = (anchor) => ` <a class="more" href="#${anchor}">${esc(t("details"))}</a>`;
  const d = s.drift || {};
  const day = (x) => (x || "").slice(0, 10);
  const driftNote = (d.observed + d.declared === 0 && d.first_baseline_at)
    ? t("drift_baseline", { n: fmt(d.files_with_baseline), d: day(d.first_baseline_at), next: nextMonday(s.generated_at) })
    : t("drift_since", { d: day(d.first_baseline_at), o: fmt(d.observed), dd: fmt(d.declared) });
  const gb = (x) => Number(x).toLocaleString(LANG === "pt" ? "pt-BR" : "en", { maximumFractionDigits: 1 });
  const tb = s.tables || {};
  const formats = Object.entries(tb.by_format || {}).map(([k, f]) =>
    `${k.toUpperCase()} ${fmt(f.files)}` + (f.gb >= 0.05 ? ` (${gb(f.gb)} GB)` : "")).join(" · ");
  const cp = ((s.findings || {}).copies) || {};
  const filesNote = [formats, tb.declared_gb == null ? "" : t("files_size", { gb: gb(tb.declared_gb) }),
    tb.size_unknown ? t("files_unknown", { n: fmt(tb.size_unknown) }) : "",
    cp.files ? t("files_copies", { n: fmt(cp.files), gb: gb(cp.gb) })
      + (cp.identical || cp.different ? ` (${t("copies_checked", { i: fmt(cp.identical), d: fmt(cp.different) })})` : "") : ""]
    .filter(Boolean).join(" · ");
  const dc = ((s.findings || {}).dictionaries) || {};
  const dictTile = dc.total == null ? "" : tile(t("t_dicts"), fmt(dc.total), esc(t("dicts_note", {
    m: fmt(dc.machine_readable), r: fmt(dc.machine_readable_and_read), p: fmt(dc.human_readable), o: fmt(dc.orphans) }))
    + more("findings"));
  // the largest files still to read, the same name and size counted once (a file published twice)
  const big = [];
  for (const x of tb.queue_largest || []) {
    const same = big.find((b) => b.name === x.name && b.gb === x.gb);
    same ? same.n++ : big.push({ ...x, n: 1 });
  }
  const queueTile = !tb.queue_remaining ? "" : tile(t("t_queue"), fmt(tb.queue_remaining),
    (tb.queue_gb == null ? "" : esc(t("queue_note", { gb: gb(tb.queue_gb) })))
    + (big.length ? `<br>${esc(t("queue_big"))}: ` + big.map((x) => esc(`${x.name} (${gb(x.gb)} GB)${x.n > 1 ? ` ×${x.n}` : ""}`)).join(" · ") : ""));
  el("tiles").innerHTML = [
    tile(t("t_datasets"), fmt(s.datasets.total)),
    dictTile,
    tile(t("t_files"), fmt(tb.total), esc(filesNote)),
    tile(t("t_checked"), fmt(c.read), esc(t("read_note", { n: fmt(c.read), t: fmt(c.files), nd: fmt(c.not_downloaded),
      e: fmt(c.empty), nt: fmt(c.not_tabular), tl: fmt(c.too_large || 0) })) + more("coverage"), c.files ? c.read / c.files : 0),
    queueTile,
    tile(t("t_conf"), pct(s.l1_rate), esc(t("conf_tile_note", { c: fmt(c.conform), k: fmt(c.checked), w: fmt(c.read_without_schema) }))
      + ` · ${esc(t("threshold", { t: pct(s.method.l1_pass_threshold) }))}` + more("coverage"), s.l1_rate ?? 0),
    tile(t("t_drift"), fmt(d.observed + d.declared), esc(driftNote) + more("drift")),
  ].join("");
}

// --- the verdict, under the tiles: pass or not, and why -----------------------------------
function renderVerdict(s) {
  const box = el("verdict");
  box.hidden = s.l1_rate == null;
  if (box.hidden) return;
  const c = s.coverage || {};
  const vars = { r: pct(s.l1_rate), c: fmt(c.conform), k: fmt(c.checked), th: pct(s.method.l1_pass_threshold) };
  box.className = `verdict ${s.l1_pass ? "good" : "bad"}`;
  box.innerHTML = `<span class="status ${s.l1_pass ? "good" : "bad"}">${s.l1_pass ? "✓" : "✗"} ${esc(t(s.l1_pass ? "pass" : "fail"))}</span> `
    + esc(t(s.l1_pass ? "verdict_pass" : "verdict_fail", vars))
    + ` <a class="more" href="#coverage">${esc(t("details"))}</a>`;
}

// --- reading and conformance ---------------------------------------------------------------
function renderCoverage(s) {
  const c = s.coverage || {};
  const steps = [["f_all", c.files], ["f_read", c.read], ["f_with_schema", c.checked], ["f_conform", c.conform]];
  const max = c.files || 1;
  el("funnel").innerHTML = `<div class="funnel">${steps.map(([k, n]) =>
    `<span>${esc(t(k))}</span><span class="bar"><span style="width:${((n || 0) / max) * 100}%"></span></span>`
    + `<span class="n">${fmt(n)} · ${pct((n || 0) / max)}</span>`).join("")}</div>`;
  // "reason · host": the reason in the page's language (HTTP codes stay as they are)
  const reason = (r) => (T[`rk_${r}`] || r);
  const notRead = {};
  for (const [k, n] of Object.entries(c.not_downloaded_by_host || {})) {
    const [r, host] = k.split(" · ");
    notRead[host && host !== "—" ? `${reason(r)} · ${host}` : reason(r)] = n;
  }
  if (c.empty) notRead[t("s_empty_f")] = c.empty;
  if (c.not_tabular) notRead[t("s_nottab")] = c.not_tabular;
  if (c.too_large) notRead[t("s_toolarge")] = c.too_large;
  const notConform = {
    [t("nc_missing")]: c.fail_missing_fields, [t("nc_undeclared")]: c.fail_undeclared_columns,
    [t("nc_cells", { r: pct(s.method.l1_max_error_rate) })]: c.fail_cells_over_limit,
    [`↳ ${t("nc_only_cells")}`]: c.fail_only_cells,
  };
  el("coverage-panels").innerHTML = `<div class="panel"><h3>${esc(t("p_notread"))}</h3>${bars(notRead)}</div>`
    + `<div class="panel"><h3>${esc(t("p_notconform"))}</h3>${bars(notConform)}<p class="small muted">${esc(t("nc_overlap"))}</p></div>`;
  const u = DATA.unreadable || [];
  el("unreadable-wrap").hidden = !u.length;
  el("unreadable").innerHTML = `<thead><tr><th>${esc(t("col_dataset"))}</th><th>${esc(t("u_file"))}</th>`
    + `<th>${esc(t("u_reason"))}</th><th>${esc(t("u_host"))}</th></tr></thead><tbody>`
    + u.map((x) => `<tr><td><a href="#" data-open="${esc(x.dataset)}">${esc(x.title)}</a></td>`
      + `<td><a href="${esc(x.url)}" rel="noopener">${esc(x.file)}</a></td><td title="${esc(x.detail)}">${esc(T[`rk_${x.reason}`] || x.reason)}</td>`
      + `<td>${esc(x.host || "—")}</td></tr>`).join("") + "</tbody>";
  el("unreadable").querySelectorAll("a[data-open]").forEach((a) => a.addEventListener("click", (ev) => {
    ev.preventDefault();
    OPEN.add(a.dataset.open);
    renderDatasets();
    document.getElementById("datasets").scrollIntoView();
  }));
  // drift
  const d = s.drift || {};
  const day = (x) => (x || "").slice(0, 10);
  const events = DATA.drift_events || [];
  el("drift-text").textContent = events.length ? t("drift_since", { d: day(d.first_baseline_at), o: fmt(d.observed), dd: fmt(d.declared) })
    : (d.files_with_baseline && day(d.first_baseline_at) === day(d.last_observed_at))
      ? t("drift_none_yet", { n: fmt(d.files_with_baseline), d: day(d.first_baseline_at), next: nextMonday(s.generated_at) })
      : t("drift_none", { n: fmt(d.files_with_baseline), d: day(d.first_baseline_at) });
  el("drift-table").innerHTML = events.length ? `<thead><tr><th>${esc(t("d_when"))}</th><th>${esc(t("d_kind"))}</th>`
    + `<th>${esc(t("u_file"))}</th><th>${esc(t("d_changes"))}</th></tr></thead><tbody>`
    + events.slice().reverse().map((e) => `<tr><td>${esc(day(e.at))}</td><td>${esc(e.kind)}</td>`
      + `<td><a href="?resource=${esc(e.resource_id)}">${esc(e.file || e.resource_id)}</a></td>`
      + `<td>${e.changes.map((x) => `<code>${esc(x)}</code>`).join(" ")}</td></tr>`).join("") + "</tbody>" : "";
}

function renderProgress(s) {
  const rows = DATA.history || [];
  const box = el("progress-chart");
  const day = (x) => (x || "").slice(0, 10);
  if (rows.length < 2) {
    box.innerHTML = `<p class="muted">${esc(t("pg_first", { d: day((rows[0] || {}).at || s.census_at), next: nextMonday(s.generated_at) }))}</p>`;
  } else {
    const series = [
      { key: "pg_conform", color: "var(--series-1)", value: (r) => (r.l1_rate == null ? null : r.l1_rate * 100) },
      { key: "pg_checkable", color: "var(--series-2)", value: (r) => (r.files ? (r.checked / r.files) * 100 : null) },
    ];
    const W = 720, H = 220, L = 40, R = 150, T = 12, B = 28;
    const x = (i) => L + (rows.length === 1 ? 0 : (i * (W - L - R)) / (rows.length - 1));
    const y = (v) => T + (1 - v / 100) * (H - T - B);
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t("progress_h"))}">`;
    for (const g of [0, 25, 50, 75, 100]) {
      svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}"/><text class="axis-label" x="${L - 6}" y="${y(g) + 4}" text-anchor="end">${g}%</text>`;
    }
    const step = Math.max(1, Math.ceil(rows.length / 8));
    rows.forEach((r, i) => {
      if (i % step === 0 || i === rows.length - 1) svg += `<text class="axis-label" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(day(r.at).slice(5))}</text>`;
    });
    for (const sr of series) {
      const pts = rows.map((r, i) => [x(i), sr.value(r)]).filter(([, v]) => v != null);
      svg += `<polyline class="line" stroke="${sr.color}" points="${pts.map(([px, v]) => `${px},${y(v)}`).join(" ")}"/>`;
      svg += pts.map(([px, v]) => `<circle class="dot" r="4" cx="${px}" cy="${y(v)}" fill="${sr.color}"/>`).join("");
      const [lx, lv] = pts[pts.length - 1] || [0, 0];
      svg += `<text class="label" x="${lx + 8}" y="${y(lv) + 4}">${pct(lv / 100)}</text>`;
    }
    svg += `<line class="cross" id="pg-cross" y1="${T}" y2="${H - B}" x1="0" x2="0" visibility="hidden"/>`;
    const band = (W - L - R) / Math.max(1, rows.length - 1);
    rows.forEach((r, i) => {
      svg += `<rect data-i="${i}" x="${x(i) - band / 2}" y="${T}" width="${band}" height="${H - T - B}" fill="transparent"/>`;
    });
    svg += "</svg>";
    box.innerHTML = `<div class="chart-legend">${series.map((sr) => `<span><span class="key" style="background:${sr.color}"></span>${esc(t(sr.key))}</span>`).join("")}</div>`
      + `<div class="chart">${svg}</div>`;
    const cross = box.querySelector("#pg-cross");
    box.querySelectorAll("rect[data-i]").forEach((rect) => {
      const r = rows[Number(rect.dataset.i)];
      const html = `<strong>${esc(day(r.at))}</strong><br>` + series.map((sr) => `${esc(t(sr.key))}: ${pct(sr.value(r) == null ? null : sr.value(r) / 100)}`).join("<br>")
        + `<br>${esc(t("pg_fixed"))} ${fmt(r.fixed)} · ${esc(t("pg_broken"))} ${fmt(r.broken)}`;
      bindTip(rect, html);
      rect.addEventListener("mouseenter", () => { cross.setAttribute("x1", x(Number(rect.dataset.i))); cross.setAttribute("x2", x(Number(rect.dataset.i))); cross.setAttribute("visibility", "visible"); });
      rect.addEventListener("mouseleave", () => cross.setAttribute("visibility", "hidden"));
    });
  }
  const cols = ["pg_date", "pg_files", "pg_read", "pg_checked", "pg_conf", "pg_fixed", "pg_broken", "pg_new", "pg_gone", "pg_drift"];
  el("progress-table").innerHTML = rows.length ? `<thead><tr>${cols.map((c, i) => `<th${i ? ' class="num"' : ""}>${esc(t(c))}</th>`).join("")}</tr></thead><tbody>`
    + rows.slice().reverse().map((r, i, all) => {
      const before = all[i + 1];
      const drift = (r.drift_observed + r.drift_declared) - (before ? before.drift_observed + before.drift_declared : 0);
      return `<tr><td>${esc(day(r.at))}${r.commit ? ` <code>${esc(r.commit)}</code>` : ""}</td><td class="num">${fmt(r.files)}</td>`
        + `<td class="num">${fmt(r.read)}</td><td class="num">${fmt(r.checked)}</td><td class="num">${fmt(r.conform)} (${pct(r.l1_rate)})</td>`
        + `<td class="num">${fmt(r.fixed)}</td><td class="num">${fmt(r.broken)}</td><td class="num">${fmt(r.new_files)}</td>`
        + `<td class="num">${fmt(r.gone_files)}</td><td class="num">${fmt(drift)}</td></tr>`;
    }).join("") + "</tbody>" : "";
}

function renderSimilar() {
  const rows = DATA.similar_names || [];
  el("similar").hidden = !rows.length;
  if (!rows.length) return;
  const draw = () => {
    const q = el("similar-search").value.trim().toLowerCase();
    const shown = rows.filter((x) => !q || [x.title, x.dataset, x.file, x.declared, x.column]
      .some((v) => (v || "").toLowerCase().includes(q)));
    el("similar-count").textContent = t("similar_count", { n: fmt(shown.length), f: fmt(new Set(shown.map((x) => x.id)).size) });
    el("similar-table").innerHTML = `<thead><tr><th>${esc(t("col_dataset"))}</th><th>${esc(t("u_file"))}</th>`
      + `<th>${esc(t("s_declared"))}</th><th>${esc(t("s_column"))}</th><th class="num">${esc(t("s_similarity"))}</th>`
      + `<th>${esc(t("s_source"))}</th></tr></thead><tbody>`
      + shown.map((x) => `<tr><td>${esc(x.title)}</td><td><a href="?resource=${esc(x.id)}">${esc(x.file)}</a></td>`
        + `<td><code>${esc(x.declared)}</code></td><td><code>${esc(x.column)}</code></td>`
        + `<td class="num">${pct(x.similarity)}</td><td>${esc(x.schema_kind || "—")}</td></tr>`).join("") + "</tbody>";
  };
  el("similar-search").addEventListener("input", draw);
  draw();
}

function schemaLinks(files) {
  return Object.entries(files || {}).map(([kind, path]) =>
    `<a href="${repo()}/blob/main/${encodeURI(path)}" rel="noopener">${esc(kind)}</a>`).join(" · ") || "—";
}

function renderPdf() {
  const rows = DATA.pdf || [];
  el("pdf").hidden = !rows.length;
  if (!rows.length) return;
  const prs = `${repo()}/pulls?q=is%3Apr+schemas+suggested`;
  el("pdf-table").innerHTML = `<thead><tr><th>${esc(t("col_dataset"))}</th><th>${esc(t("x_pdf"))}</th>`
    + `<th>${esc(t("x_outcome"))}</th><th>${esc(t("x_stage"))}</th><th>${esc(t("k_recall"))}</th>`
    + `<th>${esc(t("k_precision"))}</th><th>${esc(t("x_schema"))}</th><th>${esc(t("x_typos"))}</th>`
    + `<th>${esc(t("x_by_position"))}</th></tr></thead><tbody>`
    + rows.map((x) => {
      const schema = x.schema && x.schema_status !== "suggested"
        ? `<a href="${repo()}/blob/main/${encodeURI(x.schema)}" rel="noopener">${esc(x.schema_status || "schema")} ↗</a>`
        : x.outcome === "suggested" ? `<a href="${prs}" rel="noopener">${esc(t("open_pr"))}</a>` : "—";
      const typos = Object.entries(x.similar_names || {}).map(([a, b]) => `<code>${esc(a)}</code> → <code>${esc(b)}</code>`).join("<br>");
      const moved = Object.entries(x.by_position || {}).map(([a, b]) =>
        `<code>${esc(a)}</code> <span class="muted">(PDF)</span> × <code>${esc(b)}</code> <span class="muted">(${esc(t("x_file"))})</span>`).join("<br>");
      return `<tr><td><a href="#" data-open="${esc(x.dataset)}">${esc(x.title)}</a></td>`
        + `<td><a href="${esc(x.url)}" rel="noopener">${esc(x.dictionary)}</a></td>`
        + `<td>${esc(t(`o_${x.outcome}`))}</td><td>${esc(x.stage ? (x.stage === "llm" ? `LLM (${x.model || "?"})` : t("stage_det")) : "—")}</td>`
        + `<td class="num">${pct(x.recall)}</td><td class="num">${pct(x.precision)}</td><td>${schema}</td><td>${typos || "—"}</td><td class="small">${moved || "—"}</td></tr>`;
    }).join("") + "</tbody>";
  el("pdf-table").querySelectorAll("a[data-open]").forEach((a) => a.addEventListener("click", (ev) => {
    ev.preventDefault();
    OPEN.add(a.dataset.open);
    renderDatasets();
    document.getElementById("datasets").scrollIntoView();
  }));
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
      seg.setAttribute("role", "button");
      seg.addEventListener("click", () => filterLevel(name === t("u_files") ? "f" : "d", l));
      seg.addEventListener("keydown", (ev) => { if (ev.key === "Enter") filterLevel(name === t("u_files") ? "f" : "d", l); });
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
    `<li data-level="${l}" tabindex="0"><span class="swatch" style="background:${levelColor(l)}"></span>${esc(label)}`
    + ` (${fmt(s.datasets.by_level[l])} · ${fmt(s.tables.by_level[l])})</li>`).join("");
  el("maturity-legend").querySelectorAll("li").forEach((li) =>
    li.addEventListener("click", () => filterLevel("d", Number(li.dataset.level))));
}

function filterLevel(scope, level) {
  el("level-filter").value = `${scope}${level}`;
  el("search").value = "";
  renderDatasets();
  el("datasets-head").scrollIntoView({ behavior: "smooth", block: "start" });
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

function renderFindings(f, net, dist) {
  const d = f.dictionaries, ty = f.types, vs = f.files_vs_dictionaries, fi = f.files, pdf = f.pdf_extraction;
  const nt = (net || {}).total || {};
  const num1 = (x) => (x == null ? "—" : Number(x).toLocaleString(LANG === "pt" ? "pt-BR" : "en", { maximumFractionDigits: 1 }));
  const label = (prefix) => (k) => T[`${prefix}_${k}`] || I18N.en[`${prefix}_${k}`] || k;
  const panels = [
    [t("p_dicts"), kv([[t("k_total"), fmt(d.total)], [t("k_machine"), fmt(d.machine_readable)],
      [t("k_read"), fmt(d.machine_readable_and_read)], [t("k_human"), fmt(d.human_readable)],
      [t("k_orphans"), fmt(d.orphans)], [t("k_ids"), fmt(d.declaring_resource_ids)],
      [t("k_broken"), fmt(d.broken_declared_links)], [t("k_other_ds"), fmt(d.naming_another_dataset)]]) + bars(d.by_format)],
    [t("p_unread"), bars(d.unreadable_by_reason, label("r"))
      + (d.unreachable ? `<p class="small muted">${esc(t("k_unreachable").replace("{n}", fmt(d.unreachable)))}</p>` : "")],
    [t("p_links"), bars(f.links.by_method, label("m"))],
    [t("p_types"), kv([[t("k_fields"), fmt(ty.fields_declared)], [t("k_spell"), fmt(ty.distinct_spellings)],
      [t("k_recog"), pct(ty.fields_with_recognised_type)], [t("k_dates"), pct(ty.date_fields_with_declared_format)]])
      + `<div class="chips">${Object.entries(ty.top_spellings || {}).map(([k, n]) => `<span class="chip">${esc(k || "∅")} · ${fmt(n)}</span>`).join("")}</div>`
      + (ty.unrecognised_spellings?.length ? `<p class="small muted">${esc(t("k_unrec"))}: ${ty.unrecognised_spellings.map((x) => `<code>${esc(x)}</code>`).join(" ")}</p>` : "")],
    [t("p_vs"), kv([[t("k_checked"), fmt(vs.checked)], [t("k_missing"), fmt(vs.with_declared_fields_missing)],
      [t("k_undecl"), fmt(vs.with_undeclared_columns)], [t("k_spelling"), fmt(vs.with_spelling_differences)],
      [t("k_typos"), fmt(vs.with_similar_names)]])
      + `<p class="small muted">${esc(t("k_inferred"))}</p>` + bars(vs.formats_inferred_from_data)],
    [t("p_files"), kv([[t("k_validated"), fmt(fi.validated)], [t("k_decode"), fmt(fi.with_decode_errors)],
      [t("k_ragged"), fmt(fi.with_ragged_rows)], [t("k_multi"), fmt(fi.zips_with_several_headers)],
      [t("k_noname"), fmt(fi.with_columns_without_name)],
      [t("k_nottables"), fmt(fi.not_tables)],
      [t("k_dist"), `${fmt((dist || {}).compared)} · ${fmt((dist || {}).same_columns)} · ${fmt((dist || {}).spelling_only)}`],
      [t("k_nottab"), fmt(fi.not_tabular)], [t("k_gb"), num1(nt.gb)], [t("k_minutes"), num1(nt.minutes)],
      [t("k_mbs"), num1(nt.end_to_end_mb_s)], [t("k_netshare"), pct(nt.network_share)], [t("k_ttfb"), num1(nt.first_byte_s_median)],
      [t("k_reqfail"), fmt(Object.values(nt.request_failures || {}).reduce((a, b) => a + b, 0))]])
      + `<p class="small muted">${esc(t("k_encodings"))}: ${Object.entries(fi.encodings || {}).map(([k, n]) => `<code>${esc(k)}</code> ${fmt(n)}`).join(" · ") || "—"}<br>`
      + `${esc(t("k_formats"))}: ${Object.entries(fi.formats || {}).map(([k, n]) => `<code>${esc(k)}</code> ${fmt(n)}`).join(" · ") || "—"}<br>`
      + `${esc(t("k_delims"))}: ${Object.entries(fi.delimiters || {}).map(([k, n]) => `<code>${esc(k === "\t" ? "TAB" : k)}</code> ${fmt(n)}`).join(" · ") || "—"}</p>`
      + `<p class="small muted">${esc(t("k_unreach"))}</p>` + bars(fi.unreachable_by_reason)],
    [t("p_pdf"), kv([[t("k_pdflinked"), fmt(pdf.pdf_dictionaries_linked)], [t("k_processed"), fmt(pdf.processed)],
      [t("k_pdftypos"), fmt(pdf.with_similar_names)]])
      + `<table class="mini"><thead><tr><th>${esc(t("k_stage"))}</th><th>${esc(t("k_n"))}</th><th>${esc(t("k_recall"))}</th>`
      + `<th>${esc(t("k_precision"))}</th><th>${esc(t("k_em"))}</th><th>${esc(t("k_ls"))}</th></tr></thead><tbody>`
      + [["stage_det", pdf.deterministic], ["stage_llm", pdf.llm]].map(([k, r]) =>
        `<tr><td>${esc(t(k))}</td><td>${fmt(r.with_oracle)}</td><td>${pct(r.recall)}</td><td>${pct(r.precision)}</td>`
        + `<td>${pct(r.exact_match)}</td><td>${pct(r.levenshtein)}</td></tr>`).join("") + "</tbody></table>"
      + `<p class="small muted">${esc(t("outcomes"))}: ${Object.entries(pdf.by_outcome || {}).map(([k, n]) => `${esc(k)} ${fmt(n)}`).join(" · ") || "—"}</p>`],
  ];
  el("findings").innerHTML = panels.map(([h, body]) => `<div class="panel"><h3>${esc(h)}</h3>${body}</div>`).join("");
}

// --- file delivery -------------------------------------------------------------------
// The reference of each observation (fixed addresses: nothing here comes from the data).
const RFC = "https://www.rfc-editor.org/rfc/rfc9110#section-";
const DELIVERY_REFS = {
  "broken-links": ["W3C, Data on the Web Best Practices", "https://www.w3.org/TR/dwbp/"],
  "redirect-loops": ["RFC 9110, §15.4", RFC + "15.4"],
  "byte-ranges": ["RFC 9110, §14", RFC + "14"],
  validators: ["RFC 9110, §8.8, §13", RFC + "8.8"],
  "media-type": ["RFC 9110, §8.3", RFC + "8.3"],
  length: ["RFC 9110, §8.6", RFC + "8.6"],
};

function renderDelivery(dv) {
  const box = el("delivery");
  if (!dv || !Object.keys(dv.hosts || {}).length) { box.innerHTML = `<p class="muted small">${esc(t("none"))}</p>`; return; }
  const ratio = (n, of) => (of ? `${fmt(n)} / ${fmt(of)}` : "—");
  const rows = Object.entries(dv.hosts).map(([host, h]) =>
    `<tr><td><code>${esc(host)}</code></td><td>${(h.served_by || []).map((s) => `<code>${esc(s)}</code>`).join(" ") || "—"}`
    + `${h.server?.length ? `<br><span class="muted">${esc(h.server.join(", "))}</span>` : ""}</td>`
    + `<td>${esc(t(`rg_${h.range}`))}</td><td>${ratio(h.without_validator, h.of)}</td><td>${ratio(h.generic_type, h.typed)}</td>`
    + `<td>${fmt(h.broken_links)}</td><td>${fmt(h.redirect_loops)}</td></tr>`).join("");
  const obs = (dv.suggestions || []).map((s) => {
    const [label, url] = DELIVERY_REFS[s.id] || ["", ""];
    const text = t(`sg_${s.id}`, { host: s.host, n: fmt(s.n), of: fmt(s.of), types: (s.types || []).join(", ") });
    return `<li>${esc(text)}${url ? ` <a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)} ↗</a>` : ""}</li>`;
  }).join("");
  box.innerHTML = `<div class="table-wrap"><table class="mini"><thead><tr><th>${esc(t("dv_host"))}</th><th>${esc(t("dv_served"))}</th>`
    + `<th>${esc(t("dv_range"))}</th><th>${esc(t("dv_validators"))}</th><th>${esc(t("dv_type"))}</th>`
    + `<th>${esc(t("dv_broken"))}</th><th>${esc(t("dv_loops"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`
    + `<h3>${esc(t("dv_obs"))}</h3>` + (obs ? `<ul class="obs">${obs}</ul>` : `<p class="muted small">${esc(t("dv_none"))}</p>`);
}

// --- datasets ----------------------------------------------------------------------
function bytes(n) {
  if (!n) return "";
  const [v, u] = n >= 1e9 ? [n / 1e9, "GB"] : n >= 1e6 ? [n / 1e6, "MB"] : [n / 1e3, "KB"];
  return `${v.toLocaleString(LANG === "pt" ? "pt-BR" : "en", { maximumFractionDigits: v < 10 ? 1 : 0 })} ${u}`;
}

function levelBadge(l) {
  return l == null ? "—" : `<span class="level"><span class="swatch" style="background:${levelColor(l)}"></span>${l}</span>`;
}

function fileDetail(f) {
  const c = f.conformance;
  const queued = f.queued ? [t("s_queued"), bytes(f.size)].filter(Boolean).join(" · ") : "";
  const status = [f.status ? t(`s_${f.status}`) : queued ? "" : t("s_pending"), f.sampled ? t("s_sampled") : "", queued]
    .filter(Boolean).join(" · ");
  const dm = f.dictionary;
  const dict = dm ? `${dm.url ? `<a href="${esc(dm.url)}" rel="noopener">${esc(dm.format || "")}</a>` : esc(dm.format || "")}`
    + ` · ${esc(t(`m_${(dm.method || "").replace("-", "_")}`))}`
    + (dm.page ? `<br><a class="small" href="${esc(dm.page)}" rel="noopener">${esc(t("dict_page"))}</a>` : "")
    : esc(t("m_none"));
  let conf = "—";
  let more = "";
  if (c) {
    conf = c.pass ? `<span class="status good">✓ ${esc(t("yes"))}</span>` : `<span class="status bad">✗ ${esc(t("no"))}</span>`;
    conf += ` <span class="muted">${pct(c.error_rate)}</span>`;
    const list = (key, items) => (items && items.length
      ? `<div class="small"><span class="muted">${esc(t(key))}:</span> ${items.slice(0, 30).map((x) => `<code>${esc(x)}</code>`).join(" ")}${items.length > 30 ? " …" : ""}</div>` : "");
    more += list("f_missing", c.missing) + list("f_undecl", c.undeclared)
      + list("f_spelling", Object.entries(c.spelling || {}).map(([a, b]) => `${a} → ${b}`))
      + list("f_typos", Object.entries(c.similar_names || {}).map(([a, b]) => `${a} → ${b}`));
    const errs = Object.entries(c.errors_by_field || {}).map(([field, kinds]) =>
      [field, Object.entries(kinds).map(([k, n]) => `${k} ${fmt(n)}`).join(", "), Object.values(kinds).reduce((a, b) => a + b, 0)])
      .sort((a, b) => b[2] - a[2]).slice(0, 8);
    if (errs.length) {
      more += `<div class="small muted">${esc(t("f_errors"))}:</div><ul class="errs small">`
        + errs.map(([field, kinds]) => `<li><code>${esc(field)}</code>: ${esc(kinds)}</li>`).join("") + "</ul>";
    }
  }
  if ((f.distributions || []).length) {
    more += `<div class="small"><span class="muted">${esc(t("f_dist"))}:</span> ` + f.distributions.map((d) => {
      const what = d.status !== "ok" ? t("d_notchecked") : d.same_columns ? t("d_same") : d.spelling_only ? t("d_spelling")
        : `${t("d_diff")} (${[d.missing && d.missing.length ? `${t("d_missing")} ${d.missing.join(", ")}` : "",
            d.extra && d.extra.length ? `${t("d_extra")} ${d.extra.join(", ")}` : ""].filter(Boolean).join("; ")})`;
      return `<code>${esc(d.format || "?")}</code> ${esc(what)}`;
    }).join(" · ") + "</div>";
  }
  if (f.error) more += `<div class="small muted">${esc(f.error)}</div>`;
  if (f.copy_of) {
    const first = (DATA.datasets.flatMap((d) => d.tables).find((x) => x.id === f.copy_of) || {}).name || f.copy_of;
    more += `<div class="small muted">${esc(t("f_copy", { f: first }) + (f.copy_failed ? ` · ${t("f_copy_failed")}` : ""))}</div>`;
  }
  return `<tr id="file-${esc(f.id)}"><td><a href="${esc(f.url)}" rel="noopener">${esc(f.name || f.id)}</a>${more}</td>`
    + `<td>${f.not_a_table ? "—" : levelBadge(f.level)}</td><td>${dict}</td><td class="small">${esc(f.schema_kind || "—")}<br>${schemaLinks(f.schema_files)}</td>`
    + `<td>${esc(status)}</td><td class="num">${fmt(f.rows)}</td><td>${conf}</td><td class="num">${fmt(f.drift_events)}</td></tr>`;
}

let DATA = null;
const OPEN = new Set();

function renderDatasets() {
  const q = el("search").value.trim().toLowerCase();
  const lf = el("level-filter").value;
  const scope = lf ? lf[0] : "", level = lf ? lf.slice(1) : "";
  const failing = el("only-failing").checked;
  const body = document.querySelector("#datasets tbody");
  const rows = [];
  for (const ds of DATA.datasets) {
    let files = ds.tables;
    if (failing) files = files.filter((f) => f.conformance && !f.conformance.pass);
    if (scope === "f") files = files.filter((f) => String(f.level) === level);
    const hit = !q || ds.name.toLowerCase().includes(q) || (ds.title || "").toLowerCase().includes(q)
      || files.some((f) => (f.name || "").toLowerCase().includes(q));
    if (!hit || (scope === "d" && String(ds.level) !== level) || ((failing || scope === "f") && !files.length)) continue;
    const ver = ds.tables.filter((f) => f.conformance);
    const ok = ver.filter((f) => f.conformance.pass);
    const dicts = ds.dictionaries.map((d) => `<a href="${esc(d.page || d.url)}" rel="noopener" title="${esc(d.name)}">`
      + `${esc(d.format)}</a>${d.readable === false ? " ✗" : ""}`).join(", ") || "—";
    rows.push(`<tr class="ds" data-name="${esc(ds.name)}" tabindex="0"><td><strong>${esc(ds.title)}</strong><br>`
      + `<a class="small" href="${esc(ds.url)}" rel="noopener">${esc(ds.name)}</a></td><td>${levelBadge(ds.level)}</td>`
      + `<td class="num">${fmt(ds.tables.length)}</td><td class="num">${ver.length ? `${fmt(ok.length)}/${fmt(ver.length)}` : "—"}</td>`
      + `<td class="small">${dicts}</td></tr>`);
    if (OPEN.has(ds.name) || scope === "f") {      // a filter on files shows the matching files right away
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

// --- a run in progress -------------------------------------------------------------
// Read by the browser from GitHub's public API (no token: 60 requests an hour per visitor, so every
// 5 minutes). The job that downloads the files has no write access to the repository by design, so
// what it is doing is known from the step it is in, not from a file it writes.
const LIVE = { since: null, what: "", url: "" };

function liveWhat(job, step) {
  const n = `${job ? job.name : ""} ${step ? step.name : ""}`;
  if (!job || job.status === "queued" || job.status === "waiting") return "live_wait";
  if (/publish/.test(n)) return "live_publish";
  if (/Survey/.test(n)) return "live_survey";
  if (/stage 2|Ollama|Resolve the model/.test(n)) return "live_llm";
  if (/PDF dictionaries/.test(n)) return "live_pdf";
  if (/Validate files/.test(n)) return "live_validate";
  return "live_prep";
}

function duration(ms) {
  const m = Math.max(0, Math.floor(ms / 60000));
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`;
}

function drawLive() {
  const node = el("live");
  if (!LIVE.since) { node.hidden = true; return; }
  const at = new Date(LIVE.since);
  node.innerHTML = `<span class="dot" aria-hidden="true"></span><span>${esc(t("live_for", { what: t(LIVE.what), d: duration(Date.now() - at) }))}`
    + ` <span class="muted">(${esc(t("live_since", { t: at.toLocaleString(LANG === "pt" ? "pt-BR" : "en", { dateStyle: "short", timeStyle: "short" }) }))})</span></span>`
    + ` <a href="${esc(LIVE.url)}" target="_blank" rel="noopener">${esc(t("live_run"))} ↗</a>`;
  node.hidden = false;
}

async function refreshLive() {
  const m = repo().match(/github\.com\/([^/]+)\/([^/]+)/);
  if (!m) return;
  try {
    const api = `https://api.github.com/repos/${m[1]}/${m[2]}/actions`;
    const runs = await (await fetch(`${api}/workflows/layer1.yml/runs?per_page=1`)).json();
    const run = (runs.workflow_runs || [])[0];
    if (!run || run.status === "completed") { LIVE.since = null; drawLive(); return; }
    const jobs = (await (await fetch(`${api}/runs/${run.id}/jobs`)).json()).jobs || [];
    const job = jobs.find((j) => j.status === "in_progress") || jobs.find((j) => j.status !== "completed");
    const step = job && (job.steps || []).find((s) => s.status === "in_progress");
    LIVE.what = liveWhat(job, step);
    LIVE.since = (step && step.started_at) || (job && job.started_at) || run.run_started_at || run.created_at;
    LIVE.url = (job && job.html_url) || run.html_url;
  } catch (e) {
    return;           // no answer (offline, rate limit): the badge keeps what it had
  }
  drawLive();
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
  renderVerdict(s);
  renderMaturity(s);
  renderCoverage(s);
  renderProgress(s);
  renderSimilar();
  renderPdf();
  renderFindings(s.findings, s.network, s.distributions);
  renderDelivery(s.findings.delivery);
  // ?level=d2 / f0 (same as clicking a maturity band) filters the table
  const lvl = new URLSearchParams(location.search).get("level");
  if (lvl && /^[df][0-4]$/.test(lvl)) el("level-filter").value = lvl;
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
  refreshLive();
  setInterval(refreshLive, 5 * 60 * 1000);
  setInterval(drawLive, 60 * 1000);
  const m = s.method || {};
  const opt = (k, v) => (v == null ? "" : `, ${k}=${v}`);
  el("footer").innerHTML = esc(t("footer", { m: `L1_MAX_ERROR_RATE=${m.l1_max_error_rate}, L1_PASS_THRESHOLD=${m.l1_pass_threshold}, ROTATION_DAYS=${m.rotation_days}, LLM=${m.llm_model}`
    + opt("ZIP_DOCUMENTS_SAMPLE", m.zip_documents_sample) + opt("ZIP_STOP_AT_SAMPLE", m.zip_stop_at_sample)
    + opt("COPIES_ONCE", m.copies_once) }))
    + ` <a href="${repo()}/blob/main/results/layer1_summary.json">results/layer1_summary.json</a>`;
}

main();
