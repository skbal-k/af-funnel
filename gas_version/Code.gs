var GITHUB_RAW = "https://raw.githubusercontent.com/skbal-k/af-funnel/main/output/";

var REGIONS = {
  "🌎  LACA (All)":      { csvFile: "gas_laca.csv"            },
  "🇧🇷  Brazil":         { csvFile: "gas_brazil.csv"          },
  "🇲🇽  Mexico":         { csvFile: "gas_mexico.csv"          },
  "📈  LATAM-Growth":   { csvFile: "gas_latam_growth.csv"    },
  "🌱  LATAM-Emerging": { csvFile: "gas_latam_emerging.csv"  }
};

var STAGES = ["Provisioned", "Discovery", "Agent Created", "Agent in Prod", "Used", "Consumed 50+", "Scale"];

function doGet(e) {
  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle("⚡ AF Implementation Funnel")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ── Fetch CSV from GitHub ──────────────────────────────────────────────────
function fetchCsv(filename) {
  var url = GITHUB_RAW + filename + "?t=" + new Date().getTime();
  var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) throw new Error("No se pudo cargar " + filename + " (HTTP " + resp.getResponseCode() + ")");
  return resp.getContentText("UTF-8");
}

function parseCsv(text) {
  var lines = text.trim().split("\n");
  if (lines.length < 2) return [];
  var headers = lines[0].split(",").map(function(h){ return h.trim().replace(/^"|"$/g,""); });
  var rows = [];
  for (var i = 1; i < lines.length; i++) {
    var vals = lines[i].split(",").map(function(v){ return v.trim().replace(/^"|"$/g,""); });
    var row = {};
    for (var j = 0; j < headers.length; j++) row[headers[j]] = vals[j] || "";
    rows.push(row);
  }
  return rows;
}

// ── Funnel Table ───────────────────────────────────────────────────────────
function getFunnelData(regionName) {
  var cfg = REGIONS[regionName];
  if (!cfg) return { error: "Región no encontrada: " + regionName };
  try {
    var csv  = fetchCsv(cfg.csvFile);
    var rows = parseCsv(csv);
    if (!rows.length) return { error: "Sin datos para " + regionName };

    // Calcular Scale desde scale accounts
    var scaleByPartner = {};
    try {
      var scaleCsv  = fetchCsv("gas_scale_accounts.csv");
      var scaleRows = parseCsv(scaleCsv);
      for (var s = 0; s < scaleRows.length; s++) {
        var p = (scaleRows[s]["Impl Partner"] || "").trim();
        if (p && p !== "Direct") scaleByPartner[p.toUpperCase()] = (scaleByPartner[p.toUpperCase()] || 0) + 1;
      }
    } catch(e) {}

    var partners = rows.slice(0, 11).map(function(row) {
      var entry = { name: row["Partner"] || "" };
      STAGES.forEach(function(st) { entry[st] = parseInt(row[st]) || 0; });
      // Buscar scale por nombre
      var pUp = entry.name.toUpperCase();
      var scaleVal = 0;
      for (var k in scaleByPartner) {
        if (pUp.indexOf(k) >= 0 || k.indexOf(pUp) >= 0) { scaleVal = scaleByPartner[k]; break; }
      }
      entry["Scale"] = scaleVal;
      return entry;
    });

    return { partners: partners, stages: STAGES, region: regionName };
  } catch(e) {
    return { error: e.message };
  }
}

// ── LACA Overview ──────────────────────────────────────────────────────────
function getLacaOverviewData() {
  try {
    var csv  = fetchCsv("gas_laca_overview.csv");
    var rows = parseCsv(csv);
    if (!rows.length) return { error: "Sin datos de LACA Overview. Corré el update script primero." };
    return { rows: rows };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Scale Accounts ─────────────────────────────────────────────────────────
function getScaleAccounts() {
  try {
    var csv      = fetchCsv("gas_scale_accounts.csv");
    var accounts = parseCsv(csv);
    return { accounts: accounts };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Metadata (last updated) ────────────────────────────────────────────────
function getMetadata() {
  try {
    var url  = GITHUB_RAW + "gas_metadata.json?t=" + new Date().getTime();
    var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    if (resp.getResponseCode() === 200) return JSON.parse(resp.getContentText());
    return {};
  } catch(e) {
    return {};
  }
}

function getRegions() {
  return Object.keys(REGIONS);
}
