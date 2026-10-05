# httpSMS setup — turn one Android phone into ClimateShield's SMS gateway

**Why httpSMS:** it sends *and receives*, residents text an ordinary 09xx number, and you pay normal SIM rates. Open source (github.com/NdoleStudio/httpsms). API checked 2026-10-05 against `api.httpsms.com/doc.json`.

## You need
- An Android phone that can stay plugged in and online (Wi-Fi or data), ideally a dedicated spare.
- A Globe or Smart SIM with an unlimited-text promo (register the SIM under the project/LGU; it's the public number).
- 20 minutes.

## Steps
1. On a computer, sign up at **httpsms.com** (Google login). Open **Settings** → copy your **API key**.
2. On the phone, install the app: `https://github.com/NdoleStudio/httpsms/releases/latest/download/HttpSms.apk` (allow "install unknown apps" for the browser once, then turn it off again).
3. Open the app, sign in with the same account, grant **SMS** permissions, and enter the phone's number in `+639XXXXXXXXX` format.
4. Phone settings: battery → **Unrestricted / no optimization** for httpSMS; keep it charging; disable auto-updates that reboot overnight.
5. On the ClimateShield computer, create `.streamlit/secrets.toml` (copy the `.example`) and fill:
   ```toml
   HTTPSMS_API_KEY = "paste-key-here"
   HTTPSMS_FROM = "+639XXXXXXXXX"
   ```
6. Restart ClimateShield. In 🚑 Response & Dispatch → 📱 SMS, choose **httpSMS + Android phone** — it no longer says "not configured".

## Test (keep Drill mode ON)
1. From your own phone text the gateway number: `HELP PANTAL 3 BOAT test`.
2. In 📱 SMS press **🔄 Check for new SMS** → the message appears with "Reads as: Pantal · 3 people…". Press **➕ Create request**.
3. Add your own number as a contact with consent = True, broadcast a template → you receive it starting with `[DRILL]`.
4. Check 📤 Outbox log shows status `pending`/`sent`, not `error`.

> Note: the app treats httpSMS messages with status `received` as inbound. If step 2 shows nothing, open the httpSMS web dashboard, check the message's status label, and report it so the filter can be adjusted.

## Publish the number
Print the gateway number + the text format on barangay hall boards:

> **BAHA? I-text ang `SAKLOLO <barangay> <ilang tao> <kailangan>` sa 09XX-XXX-XXXX.**
> Halimbawa: `SAKLOLO PANTAL 5 BANGKA nasa bubong` · Kailangan: BANGKA, GAMOT, PAGKAIN, TUBIG, SHELTER, SUNOG
> Kung buhay ay nasa panganib, tumawag sa **911**.

## Limits to know
- One phone ≈ the SIM's send rate; carriers may throttle bulk sends. For city-wide broadcasts add **Semaphore** (₱0.50/SMS, sender name approval 2–4 weeks).
- If the phone's area loses signal or power, the gateway stops. Put it somewhere with generator backup (CDRRMO ops centre).
