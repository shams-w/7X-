# WhatsApp message templates

WhatsApp only lets a business **start** a conversation with an approved **template**.
You need to create and get approval for these templates once, in WhatsApp Manager.

> Machine-readable copy: [`meta_templates.json`](meta_templates.json)

## Which category should I choose?

Choose **Marketing**. Meta's category rules treat greetings such as "Happy birthday" as
Marketing, not Utility. If you submit them as Utility, Meta will usually move them to
Marketing anyway, or reject them.

Marketing templates have two practical effects:
* Meta charges for each delivered message. Check current UAE prices in WhatsApp Manager → Insights / Billing.
* Meta can hold back marketing messages to someone who has received many business
  marketing messages recently (error `131049`). The automation records this as `FAILED`
  and a later run the same day may retry it. A few executives a day is far below any limit.

---

## Template 1 — English birthday (required)

| Field | Value |
|---|---|
| Name | `employee_birthday` |
| Category | Marketing → **Default** (custom message) |
| Language | English (`en`) |
| Header / Footer / Buttons | none |

**Body** (copy exactly, including line breaks):

```
Happy Birthday, {{1}}! 🎉
Wishing you a wonderful day and a great year ahead.
Best wishes from 7X.
```

Sample for `{{1}}`: `Ahmed`

## Template 2 — English work anniversary (required)

| Field | Value |
|---|---|
| Name | `work_anniversary` |
| Category | Marketing → Default |
| Language | English (`en`) |

**Body:**

```
Congratulations, {{1}}, on completing {{2}} years with 7X! 🎉
Thank you for being part of our journey.
```

Samples: `{{1}}` = `Sara`, `{{2}}` = `4`

> **Grammar note for the first anniversary.** With this exact text, a 1-year anniversary
> reads "completing 1 years". If you want correct grammar, submit this body instead:
> `Congratulations, {{1}}, on completing {{2}} with 7X! 🎉` with samples `Sara` / `4 years`,
> and set `ANNIVERSARY_YEARS_FORMAT=phrase` (Python). In Make, map `{{2}}` to
> `{{X}} year(s)` (see make/SCENARIO_DESIGN.md). Either option works. Decide before you submit.

## Optional Arabic templates

These are only used when **both** of these are true:
1. the `Language` column for the employee is `AR`, and
2. `ARABIC_TEMPLATES_ENABLED=true` (Python), or the Arabic route is enabled in Make.

Anyone else always gets the English template. **Have a native Arabic speaker at 7X check the text before you submit it.**

| Name | Language | Body |
|---|---|---|
| `employee_birthday_ar` | Arabic (`ar`) | `عيد ميلاد سعيد يا {{1}}! 🎉`<br>`نتمنى لك يوماً رائعاً وعاماً مليئاً بالخير والنجاح.`<br>`مع أطيب التمنيات من 7X.` |
| `work_anniversary_ar` | Arabic (`ar`) | `تهانينا يا {{1}} بمناسبة إكمال عامك رقم {{2}} مع 7X! 🎉`<br>`شكراً لكونك جزءاً من رحلتنا.` |

The anniversary wording ("your year number {{2}}") avoids the Arabic number agreement
problem (سنة / سنتين / سنوات), so it reads correctly for any number of years.

## Rules Meta checks (why a template gets rejected)

* Variables must be numbered in order: `{{1}}`, `{{2}}`.
* A variable may not be the very first or very last thing in the body (ours are not).
* Every variable needs a sample value.
* The name must use only lowercase letters, numbers and underscores (ours do).
* Approval usually takes from a few minutes up to 24–48 hours.

The template **name** and **language code** you use in the code or in Make must match the approved template exactly.
