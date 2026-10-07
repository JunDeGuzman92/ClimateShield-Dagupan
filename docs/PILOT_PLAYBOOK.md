# Response simulator: tabletop exercise script

A 60–90 minute practice session using ClimateShield's simulator. Nothing is sent and no agency is contacted; every text, dispatch and alert is simulated and logged on the computer. Run it with 1 operator at the screen and 2–6 participants playing roles (dispatcher, shelter manager, rescue lead, barangay official).

## Fastest way: the timed exercise
🚑 Response & Dispatch → **🎯 Timed exercise** panel → team name, storm, speed (×4 = 10-minute storm) → **▶ Start**.
Storms can be 40-hour **story storms** or **real storm replays**: the Aug 2026 habagat, Pepeng 2009, Egay 2023 and
other recorded events, spanning real calendar dates. For a month-long replay use the higher speeds (×48 ≈ 18 minutes);
each replay can also be run "if the city had prepared" to compare response conditions.
The storm clock drives flood conditions, complications fire on their own (text waves, road cut, shelter loses power,
boat breaks down, clinic floods), and **⏹ Stop & score** gives a 0–100 score that is saved to **📊 Run history**
so teams can compare. The manual script below is for facilitator-led sessions.

Scoring (100 pts): text → request speed 15 · request → unit speed 20 · requests resolved 25 · critical resolved 15 ·
events acknowledged (and how fast) 15 · texts answered 10 · penalties −5 per overfilled shelter, −8 per unsafe shelter still occupied.

## Setup (5 min)
1. 🚑 Response & Dispatch → **🧹 Reset simulation**.
2. Practice barangay(s): e.g. Pantal (+ Carael for a harder run).
3. 🏠 Shelters: open 2–3 centres and type practice capacities (e.g. 150). Mark them "practice values" in your notes.
4. 🚤 Resources: add a few units (2 rubber boats, 1 truck, 1 ambulance, 1 rescue team), status *available*.
5. "Assume flood conditions": Calamity-class.

## Run (45 min)
| Minute | Action | Role |
|---|---|---|
| 0 | Command Deck → play *Unprepared city* time-lapse to hour ~6 | All watch |
| 5 | 📱 Messages → simulate a Pre-emptive (TL) alert for the practice barangays | Barangay official |
| 8 | **🎲 Simulate 6 incoming help texts** | Operator |
| 8–25 | Turn each text into a request; assign units; simulate dispatch messages | Dispatcher |
| 25 | Fill one shelter to capacity → watch it auto-mark FULL; route a shelter request elsewhere | Shelter manager |
| 30 | Simulate 6 more texts; pressure test | Operator |
| 30–45 | Move requests to en route → resolved; units return | Rescue lead |
| 45 | Simulate All clear (TL) | Barangay official |

## Review (15 min)
| Question | Answer |
|---|---|
| Average time text → request → unit assigned (from queue timestamps)? | |
| Any texts misread by the parser? Which words? | |
| Did any request wait because no unit was free? | |
| Did a shelter fill up? What happened next? | |
| What would you change in the screen layout? | |

Finish with **🧹 Reset simulation** so the next group starts clean.

## Heat drill variant (☀️ Heat Scenario Simulator)

The heat tabletop uses the same two-screen setup (operator + 🖥 facilitator):
1. Pick a day: recorded (April typical · 2024-type wave · wave + brownout), **build your own** (peak °C, RH%,
   brownout, tropical night), or **today's live forecast**.
2. Use the 🎬 **Day time-lapse** to let the day play in front of the room; pause at the hour the
   facilitator calls out (e.g. "13:00 · casualty").
3. Work the 🚶 **Relief reach & survival** tab for one community (default Pantal): who is beyond 2.5 km of
   an open cooling point? Which school call (DepEd discretion) happens at which band? Where does the
   nearest health site sit?
4. Use the **heat tabletop injects** (bottom of the page) as complications: brownout, water outage,
   casualty, cooling point full.
5. Close with the 📄 heat **survival card** (PNG) for the community; it is the takeaway for the
   barangay board.

Read the protocol sources before quoting: PAGASA bands; DepEd Order 37 s.2022 + 4-Apr-2024 ADM discretion;
a 2026 draft auto-suspension rule flagged draft-not-policy; DOLE Labor Advisory 08 s.2023.
