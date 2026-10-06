# ClimateShield gauge feed — what we need from an agency (one page)

Attach this page to the PDRRMO / DOST-ASTI letters in this folder. It says exactly what data we can
consume, in what shape, and what happens to it on arrival. The app needs **none** of your
infrastructure — a shared spreadsheet updated by any phone is enough.

## The minimum: one table, five (or three) columns

| column | type | example | required |
|---|---|---|---|
| `logged_at` | date & time (any Excel/ISO format) | 2026-08-10 14:30 | yes |
| `level_m` | number — stage above normal, metres | 1.42 | yes |
| `station` | text — gauge/site name | Pantal bridge | no (one station implied if empty) |
| `note` | text — source remark | sitrep 15 photo | no |
| `alert_m` / `alarm_m` / `critical_m` | number — your official warning thresholds for that gauge | 0.8 | no |

CSV example (a "publish to web" Google Sheet gives you this link for free):

```csv
logged_at,level_m,note
2026-08-10 06:00,0.72,banca ops normal
2026-08-10 09:00,1.05,sitreps begin
2026-08-10 12:00,1.44,depressed areas impassable
```

## Three ways to deliver it — pick whichever is easiest

1. **Published sheet (works today, zero setup):** PDRRMO/Log sheet → File → Share → *Publish to
   web* → CSV → paste the link into ClimateShield (📡 Live Telemetry → Pantal gauge → *Reading
   source: shared sheet*). The app already reads this; during floods someone updates the sheet from
   any phone and the dashboard follows.
2. **Pasted rows (works today, no account needed):** text/email us the CSV rows; the operator pastes
   them into the same panel and the chart + Alert/Alarm/Critical tags update immediately.
3. **API / hourly export (a future ops-center setup):** any JSON/CSV endpoint with the fields above;
   we can poll it on a schedule once it exists.

Send us the thresholds too (`alert_m`, `alarm_m`, `critical_m` for the Pantal/Calmay gauges) and we
will use **your** official bands instead of the current proxies (0.8 / 1.2 / 1.5 m labelled
'proxy datum'). If a different datum or unit (feet, stage above gauge zero) is used, tell us — one
line of metadata ("levels are feet above gauge plate 4.21 m ASL") is enough for us to convert.

## What the app does with your data

- Charts the history; tags the latest reading **Alert / Alarm / Critical** using your thresholds;
- Drives the wall-display header and the flood-scenario "now-cast" panel;
- Keeps every reading source-labeled: your feed always displays as *your* office's data, never as
  PAGASA's or a model's, and never replaces official warnings.

## What we do NOT do

- No redistribution without written permission: your feed appears inside ClimateShield with
  attribution, and never leaves the computer unless you say so.
- Personal information: none is expected in a stage feed; if notes contain names/numbers we will
  blank them before anything is stored.

Contact for integration: [name / mobile / email]. We can be on a call while the first feed is
plugged in; it usually takes one afternoon, most of it deciding the datum.
