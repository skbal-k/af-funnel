var SPREADSHEET_ID = "1CH8lMnVTLVQGxRo7BEIJhinTvOTH5GUMwlsbBFm085w";

var REGIONS = {
  "🌎  LACA (All)":      { sheetTab: "LACA",    scaleFilter: "LATAM"  },
  "🇧🇷  Brazil":         { sheetTab: "BRAZIL",  scaleFilter: "BRAZIL" },
  "🇲🇽  Mexico":         { sheetTab: "MEXICO",  scaleFilter: "MEXICO" },
  "📈  LATAM-Growth":   { sheetTab: "GRW",     scaleFilter: "GROWTH" },
  "🌱  LATAM-Emerging": { sheetTab: "EMG",     scaleFilter: "EMERG"  }
};

var STAGES = ["Provisioned", "Discovery", "Agent Created", "Agent in Prod", "Used", "Consumed 50+", "Scale"];

function doGet(e) {
  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle("⚡ AF Implementation Funnel")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    if (payload.action !== "syncData") {
      return ContentService.createTextOutput(JSON.stringify({ok: false, msg: "Acción desconocida"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    var data = payload.data;
    var updated = [];
    for (var tabName in data) {
      var rows = data[tabName];
      var sheet = ss.getSheetByName(tabName);
      if (!sheet) sheet = ss.insertSheet(tabName);
      sheet.clearContents();
      if (rows.length > 0) sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
      updated.push(tabName);
    }
    return ContentService.createTextOutput(JSON.stringify({ok: true, msg: "Tabs actualizadas: " + updated.join(", ")}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch(e) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, msg: e.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

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

    // Scale desde Scale Clients
    var scaleByPartner = {};
    try {
      var scaleSheet = ss.getSheetByName("Scale Clients");
      if (scaleSheet) {
        var scaleData = scaleSheet.getDataRange().getValues();
        for (var sr = 1; sr < scaleData.length; sr++) {
          var ou = String(scaleData[sr][6] || "").toUpperCase();
          var p  = String(scaleData[sr][12] || "").trim();
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

function getScaleAccounts() {
  try {
    var ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = ss.getSheetByName("Scale Clients");
    if (!sheet) return { accounts: [] };
    var data = sheet.getDataRange().getValues();
    if (data.length < 2) return { accounts: [] };

    // Detectar columnas por nombre — robusto ante cambios de orden (igual que Agent 1)
    var headers = data[0].map(function(h){ return String(h).trim().toLowerCase(); });
    function findCol(keywords) {
      for (var i = 0; i < headers.length; i++)
        for (var k = 0; k < keywords.length; k++)
          if (headers[i].indexOf(keywords[k]) >= 0) return i;
      return -1;
    }
    var iName    = findCol(["account name"]);                        if (iName    < 0) iName    = 1;
    var iOU      = findCol(["\" ou\"", " ou\t", " ou,"]);
    if (iOU < 0) { for (var i=0; i<headers.length; i++) { if (headers[i] === "ou") { iOU = i; break; } } }
                                                                     if (iOU      < 0) iOU      = 6;
    var iOU2     = findCol(["ou+2", "ou 2"]);                        if (iOU2     < 0) iOU2     = 8;
    var iAWU     = findCol(["awu", "agent awu", "action"]);          if (iAWU     < 0) iAWU     = 3;
    var iPartner = findCol(["impl partner", "implementation part"]);  if (iPartner < 0) iPartner = 12;

    var accounts = [];
    for (var r = 1; r < data.length; r++) {
      var row    = data[r];
      var ou     = String(row[iOU]  || "").toUpperCase();
      var ou2    = String(row[iOU2] || "");
      var awuRaw = String(row[iAWU] || "0").replace(/,/g,"");
      var awu    = parseInt(awuRaw) || 0;
      if (ou.indexOf("LATAM") < 0) continue;
      var partner = String(row[iPartner] || "").trim();
      partner = partner.replace(/ TECNOLOGIA LTDA dba EVERYMIND/gi,"")
                       .replace(/ TECNOLOGIA LTDA/gi,"").replace(/ LLC/gi,"")
                       .replace(/ LTDA/gi,"").trim();
      if (!partner) partner = "Direct";
      var region = "🌎 LATAM";
      if (ou2.indexOf("- BR -") >= 0 || ou2.indexOf("PS - BR") >= 0) region = "🇧🇷 Brazil";
      else if (ou2.indexOf("- MX -")  >= 0) region = "🇲🇽 Mexico";
      else if (ou2.indexOf("- GRW -") >= 0) region = "📈 Growth";
      else if (ou2.indexOf("- EMG")   >= 0) region = "🌱 Emerging";
      accounts.push({
        "Account":      String(row[iName] || ""),
        "Region":       region,
        "Impl Partner": partner,
        "AWUs":         awu
      });
    }
    accounts.sort(function(a,b){ return b.AWUs - a.AWUs; });
    return { accounts: accounts };
  } catch(e) {
    return { error: e.message, accounts: [] };
  }
}

function getRegions() {
  return Object.keys(REGIONS);
}
