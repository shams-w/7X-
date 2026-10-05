from datetime import date

from app.anniversary import anniversary_event, years_completed
from app.main import run_daily
from app.models import Employee
from conftest import TODAY, employee_row, make_workbook


def emp(joining, **kw) -> Employee:
    base = dict(row_number=2, employee_id="EMP002", name="Sara Sample", phone="+971500000002",
                consent=True, active=True, joining_date=joining)
    base.update(kw)
    return Employee(**base)


# 4. Anniversary today
def test_anniversary_today():
    ev = anniversary_event(emp(date(2019, 10, 5)), TODAY)
    assert ev is not None
    assert ev.years_completed == 7
    assert ev.event_id == "EMP002_ANNIVERSARY_2026"


# 5. First anniversary
def test_first_anniversary():
    ev = anniversary_event(emp(date(2025, 10, 5)), TODAY)
    assert ev is not None and ev.years_completed == 1


# 6. Fifth anniversary
def test_fifth_anniversary_and_template_params(settings, wa, fake_session):
    assert anniversary_event(emp(date(2021, 10, 5)), TODAY).years_completed == 5
    make_workbook(settings.spreadsheet_path, [employee_row(name="Sara Sample", joining=date(2021, 10, 5))])
    s = run_daily(settings, TODAY, wa)
    assert len(s.sent) == 1
    tpl = fake_session.calls[0]["json"]["template"]
    assert tpl["name"] == "work_anniversary"
    assert [p["text"] for p in tpl["components"][0]["parameters"]] == ["Sara Sample", "5"]


# 7. Joining date today = zero years
def test_joined_today_zero_years_not_sent(settings, wa, fake_session):
    assert anniversary_event(emp(TODAY), TODAY) is None
    make_workbook(settings.spreadsheet_path, [employee_row(joining=TODAY)])
    s = run_daily(settings, TODAY, wa)
    assert fake_session.calls == []
    assert any("0 years" in x for x in s.skipped)


# 8. Future joining date
def test_future_joining_date(settings, wa, fake_session):
    assert anniversary_event(emp(date(2027, 10, 5)), TODAY) is None
    make_workbook(settings.spreadsheet_path, [employee_row(joining=date(2027, 10, 5))])
    s = run_daily(settings, TODAY, wa)
    assert fake_session.calls == []
    assert any("future" in d for d in s.data_errors)


def test_anniversary_not_today():
    assert anniversary_event(emp(date(2019, 10, 6)), TODAY) is None


def test_anniversary_already_sent_this_year():
    assert anniversary_event(emp(date(2019, 10, 5), anniversary_sent_year=2026), TODAY) is None


def test_years_completed():
    assert years_completed(date(2023, 10, 5), TODAY) == 3


def test_missing_joining_date_reported(settings, wa, fake_session):
    make_workbook(settings.spreadsheet_path, [employee_row(joining=None)])
    s = run_daily(settings, TODAY, wa)
    assert any("Joining_Date missing" in d for d in s.data_errors)


def test_years_phrase_format(settings, fake_session):
    from app.whatsapp import WhatsAppService

    settings.anniversary_years_format = "phrase"
    w = WhatsAppService(settings, session=fake_session, sleep=lambda s: None)
    w.send_anniversary_message("+971500000001", "Sara", 1)
    w.send_anniversary_message("+971500000001", "Sara", 4)
    texts = [c["json"]["template"]["components"][0]["parameters"][1]["text"] for c in fake_session.calls]
    assert texts == ["1 year", "4 years"]
