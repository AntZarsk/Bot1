const SPREADSHEET_ID = "17EIx76oHsel7uPtHj5FyWuE8D-1sKAMNAc6PXZBhIgE";
const SHEET_NAME = "Sheet1";

function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({
      ok: true,
      message: "Google Sheets webhook is alive"
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
    const data = JSON.parse((e && e.postData && e.postData.contents) || "{}");

    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Дата та Час публікації",
        "Тема/Заголовок факту",
        "Повний текст поста",
        "Шлях до медіафайлу",
        "Telegram Message ID",
        "Статус",
        "Source",
        "Source ID"
      ]);
    }

    sheet.appendRow([
      data.published_at || "",
      data.title || "",
      data.caption || "",
      data.media_path || "",
      data.telegram_message_id || "",
      data.status || "",
      data.source || "",
      data.source_id || ""
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, message: "Row appended" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(error) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
