# Google Sheets logging via Apps Script webhook

This method removes the need for `service_account.json`.

## 1) Create an Apps Script bound to your spreadsheet

Open your Google Sheet, then:

- Extensions → Apps Script
- Delete any starter code
- Paste the script below
- Save it as e.g. `WorldFactsLogger`

## 2) Apps Script code

```javascript
function doPost(e) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    const data = JSON.parse(e.postData.contents);

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
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(error) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

## 3) Deploy as a web app

In Apps Script:

- Deploy → New deployment
- Select type: Web app
- Execute as: Me
- Who has access: Anyone
- Click Deploy

You will receive a URL like:

```text
https://script.google.com/macros/s/XXXXXXXXXXXXXXXXXXXX/exec
```

Copy that URL into `.env` as:

```env
GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/XXXXXXXXXXXXXXXXXXXX/exec
```

## 4) Test

Send a POST request from Python by running:

```bash
python -m app.main
```

If everything is configured, the script will append a row into the first sheet tab.
