"""Acceptance scenario requested by 7X: 'Shams Test' birthday + 3-year anniversary today."""

from conftest import TEST_PHONE, TODAY, employee_row, make_workbook, years_ago

from app.main import run_daily


def test_shams_test_two_events_then_duplicates(settings, wa, fake_session):
    make_workbook(settings.spreadsheet_path, [
        employee_row("EMP900", name="Shams Test", phone="+971555000111",
                     birthday=years_ago(TODAY, 30), joining=years_ago(TODAY, 3)),
    ])

    first = run_daily(settings, TODAY, wa)
    assert first.events_found == 2
    assert len(first.sent) == 2
    assert any("Birthday to Shams Test" in x for x in first.sent)
    assert any("Anniversary to Shams Test - 3 years" in x for x in first.sent)
    assert fake_session.recipients == [TEST_PHONE.lstrip("+")] * 2  # never the employee's number

    second = run_daily(settings, TODAY, wa)
    assert second.sent == []
    assert len(second.duplicates) == 2
    assert len(fake_session.calls) == 2  # nothing new was sent
