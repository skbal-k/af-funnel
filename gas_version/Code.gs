var SPREADSHEET_ID = "1CH8lMnVTLVQGxRo7BEIJhinTvOTH5GUMwlsbBFm085w";

var REGIONS = {
  "🌎  LACA (All)":      { sheetTab: "LACA",           scaleFilter: "LATAM"  },
  "🇧🇷  Brazil":         { sheetTab: "BRAZIL",          scaleFilter: "BRAZIL" },
  "🇲🇽  Mexico":         { sheetTab: "MEXICO",          scaleFilter: "MEXICO" },
  "📈  LATAM-Growth":   { sheetTab: "GRW",   scaleFilter: "GROWTH" },
  "🌱  LATAM-Emerging": { sheetTab: "EMG",   scaleFilter: "EMERG"  }
};

var STAGES = ["Provisioned", "Discovery", "Agent Created", "Agent in Prod", "Used", "Consumed 50+", "Scale"];

function doGet(e) {
  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle("⚡ AF Implementation Funnel")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ── Funnel Table ───────────────────────────────────────────────────────────
function getFunnelData(regionName) {
  var cfg = REGIONS[regionName];
  if (!cfg) return { error: "Región no encontrada: " + regionName };
  try {
    var ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = ss.getSheetByName(cfg.sheetTab);
    if (!sheet) return { error: "No hay datos para '" + regionName + "'. Importá el CSV al Sheet primero." };
    var data    = sheet.getDataRange().getValues();
    var headers = data[0];

    var stageMap = {
      "Provisioned":   ["provisioned"],
      "Discovery":     ["discovery"],
      "Agent Created": ["agent created", "created"],
      "Agent in Prod": ["agent in prod", "activated"],
      "Used":          ["used"],
      "Consumed 50+":  ["consumed 50+", "consumed"],
    };
    var colIdx = {};
    for (var s in stageMap) {
      colIdx[s] = -1;
      for (var h = 0; h < headers.length; h++) {
        var hLower = String(headers[h]).toLowerCase().trim();
        for (var k = 0; k < stageMap[s].length; k++) {
          if (hLower.indexOf(stageMap[s][k]) >= 0) { colIdx[s] = h; break; }
        }
        if (colIdx[s] >= 0) break;
      }
    }

    var partners = [];
    for (var r = 1; r < data.length; r++) {
      var row     = data[r];
      var partner = String(row[0] || "").trim();
      if (!partner || partner.toLowerCase() === "no partner" || partner.toLowerCase() === "total") continue;
      var entry = { name: partner };
      for (var st in colIdx) {
        var ci    = colIdx[st];
        entry[st] = (ci >= 0) ? (parseInt(row[ci]) || 0) : 0;
      }
      partners.push(entry);
    }
    partners.sort(function(a, b) { return b["Provisioned"] - a["Provisioned"]; });
    partners = partners.slice(0, 11);

    // Scale desde Scale Clients sheet
    var scaleByPartner = {};
    try {
      var scaleSheet = ss.getSheetByName("Scale Clients");
      if (scaleSheet) {
        var scaleData = scaleSheet.getDataRange().getValues();
        for (var sr = 1; sr < scaleData.length; sr++) {
          var ou  = String(scaleData[sr][6] || "").toUpperCase(); // OU = col G
          var p   = String(scaleData[sr][12] || "").trim();       // Impl Partner = col M
          if (!ou.includes("LATAM")) continue;
          if (!p || p.toLowerCase() === "no partner") continue;
          p = p.replace(/ TECNOLOGIA LTDA dba EVERYMIND/gi,"").replace(/ TECNOLOGIA LTDA/gi,"")
               .replace(/ LLC/gi,"").replace(/ LTDA/gi,"").trim();
          scaleByPartner[p.toUpperCase()] = (scaleByPartner[p.toUpperCase()] || 0) + 1;
        }
      }
    } catch(e) {}

    for (var p = 0; p < partners.length; p++) {
      var pUp = partners[p].name.toUpperCase();
      var scaleVal = 0;
      for (var k in scaleByPartner) {
        if (pUp.indexOf(k) >= 0 || k.indexOf(pUp) >= 0) { scaleVal = scaleByPartner[k]; break; }
      }
      partners[p]["Scale"] = scaleVal;
    }

    return { partners: partners, stages: STAGES, region: regionName };
  } catch(e) {
    return { error: e.message };
  }
}

// ── LACA Overview ──────────────────────────────────────────────────────────
function getLacaOverviewData() {
  try {
    var ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = ss.getSheetByName("LACA_OVERVIEW");
    if (!sheet) return { error: "No hay datos de LACA Overview. Importá el CSV al Sheet primero." };
    var data    = sheet.getDataRange().getValues();
    if (data.length < 2) return { error: "Sheet LACA_OVERVIEW está vacía." };
    var headers = data[0];
    var rows    = [];
    for (var r = 1; r < data.length; r++) {
      var row = {};
      for (var c = 0; c < headers.length; c++) row[String(headers[c])] = data[r][c];
      rows.push(row);
    }
    return { rows: rows };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Scale Accounts ─────────────────────────────────────────────────────────
function getScaleAccounts() {
  try {
    var ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = ss.getSheetByName("SCALE_ACCOUNTS");
    if (!sheet) return { accounts: [] };
    var data    = sheet.getDataRange().getValues();
    if (data.length < 2) return { accounts: [] };
    var headers  = data[0];
    var accounts = [];
    for (var r = 1; r < data.length; r++) {
      var row = {};
      for (var c = 0; c < headers.length; c++) row[String(headers[c])] = data[r][c];
      accounts.push(row);
    }
    return { accounts: accounts };
  } catch(e) {
    return { error: e.message };
  }
}

function getRegions() {
  return Object.keys(REGIONS);
}
