"""Generate the importable Make.com blueprint for 7X Executive Connect.

    python make/build_blueprint.py   ->  make/7X_Executive_Connect.blueprint.json

The blueprint contains PLACEHOLDERS (e.g. EXCEL_CONNECTION_ID) because the real IDs
only exist after 7X connects its own accounts in Make. See make/PLACEHOLDERS.md.

Design principle: module 3 ("Employee row") is the ONLY place that reads Excel
columns. Every later module uses its clean variable names, so if Make shows the
Excel columns differently, you fix one module and nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "7X_Executive_Connect.blueprint.json"

# ------------------------------------------------------------------ placeholders
EXCEL_CONN = "EXCEL_CONNECTION_ID"
WHATSAPP_CONN = "WHATSAPP_CONNECTION_ID"
DATASTORE = "DATASTORE_ID"
DRIVE_ID = "ONEDRIVE_OR_SHAREPOINT_DRIVE_ID"
SPREADSHEET = "SPREADSHEET_ID"
PHONE_NUMBER_ID = "WHATSAPP_PHONE_NUMBER_ID"
TEST_PHONE = "TEST_PHONE_NUMBER"

# Module identifiers (Make internal names). Verified display names in brackets.
M_SET_VARS = "util:SetVariables"                          # [Tools > Set multiple variables]
M_ROUTER = "builtin:BasicRouter"                          # [Flow control > Router]
M_IGNORE = "builtin:Ignore"                               # [Error handler > Ignore]
M_DS_GET = "datastore:GetRecord"                          # [Data store > Get a record]
M_DS_ADD = "datastore:AddRecord"                          # [Data store > Add/replace a record]
M_DS_DEL = "datastore:DeleteRecord"                       # [Data store > Delete a record]
M_XL_LIST = "microsoft-excel:listWorksheetRows"           # [Microsoft 365 Excel > List Worksheet Rows]
M_XL_UPDATE = "microsoft-excel:updateWorksheetRow"        # [Microsoft 365 Excel > Update a Worksheet Row]
M_XL_ADD = "microsoft-excel:addWorksheetRow"              # [Microsoft 365 Excel > Add a Worksheet Row]
M_WA_TEMPLATE = "whatsapp-business-cloud:sendTemplateMessage"  # [WhatsApp Business Cloud > Send a Template Message]

# Employees sheet column order (A..R) created by scripts/create_sample_spreadsheet.py
EXCEL_COLUMNS = [
    "Employee_ID", "Name", "Phone", "Birthday", "Joining_Date", "WhatsApp_Consent", "Active",
    "Language", "Birthday_Sent_Year", "Anniversary_Sent_Year", "Last_Message_Type",
    "Last_Message_Date", "Send_Status", "Error_Message", "Birthday_MMDD", "Joining_MMDD",
    "Joining_Year", "Row_No",
]
EVENT_LOG_COLUMNS = ["Event_ID", "Employee_ID", "Event_Type", "Event_Year", "Scheduled_Date",
                     "Mode", "Recipient", "Message_ID", "Status", "Created_At", "Sent_At", "Error"]


def col_index(name: str) -> str:
    return str(EXCEL_COLUMNS.index(name))


def xl(name: str) -> str:
    """Reference to a column of the current Excel row bundle (module 2)."""
    return "{{2.`" + col_index(name) + "`}}"


def designer(x: int, y: int) -> dict:
    return {"designer": {"x": x, "y": y}}


def cond(a: str, op: str, b: str | None = None) -> dict:
    c = {"a": a, "o": op}
    if b is not None:
        c["b"] = b
    return c


def excel_params() -> dict:
    return {"__IMTCONN__": EXCEL_CONN}


def update_columns(values: dict[str, str]) -> dict:
    """Update-row mapper: only listed columns are written (others are left unchanged)."""
    return {str(EXCEL_COLUMNS.index(k)): v for k, v in values.items()}


def event_log_values(values: dict[str, str]) -> dict:
    return {str(EVENT_LOG_COLUMNS.index(k)): v for k, v in values.items()}


def celebration_route(kind: str, base_id: int, y: int) -> dict:
    """One router branch: duplicate check -> claim -> send -> update sheet -> log."""
    is_bday = kind == "BIRTHDAY"
    label = "Birthday" if is_bday else "Anniversary"
    sent_col = "Birthday_Sent_Year" if is_bday else "Anniversary_Sent_Year"
    event_id = "{{3.employee_id}}_" + kind + "_{{1.THIS_YEAR}}"
    ds_key = "{{1.APP_MODE}}_" + event_id
    ids = {name: base_id + i for i, name in enumerate(
        ["get", "claim", "send", "mark_sent", "update_row", "log_row",
         "err_delete", "err_update", "err_log", "err_ignore", "claim_ignore"])}

    if is_bday:
        route_filter = {
            "name": "Birthday today and not yet sent this year",
            "conditions": [[
                cond("{{3.birthday_mmdd}}", "text:equal", "{{1.TODAY_MMDD}}"),
                cond("{{3.birthday_sent_year}}", "text:notequal", "{{1.THIS_YEAR}}"),
            ]],
        }
        template_name, params = "employee_birthday", ["{{3.name}}"]
    else:
        route_filter = {
            "name": "Anniversary today, >= 1 year, not yet sent this year",
            "conditions": [[
                cond("{{3.joining_mmdd}}", "text:equal", "{{1.TODAY_MMDD}}"),
                cond("{{1.THIS_YEAR - 3.joining_year}}", "number:greaterorequal", "1"),
                cond("{{3.anniversary_sent_year}}", "text:notequal", "{{1.THIS_YEAR}}"),
            ]],
        }
        template_name = "work_anniversary"
        params = ["{{3.name}}", "{{1.THIS_YEAR - 3.joining_year}}"]

    x0 = 1500
    flow = [
        {   # Duplicate check (readable): does the idempotency key already exist?
            "id": ids["get"], "module": M_DS_GET, "version": 1,
            "parameters": {"datastore": DATASTORE},
            "mapper": {"key": ds_key},
            "filter": route_filter,
            "metadata": {**designer(x0, y), "notes": f"{label}: duplicate check"},
        },
        {   # Atomic claim: overwrite = NO -> fails (and is ignored) if a parallel run claimed it
            "id": ids["claim"], "module": M_DS_ADD, "version": 1,
            "parameters": {"datastore": DATASTORE},
            "mapper": {
                "key": ds_key, "overwrite": False,
                "data": {"event_id": event_id, "employee_id": "{{3.employee_id}}",
                         "event_type": kind, "event_year": "{{1.THIS_YEAR}}",
                         "mode": "{{1.APP_MODE}}", "status": "PENDING",
                         "created_at": "{{1.NOW_TEXT}}"},
            },
            "filter": {"name": "Not sent before (no record)",
                       "conditions": [[cond(f"{{{{{ids['get']}.status}}}}", "notexist")]]},
            "onerror": [{"id": ids["claim_ignore"], "module": M_IGNORE, "version": 1,
                         "metadata": designer(x0 + 300, y + 300)}],
            "metadata": designer(x0 + 300, y),
        },
        {   # Send the approved template (official Cloud API via Make's WhatsApp app)
            "id": ids["send"], "module": M_WA_TEMPLATE, "version": 1,
            "parameters": {"__IMTCONN__": WHATSAPP_CONN},
            "mapper": {
                "senderId": PHONE_NUMBER_ID,
                "to": "{{3.recipient}}",
                "template": template_name,
                "language": "en",
                "bodyParameters": [{"type": "text", "text": p} for p in params],
            },
            "onerror": [
                {   # Failure: remove the claim so a later rerun may retry; Sent_Year untouched
                    "id": ids["err_delete"], "module": M_DS_DEL, "version": 1,
                    "parameters": {"datastore": DATASTORE}, "mapper": {"key": ds_key},
                    "metadata": designer(x0 + 600, y + 300),
                },
                {
                    "id": ids["err_update"], "module": M_XL_UPDATE, "version": 2,
                    "parameters": excel_params(),
                    "mapper": {"drive": DRIVE_ID, "workbook": SPREADSHEET, "worksheet": "Employees",
                               "rowNumber": "{{3.row_no}}",
                               "values": update_columns({"Send_Status": "FAILED",
                                                         "Error_Message": "{{error.message}}"})},
                    "metadata": designer(x0 + 900, y + 300),
                },
                {
                    "id": ids["err_log"], "module": M_XL_ADD, "version": 2,
                    "parameters": excel_params(),
                    "mapper": {"drive": DRIVE_ID, "workbook": SPREADSHEET, "worksheet": "Event_Log",
                               "values": event_log_values({
                                   "Event_ID": event_id, "Employee_ID": "{{3.employee_id}}",
                                   "Event_Type": kind, "Event_Year": "{{1.THIS_YEAR}}",
                                   "Scheduled_Date": "{{1.TODAY_ISO}}", "Mode": "{{1.APP_MODE}}",
                                   "Recipient": "{{3.recipient_masked}}", "Status": "FAILED",
                                   "Created_At": "{{1.NOW_TEXT}}", "Error": "{{error.message}}"})},
                    "metadata": designer(x0 + 1200, y + 300),
                },
                {"id": ids["err_ignore"], "module": M_IGNORE, "version": 1,
                 "metadata": designer(x0 + 1500, y + 300)},
            ],
            "metadata": designer(x0 + 600, y),
        },
        {   # Mark SENT in the idempotency store
            "id": ids["mark_sent"], "module": M_DS_ADD, "version": 1,
            "parameters": {"datastore": DATASTORE},
            "mapper": {
                "key": ds_key, "overwrite": True,
                "data": {"event_id": event_id, "employee_id": "{{3.employee_id}}",
                         "event_type": kind, "event_year": "{{1.THIS_YEAR}}",
                         "mode": "{{1.APP_MODE}}", "status": "SENT",
                         "message_id": f"{{{{{ids['send']}.messages[1].id}}}}",
                         "created_at": "{{1.NOW_TEXT}}"},
            },
            "metadata": designer(x0 + 900, y),
        },
        {   # Update the employee row. TEST mode keeps the old Sent_Year (never marks real people).
            "id": ids["update_row"], "module": M_XL_UPDATE, "version": 2,
            "parameters": excel_params(),
            "mapper": {"drive": DRIVE_ID, "workbook": SPREADSHEET, "worksheet": "Employees",
                       "rowNumber": "{{3.row_no}}",
                       "values": update_columns({
                           sent_col: '{{if(1.APP_MODE = "PRODUCTION"; 1.THIS_YEAR; 3.'
                                     + sent_col.lower() + ")}}",
                           "Last_Message_Type": label,
                           "Last_Message_Date": "{{1.NOW_TEXT}}",
                           "Send_Status": '{{if(1.APP_MODE = "PRODUCTION"; "SENT"; "TEST_SENT")}}',
                           "Error_Message": "",
                       })},
            "metadata": designer(x0 + 1200, y),
        },
        {   # Audit trail
            "id": ids["log_row"], "module": M_XL_ADD, "version": 2,
            "parameters": excel_params(),
            "mapper": {"drive": DRIVE_ID, "workbook": SPREADSHEET, "worksheet": "Event_Log",
                       "values": event_log_values({
                           "Event_ID": event_id, "Employee_ID": "{{3.employee_id}}",
                           "Event_Type": kind, "Event_Year": "{{1.THIS_YEAR}}",
                           "Scheduled_Date": "{{1.TODAY_ISO}}", "Mode": "{{1.APP_MODE}}",
                           "Recipient": "{{3.recipient_masked}}",
                           "Message_ID": f"{{{{{ids['send']}.messages[1].id}}}}",
                           "Status": "SENT", "Created_At": "{{1.NOW_TEXT}}",
                           "Sent_At": "{{1.NOW_TEXT}}"})},
            "metadata": designer(x0 + 1500, y),
        },
    ]
    return {"flow": flow}


def build() -> dict:
    config = {
        "id": 1, "module": M_SET_VARS, "version": 1, "parameters": {},
        "mapper": {"scope": "roundtrip", "variables": [
            # >>> The ONLY switch between TEST and PRODUCTION in Make <<<
            {"name": "APP_MODE", "value": "TEST"},
            {"name": "TEST_PHONE_NUMBER", "value": TEST_PHONE},
            {"name": "TODAY_MMDD", "value": '{{formatDate(now; "MM-DD"; "Asia/Dubai")}}'},
            {"name": "TODAY_ISO", "value": '{{formatDate(now; "YYYY-MM-DD"; "Asia/Dubai")}}'},
            {"name": "THIS_YEAR", "value": '{{formatDate(now; "YYYY"; "Asia/Dubai")}}'},
            {"name": "NOW_TEXT", "value": '{{formatDate(now; "YYYY-MM-DD HH:mm"; "Asia/Dubai")}}'},
        ]},
        "metadata": {**designer(0, 0), "notes": "CONFIG - set APP_MODE and TEST_PHONE_NUMBER here"},
    }
    list_rows = {
        "id": 2, "module": M_XL_LIST, "version": 2, "parameters": excel_params(),
        "mapper": {"drive": DRIVE_ID, "workbook": SPREADSHEET, "worksheet": "Employees",
                   "headerRow": True, "limit": 3000},
        "metadata": designer(300, 0),
    }
    row = {
        "id": 3, "module": M_SET_VARS, "version": 1, "parameters": {},
        "mapper": {"scope": "roundtrip", "variables": [
            {"name": "employee_id", "value": "{{trim(" + xl("Employee_ID")[2:-2] + ")}}"},
            {"name": "name", "value": "{{trim(" + xl("Name")[2:-2] + ")}}"},
            {"name": "phone", "value": "{{replace(" + xl("Phone")[2:-2] + '; " "; emptystring)}}'},
            {"name": "consent", "value": "{{upper(trim(" + xl("WhatsApp_Consent")[2:-2] + "))}}"},
            {"name": "active", "value": "{{upper(trim(" + xl("Active")[2:-2] + "))}}"},
            {"name": "birthday_mmdd", "value": xl("Birthday_MMDD")},
            {"name": "joining_mmdd", "value": xl("Joining_MMDD")},
            {"name": "joining_year", "value": xl("Joining_Year")},
            {"name": "birthday_sent_year", "value": xl("Birthday_Sent_Year")},
            {"name": "anniversary_sent_year", "value": xl("Anniversary_Sent_Year")},
            {"name": "row_no", "value": xl("Row_No")},
            # TEST mode: every message goes to TEST_PHONE_NUMBER, never to the employee.
            {"name": "recipient", "value": '{{if(1.APP_MODE = "PRODUCTION"; replace('
                                           + xl("Phone")[2:-2] + '; " "; emptystring); 1.TEST_PHONE_NUMBER)}}'},
            {"name": "recipient_masked", "value": '{{if(1.APP_MODE = "PRODUCTION"; substring('
                                                  + xl("Phone")[2:-2] + '; 0; 6) + "****"; "TEST")}}'},
        ]},
        "filter": {"name": "Has an Employee_ID", "conditions": [[cond(xl("Employee_ID"), "exist")]]},
        "metadata": {**designer(600, 0), "notes": "EMPLOYEE ROW - the only module that reads Excel columns"},
    }
    router = {
        "id": 4, "module": M_ROUTER, "version": 1,
        "filter": {"name": "Active = YES AND Consent = YES AND phone starts with +",
                   "conditions": [[
                       cond("{{3.active}}", "text:equal", "YES"),
                       cond("{{3.consent}}", "text:equal", "YES"),
                       cond("{{3.phone}}", "text:startwith", "+"),
                   ]]},
        "routes": [celebration_route("BIRTHDAY", 10, -300), celebration_route("ANNIVERSARY", 30, 300)],
        "metadata": designer(900, 0),
    }
    return {
        "name": "7X Executive Connect - Daily Celebrations",
        "flow": [config, list_rows, row, router],
        "metadata": {
            "instant": False,
            "version": 1,
            "scenario": {
                "roundtrips": 1, "maxErrors": 3, "autoCommit": True, "autoCommitTriggerLast": True,
                "sequential": True, "confidential": True, "dataloss": False, "dlq": False,
                "freshVariables": False,
            },
            "designer": {"orphans": []},
            "zone": "eu1.make.com",
        },
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
