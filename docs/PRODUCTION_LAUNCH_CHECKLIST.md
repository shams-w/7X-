# Production launch checklist

Production means **real executives receive real messages**. Two people should check this list (for example you + HR).

## Before go-live
- [ ] Setup checklist A–C fully passed
- [ ] Every person in the sheet has given WhatsApp consent, and `WhatsApp_Consent = YES` only for them
- [ ] Every `Phone` is international format (`+971...`), with no red cells in the sheet
- [ ] `Active = NO` for anyone who has left
- [ ] Employee IDs are unique
- [ ] Remove test rows (Shams Test / EMP900), or set `Active = NO`
- [ ] Clear `Send_Status` / `Error_Message` left over from tests (optional, cosmetic)
- [ ] Do a final dry check: filter the sheet for today's and tomorrow's birthdays and anniversaries, so you know what to expect
- [ ] Management has approved the template wording and the sending time (09:00 UAE)
- [ ] Someone is named as owner of the automation (watches failures, updates the sheet)

## Switch (Make)
1. Open the scenario → module **1 CONFIG** → set `APP_MODE` = `PRODUCTION` → OK → **Save** (disk icon).
2. Check the schedule: **Every day, 09:00**, and the profile time zone is Asia/Dubai.
3. Turn the scenario **ON**.
4. Write down the date/time and who switched it in the `README` sheet of the workbook.

## Switch (Python fallback, only if used instead of Make)
1. In `.env`: `APP_MODE=PRODUCTION`, `PRODUCTION_CONFIRM=I_UNDERSTAND_REAL_EMPLOYEES_WILL_RECEIVE_MESSAGES`, `DRY_RUN=false`.
2. Run `python -m app.main --dry-run` once to see what *would* go out today.
3. Make sure **only one** system is live (Make **or** Python, never both). They keep separate duplicate logs.

## First 7 days
- [ ] Check the `Event_Log` sheet / Make execution history each morning after 09:00
- [ ] Any `FAILED` or `UNKNOWN` → see docs/TROUBLESHOOTING.md
- [ ] Ask the first recipients (discreetly) whether the message looked right
- [ ] Check that the phone app still shows the sent messages (Coexistence is healthy)

## Every month
- [ ] Open the WhatsApp Business app on the phone (keeps Coexistence connected)
- [ ] Review joiners and leavers in the sheet
- [ ] Look at WhatsApp Manager → Insights for cost and quality rating
