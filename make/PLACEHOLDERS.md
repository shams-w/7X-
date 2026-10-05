# Blueprint placeholders — what to replace and where

After importing `7X_Executive_Connect.blueprint.json`, Make will show warnings on the modules
below. Open each module, pick the real value from the drop-down, and click **OK**.
Values chosen from a drop-down are always right; do not type IDs by hand unless Make asks.

| Placeholder | Where (module #) | What to choose |
|---|---|---|
| `EXCEL_CONNECTION_ID` | 2, 14, 15, 34, 35 and the error-handler Excel modules | **Connection** → *Add* → sign in with your 7X Microsoft 365 work account (ACTION REQUIRED). After that, pick the same connection everywhere. |
| `ONEDRIVE_OR_SHAREPOINT_DRIVE_ID` | same Excel modules | **Drive / Location** where `7X_Employees.xlsx` is stored (OneDrive for Business or the SharePoint site) |
| `SPREADSHEET_ID` | same Excel modules | **Workbook** → browse to `7X_Employees.xlsx` |
| `WHATSAPP_CONNECTION_ID` | 12, 32 | **Connection** → *Add* → Connection type **Coexistence** (see docs/META_SETUP_COEXISTENCE.md) |
| `WHATSAPP_PHONE_NUMBER_ID` | 12, 32 | **Sender / Phone number** → the official 7X number |
| `DATASTORE_ID` | 10, 11, 13, 30, 31, 33 and the error-handler delete modules | **Data store** → `7X_Event_Log` |
| `TEST_PHONE_NUMBER` | 1 (CONFIG) | Your own mobile in `+9715XXXXXXXX` format |
| `APP_MODE` | 1 (CONFIG) | Leave `TEST` until the Production Launch Checklist is complete |

Worksheet names (`Employees`, `Event_Log`) are already filled in. They must match the tab names in the workbook.

**After replacing:** right-click module 2 → **Run this module only** and check that the output
shows your columns. Then check module 3: `employee_id`, `name`, `birthday_mmdd` and the others must
show real values. If a field is empty, re-map it from module 2's output by clicking the field.
