# Connecting the official 7X WhatsApp number (Coexistence)

Goal: **7X Business Portfolio → WhatsApp Business Account → official 7X number →
WhatsApp Business Platform (Cloud API) → Make.com**, while the **WhatsApp Business app on
the phone keeps working**.

## What Coexistence is

Coexistence is Meta's official way to use one number in two places at once:
* the **WhatsApp Business app** on the phone, so your team keeps chatting as today, and
* the **Cloud API**, so the automation can send templates.

Messages sent by the automation also appear in the phone app. You don't migrate the number,
delete the account, or remove the business profile.

Meta only offers Coexistence through its **Embedded Signup**, which is run by a Meta
Tech Provider or Solution Partner. Make.com's *WhatsApp Business Cloud* app has a
**Coexistence** connection type, which runs this signup for you. That's why this
project uses Make.

## ⚠️ READ BEFORE YOU START — risks and what changes

| Item | Detail |
|---|---|
| What stays | Number, business profile, display name, chats, and the app on the phone |
| What changes in the app | Meta turns off some app features for Coexistence numbers. These may include broadcast lists, disappearing messages, view-once and some companion-device features. The exact list changes over time, and Meta shows it during signup. **Read that screen.** |
| Keep it connected | Meta asks that the WhatsApp Business app is **opened on the phone regularly (at least every ~14 days)**, or the API connection may be disconnected. |
| Requirements | The number must already be active in the **WhatsApp Business app** (not personal WhatsApp), with the app updated to the latest version (Meta's minimum is 2.24.17). Some accounts must have been in use for a few days before they qualify. |
| Billing | Template messages sent through the API are charged by Meta (Marketing rate). A payment method must be added to the WhatsApp Business Account. |
| Undo | You can disconnect later from the phone: WhatsApp Business app → Settings → Account → Business Platform → Disconnect. The app keeps working on its own. |

### 🛑 The one dangerous button

In Make's connection dialog there are two connection types:
* **Coexistence** — ✅ USE THIS. It keeps the phone app working.
* **Cloud API** — ❌ DO NOT use this with the existing 7X number. It only works for numbers
  that are *not* registered in the WhatsApp Business app. Using it means deleting the number
  from the app first. That is a migration, and you must not do it.

If Meta shows anything like **"delete your account from the WhatsApp Business app"**,
**"migrate"** or **"this number will no longer work in the app"**: **stop, click Cancel,
and tell me what you saw.**

### If Coexistence is not available for the 7X number

Do **not** migrate the number. The alternatives, safest first:
1. **Wait and retry.** Common reasons are an old app version, a number that's too new,
   or a temporary Meta problem.
2. **Try another official Meta Tech Provider** that supports Coexistence (for example
   360dialog, Twilio or WATI). The Python fallback works with any provider that gives you
   a Cloud API token. Change only the base URL if the provider uses its own endpoint.
3. **Use a second, dedicated number** for the automation (for example a new SIM, shown as
   "7X"). There's no risk to the main number, but employees will see a different sender.
4. **Migrate the main number to API-only.** ❌ Not recommended. The phone app stops
   working on that number. Do this only after management signs off in writing.

---

## ACTION REQUIRED FROM SHAMS — step by step (one at a time)

### Action 1 — Prepare the phone (5 minutes)
1. On the phone that runs the official 7X WhatsApp **Business** app, open the App Store / Play Store and **update WhatsApp Business**.
2. Open WhatsApp Business → **Settings → Business tools → Business profile**. Check that the 7X name and details are correct.
3. **Make a chat backup now:** Settings → Chats → Chat backup → **Back up**. This is a safety step.
4. Keep the phone next to you, unlocked, with internet access.

**Tell me:** "Phone ready", plus the WhatsApp Business app version (Settings → Help → App info).

### Action 2 — Check you control the 7X Business Portfolio
1. Open **https://business.facebook.com/settings**.
2. At the top left, choose the **7X** business portfolio.
3. Click **Users → People**. Your name must show **Full control** (admin).
4. Click **Accounts → WhatsApp accounts**. Note whether a WhatsApp account already exists. If one exists, **do not delete or change it**.

**Tell me:** "Admin confirmed", and whether a WhatsApp account already exists (its name only, no IDs needed yet).

### Action 3 — Create the Make.com account and set the timezone
1. Open **https://www.make.com** → **Get started free**. Sign up with your 7X work email.
2. Choose the hosting region when asked (EU is fine).
3. Top right avatar → **Profile** → **Time zone** = **(GMT+04:00) Asia/Dubai** → Save.

**Tell me:** "Make ready".

### Action 4 — Connect WhatsApp with Coexistence ⚠️
1. In Make: **Scenarios → Create a new scenario**.
2. Click the big **+** → search **WhatsApp Business Cloud** → choose **Send a Template Message**.
3. Next to *Connection* click **Create a connection**.
4. **Connection type: Coexistence** ← check this twice. Give it the name `7X WhatsApp Coexistence`.
5. Click **Save / Sign in**. A Meta (Facebook) pop-up opens.
   * Log in with the Facebook account that is admin of the 7X portfolio.
   * **Business portfolio:** select **7X** (do *not* create a new one).
   * When asked which number: choose **connect your existing WhatsApp Business app** and enter the official 7X number.
6. **WhatsApp Business app on the phone:** you'll get a message or a QR code. Follow the
   on-screen steps in the app to scan or approve. When asked about sharing chat history,
   choose what 7X prefers (sharing history is optional).
7. Back in the browser, finish the pop-up. Make should show the connection as **valid**.

**What you should see:** the pop-up talks about *connecting* or *sharing* your WhatsApp
Business app. It does not talk about deleting it. Afterwards, the phone app still works.

**Tell me:** "Connected" or the exact error text. **Do not** retry with "Cloud API" if it fails.

### Action 5 — Add a payment method (needed to send templates)
1. Open **https://business.facebook.com/wa/manage/home/** (WhatsApp Manager) → choose the 7X WhatsApp account.
2. **Settings (gear) → Payment methods / Billing** → add a company card.

**Tell me:** "Payment added".

### Action 6 — Create the 2 English templates
1. WhatsApp Manager → **Message templates → Create template**.
2. Category **Marketing** → **Default** → Name `employee_birthday` → Language **English**.
3. Paste the body from `templates/WHATSAPP_TEMPLATES.md` exactly → add sample `Ahmed` → **Submit**.
4. Repeat for `work_anniversary` (samples `Sara`, `4`).
5. Wait for the status **Active / Approved** (minutes to 48 hours).

**Tell me:** the status of both templates.

### Action 7 — Microsoft 365 workbook
1. Upload `sample_data/7X_Employees_SAMPLE.xlsx` to a **restricted** OneDrive for Business or SharePoint folder (only HR + you). Rename it `7X_Employees.xlsx`.
2. Replace the fake rows with real employees (see README → "How to update employee data").
3. In Make, when a Microsoft 365 Excel module asks for a connection, sign in with your 7X Microsoft account and **Accept** the permissions. If it says *"Need admin approval"*, forward that screen to your Microsoft 365 administrator.

**Tell me:** "Workbook connected".

After Action 7, follow `docs/SETUP_CHECKLIST.md` from step B.

---

## Optional: token for the Python fallback

You only need this if 7X wants to run the Python version instead of Make, or as a backup.

1. **https://developers.facebook.com/apps** → **Create app** → use case **Other** → type **Business** → link it to the 7X portfolio.
2. In the app dashboard → **Add product → WhatsApp → Set up**.
3. **https://business.facebook.com/settings → Users → System users → Add** → name `7x-automation`, role **Admin**.
4. Select that system user → **Assign assets** → **Apps** → your app (Full control). Then **WhatsApp accounts** → the 7X account (Full control).
5. **Generate token** → choose the app → expiry **Never** → permissions
   `whatsapp_business_messaging` and `whatsapp_business_management` → copy the token **once**
   into the `.env` file on the server (`WHATSAPP_ACCESS_TOKEN`). Never paste it into chat or email.
6. WhatsApp Manager → **Phone numbers** → open the 7X number → copy the **Phone number ID** into `WHATSAPP_PHONE_NUMBER_ID`.
