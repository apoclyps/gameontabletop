# Game Night Organiser — Feature Specification

## How to Read This Document

Features are grouped into **six functional areas**. Within each area, features are ordered by implementation priority. Each feature describes:
- **What it is** (the behaviour)
- **What high standard looks like** (the difference between a working feature and a good one)
- **The failure mode** (what happens if this is built carelessly)
- **Data considerations** (the shape of the problem, not a schema)

---

## Functional Area 1: Groups & Sessions

### F1.1 — Group Definition

A Group is the atomic social unit of the product. It has members, a shared game library, a recurring schedule, and a leaderboard. A user can belong to multiple groups.

**What high standard looks like:**
- Creating a group is frictionless: name it, set a rough recurring schedule, invite people by link or contact. Done in under 2 minutes.
- Group membership is immediately useful: the moment two people are in a group, the library, attendance, and stats features activate.
- Groups are private by default — no public discovery, no joinable by URL without an explicit invite.

**Failure mode:** Groups that require full setup before being useful, or that conflate "group" with "event" (common in event tools, wrong here).

**Data:** Group → members (with roles: organiser, member, guest) → sessions → plays.

---

### F1.2 — Recurring Schedule

A group defines a standing schedule: day-of-week, time, and cadence (weekly, fortnightly, monthly, every N weeks). The system auto-generates upcoming session instances from this pattern — no one manually creates the next game night.

**What high standard looks like:**
- Natural language input: "Every other Saturday at 7pm" — no fiddly date pickers.
- The next 4–6 occurrences are generated in advance and visible, so members can see what's coming and plan around it.
- Editing the schedule (e.g., "we're moving to Fridays") applies to future instances without disturbing past records or requiring re-entry.
- Sessions can be individually overridden: a single occurrence can be moved, cancelled, or skipped without breaking the pattern.

**Failure mode:** Forcing groups to create sessions manually. This kills the product because the point of a recurring event is that it happens without administrative overhead.

**Data:** Schedule (rrule or equivalent) → generates Session instances. Each instance has its own state independent of the pattern.

---

### F1.3 — Session States

A session moves through a lifecycle. The states are:

- **Upcoming** — generated, RSVPs open, no log yet
- **Confirmed** — quorum met, session is on (can be set manually or auto-triggered)
- **Cancelled** — this occurrence is off, no session happened
- **Completed** — happened, play log entered (or explicitly marked as played with no log)

**What high standard looks like:**
- The state is always visible at a glance — it's the hero of the session card, not a label buried under details.
- Transitions feel natural: a session auto-moves to "Confirmed" when quorum is met; the organiser can manually cancel; it moves to "Completed" once a play is logged.
- "Cancelled" and "Skipped" are different: cancelled means it was on and got called off; skipped means it was never going to happen (bank holiday, etc.). This distinction matters for attendance stats.

**Failure mode:** Sessions that exist in a binary "happening / not happening" state with no nuance, forcing coordinators to use WhatsApp for the nuance.

---

### F1.4 — Ad-hoc Sessions

Beyond the standing schedule, groups occasionally want a bonus session: "Anyone free Sunday?" These are one-off sessions, not recurring, and should be easy to create without disturbing the pattern.

**What high standard looks like:**
- Creation is quick: name, date, time, host — done. Appears in the session list alongside recurring ones but clearly marked as ad-hoc.
- RSVP and game selection work identically to recurring sessions.

---

## Functional Area 2: Attendance & "Is It On?"

### F2.1 — Per-Occurrence RSVP

Each session instance has its own RSVP state per member. States: **In**, **Out**, **Maybe**, **No Response**.

"No Response" is distinct from "Out" — it means the member hasn't been asked yet or hasn't answered, not that they've declined. This matters for quorum calculation and for nudge logic.

**What high standard looks like:**
- RSVP is a single tap from the dashboard — it's not buried in a session detail page.
- Changing your RSVP (In → Out, Out → In) is equally easy and immediate with no confirmation friction.
- The group sees updated counts in real time — if someone flips to In and that tips the quorum, it should show immediately.
- RSVP should work via a direct link (notification email/push tap → lands on session with one-tap RSVP). Members shouldn't need to navigate the full app to answer "are you coming?".

**Failure mode:** RSVP buried three taps deep; no real-time update for the group; treating "no response" as "out" in quorum counts (this causes false "off" signals and kills the group's trust in the system).

---

### F2.2 — Quorum Engine

The group defines a minimum player count threshold (e.g., "we need at least 4"). The system continuously computes the session state against confirmed and potential attendance.

**The three meaningful quorum states:**
- **On** — confirmed count ≥ threshold. Session is happening.
- **Borderline** — confirmed + maybe count ≥ threshold, but confirmed alone doesn't meet it. Session is uncertain.
- **Off** — confirmed + maybe count < threshold. Very unlikely to happen.

**What high standard looks like:**
- The quorum state is the FIRST thing visible on the dashboard. Not a detail; the headline.
- In "Borderline" state, the UI shows exactly what's needed to tip it: "3 confirmed · 1 more needed · 2 maybes outstanding." This is actionable — members can see they're the difference.
- Quorum is computed from confirmed + maybe, with a note of how many maybes remain. Pure confirmed-only quorum is too pessimistic and causes sessions to fail that would have succeeded.
- The threshold is per-group and editable — some groups need 4, some are fine at 3, some want 6.

**Failure mode:** Quorum that's binary (on/off with no borderline), or that buries the answer in a list of names rather than surfacing the count prominently.

---

### F2.3 — Nudge & Reminder System

Automated nudges that ask members to RSVP, and notify the organiser when the status changes meaningfully.

**The nudge schedule (sensible defaults, configurable):**
- T-4 days: "Are you in for Saturday?" — initial RSVP request
- T-1 day: Reminder to anyone who hasn't responded (No Response only, not those who said Out)
- Session day: Final count pushed to all "In" members (location, host, shortlisted games)
- T+4 hours after session: "Log your plays" nudge to the host/organiser

**What high standard looks like:**
- Nudges go to members who haven't responded — not to everyone every time. Blasting "Out" members with reminders is annoying and erodes trust.
- Organiser-only alerts: when someone flips from In to Out within 24 hours of the session, the organiser gets a notification (but not the whole group).
- The nudge itself is the RSVP — click the link in the email/notification and you're RSVPing, not logging in first.
- Nudges are suppressible: if a session is already cancelled or confirmed well in advance of the reminder window, skip the nudge.

**Failure mode:** Sending the same reminder to everyone including people who already answered; over-notifying; requiring a login click-through before RSVP works.

---

## Functional Area 3: Hosting & Venue

### F3.1 — Host Assignment

Each session has a designated host. The host is responsible for the physical location and has a meaningful role in the product (they log plays, set the venue, see organiser-level status updates).

**What high standard looks like:**
- The group can define a rotation order (a queue), and the system auto-assigns the next host in the queue for each session.
- Any member can volunteer to host by tapping "I'll host this one," which advances or adjusts the queue.
- The default next host can flag "can't host this time" — triggering the system to either auto-advance to the next in queue or surface an open volunteer slot.
- Hosting history is visible: a simple count of sessions hosted per member, so the rotation's fairness is transparent.

**Failure mode:** A "host" field that's just a free-text name with no tracking, which means one person always hosts by default because there's no social accountability for the rotation.

---

### F3.2 — Venue & Capacity

The venue for each session is the host's home or a named location. Members can register a hosting capacity on their profile ("I can comfortably fit 6 players").

**What high standard looks like:**
- When confirmed attendance approaches or exceeds the host's registered capacity, the system surfaces a gentle warning — not a hard block, just visibility.
- Venue field supports: "at [host's name]'s" (auto-filled), a custom name ("The Crown pub"), or an address/postcode.
- For non-home venues, a map link is useful but optional — don't require it.

---

## Functional Area 4: The Game Library & Selection

This is the most technically complex area and the one with the highest potential for delight or failure. Get this wrong and the product has no heart.

### F4.1 — Per-Member Game Collection

Each member registers the games they own. This is their personal collection within the app, independent of any BGG account (though BGG import is a high-value shortcut).

**What high standard looks like:**
- Search by game name → fuzzy-matched against BGG's database → select the right entry → added to collection. Three steps, under 10 seconds.
- BGG data is fetched at add-time and cached: official player count range, BGG community "Best" and "Recommended" player counts (from poll data), average play time, weight/complexity (BGG's "weight" 1–5), primary category/mechanic tags.
- Members can mark games with their own notes — "needs an expansion to be good at 4" or "avoid — no one ever wants to play this."
- Physical ownership vs. digital/BGA availability could be tracked separately, but this is a depth feature.

**Data consideration:** BGG's player count poll data (the community "best at N players" votes) is more valuable than the box-printed range. A game listed as 2–8 players might be genuinely good only at 3–4 and mediocre at 6+. The filtering must use this community data, not just the box range.

**Failure mode:** Manual game entry without BGG data; using only the box player count range; requiring BGG accounts to use this feature.

---

### F4.2 — Session Library (Pooled, Filtered by Attendance)

For each session, the available game library is the union of collections from attending members — not the full group library. A game is only "available" if its owner has RSVPed In (or Maybe, with a soft flag).

**What high standard looks like:**
- The session library auto-updates as RSVPs come in. If the person who owns Wingspan says they're out, Wingspan disappears from the session's available list.
- Games from "Maybe" attendees are shown but visually distinguished — "available if [name] comes."
- The library view is filterable. The default view for any session should already be filtered to: games that work at the expected player count (confirmed + maybe), sorted by a reasonable default (most played by this group? group rating? recently unplayed?).

---

### F4.3 — Player Count Filtering (The Core Smart Filter)

Given the expected attendance for a session, show only games that work at that count — using BGG community poll data to determine what "works" means.

**The three tiers:**
- **Best at N** — BGG community voted this as the ideal count. Surfaced prominently.
- **Recommended at N** — Works well but not optimal. Included in default results.
- **Technically supports N but not recommended** — The box says it plays N but the community says it's not good at that count. Hidden by default, accessible via a filter toggle.

**What high standard looks like:**
- The player count input is dynamic: it updates as RSVPs change. If you start at 4 confirmed and someone else RSVPs In, the filter updates to 5.
- The filter uses a range: if 4 are confirmed and 1 maybe, show games that are recommended at 4 OR 5.
- Games at the wrong count are not just filtered out — they're categorised: "also available (better at 4)" so people can opt into them knowingly.

**Failure mode:** Using box-printed player counts, which makes the filter useless (most modern games "support" a wide range but are only truly good at 2–3 of them).

---

### F4.4 — Session Context Filters

Quick toggles the group applies per session to narrow to the right vibe:

- **Time**: Under 60 min / 1–2 hours / 2+ hours (maps to BGG average play time with this group's actual recorded times where available)
- **Complexity**: Light (BGG weight < 2.0) / Medium (2.0–3.0) / Heavy (3.0+)
- **Familiarity**: Games the group has played before / Games no one in this session has played / Games [specific player] hasn't played

**What high standard looks like:**
- These are one-tap toggles on the session library, not a separate filter screen.
- "Light" and "Heavy" should be human labels, not BGG's 1.0–5.0 scale. Showing "weight: 3.4" to a non-hobbyist is meaningless; "Heavy" is useful.
- The group's actual play time data overrides BGG's estimate — if you always finish Wingspan in 55 minutes despite the box saying 40–70, the filter should use your data.
- A "Never played by anyone in this session" filter surfaces new experiences — genuinely useful when a new player joins.

---

### F4.5 — Game Nomination & Voting

Any member can nominate games for the upcoming session's shortlist. Other members can express interest (a simple thumbs-up, not a ranked vote). The host sees the shortlist and makes the final call.

**What high standard looks like:**
- Nomination is frictionless: browse the session library, tap "Suggest this." It appears in the shortlist immediately.
- Interest is lightweight: a single thumbs-up per game, no ranking, no obligation to vote on everything. The goal is signal, not a committee decision.
- The shortlist is visible to all members on the session dashboard — it creates pre-session anticipation and discussion.
- The host can mark a game as "We're playing this" which locks it in and removes the uncertainty.
- Multiple games can be locked in — it's common to play two or three in a session.

**Failure mode:** A formal voting system that requires everyone to rank all options — this is fatigue-inducing and usually results in the same person deciding anyway. Keep it conversational, not procedural.

---

## Functional Area 5: Play Logging

### F5.1 — Session Play Log

After a session, someone (usually the host) logs what was played. A single log entry covers all players — they don't each need to record it.

**A play log entry contains:**
- Game played (from the group library or searched manually)
- Players (selected from session attendees + any guests)
- Result type: competitive (one winner), team (winning team), cooperative (group win/loss), no score tracked
- Scores per player (optional — if recorded, enables win margin stats)
- Duration (optional — enables actual play time tracking)
- Notes (optional — "Sarah played brilliantly despite never having played before")
- Expansion(s) used (optional)

**What high standard looks like:**
- Logging is fast — under 2 minutes for a typical session with 1–2 games.
- Players default to the session's confirmed attendees. Adding a guest is one extra step.
- Score entry is frictionless: enter scores, winner is auto-derived (highest or lowest score, configured per game). No tapping a separate "winner" field if scores are entered.
- Multiple games per session are supported naturally — each game is a separate play entry, but they're grouped under the session.
- Cooperative games need explicit win/loss entry (not a winner player).

**Failure mode:** A play log that takes 10 minutes to fill in, or that requires entering data that's already known (who attended, what was shortlisted). The session context should pre-fill what it can.

---

### F5.2 — Play Attribution

When a play is logged, all participating players get the record attributed to their group account. Stats update for everyone automatically.

**What high standard looks like:**
- Guest players (not group members) can be logged by name and tracked historically, even without an account. Their records accumulate as named guests, visible in the group's play history.
- A logged play can be edited by the organiser if there was an error (wrong winner, wrong score) — edit history should be transparent.
- Players can be flagged as "sat out" or "teaching only" for a game (doesn't count toward their win/loss record for that game).

---

### F5.3 — BGG Sync (Export)

For members who use BGG, the system can post their plays to their BGG account after logging.

**What high standard looks like:**
- Opt-in per member, not mandatory.
- Connection via BGG credentials (BGG doesn't have OAuth, so this is username + password or API key where available).
- Posts immediately after play logging, or batched at end of session.
- Failed syncs are surfaced (BGG API is notoriously flaky) with a retry option, not silently dropped.

---

## Functional Area 6: Stats, Leaderboard & Social Identity

This is the fun layer — what makes people open the app on non-game-night days and what creates group identity over time. Build this poorly and it's a table. Build it well and it's a reason to care.

### F6.1 — Player Stats

Per-player statistics, calculated from the group's play log.

**Core stats (always visible):**
- Total plays (all games) and total sessions attended
- Overall win rate (wins / competitive game plays)
- Favourite game (most played, with sub-stat: win rate in that game)
- Current win streak / best win streak
- Attendance rate (sessions attended / sessions that occurred while a member)
- Games played count (unique titles)

**Depth stats (expandable):**
- Win rate per game (only surfaces after ≥3 plays to avoid misleading small-sample rates)
- Head-to-head record against each other member
- Average score vs. group average per game
- Best and worst games (win rate extremes)
- H-index: N games played N or more times (a nerdy but beloved metric for hobbyists)

**What high standard looks like:**
- Small sample sizes are handled gracefully. A 100% win rate after 1 game shouldn't be displayed as meaningful. After <3 plays: show the data but label it "too few plays to be meaningful" or similar.
- Stats are time-filterable: all time / current season / last 12 months / custom. This matters because groups evolve and old data can be misleading.
- The player stats page has a personality — it's not just a table. Highlight interesting facts: "Dan's 4-game Wingspan winning streak ended last Saturday."

**Failure mode:** A flat table of numbers. Stats that surface misleading data without sample-size caveats. No time filtering.

---

### F6.2 — Group Leaderboard

A ranked view of all group members by a primary metric, plus secondary stats visible at a glance.

**What high standard looks like:**
- Primary ranking is overall win rate (with minimum play count threshold to qualify — e.g., must have played at least 5 competitive games). Ranking by raw win rate with no floor produces nonsense results.
- Secondary stats shown inline: games played, current streak, favourite game.
- Leaderboard resets by season (annual is the default, but the group can define it). This creates narrative arcs: who's on top this year?
- Show movement: up/down arrows since last week or last session. This makes the leaderboard feel alive.
- Guest players appear below the member leaderboard, separately, if they've played enough to be interesting.

**Failure mode:** A leaderboard that ranks by total wins (benefits whoever plays most), or one that doesn't reset (first-mover advantage forever, kills motivation for newer members).

---

### F6.3 — Per-Game Stats

Each game in the group library has its own stats page, showing how the game has been played within this group.

**Core:**
- Total plays and total play time (group-accumulated)
- Win distribution (who wins most often — shown as a bar or ring per player)
- Average score and score range per player
- Average duration for this group vs. BGG estimate
- Play frequency trend (is it being played more or less lately?)

**What high standard looks like:**
- Win distribution is visual — a small portrait cluster weighted by win count. More interesting than a table.
- "Getting dusty" flag: if a game hasn't been played in N sessions, surface it as neglected in the library view.
- Score records: highest score ever, closest game (smallest margin of victory).

---

### F6.4 — Head-to-Head & Rivalries

For any two members, a head-to-head view showing their competitive record across all shared games.

**What high standard looks like:**
- Overall record (wins / losses / draws in games they both played)
- Broken down by game — some rivalries are game-specific
- "Most evenly matched" games (closest win rates between the two)
- This view is surfaced socially — the dashboard might show "You and Priya are 4-4 this season. Play a tiebreaker?"

**Derived social concepts (surface as fun facts, not formal systems):**
- **Nemesis**: the person you play against most but win against least
- **Rival**: your most evenly matched opponent (closest record)
- **Specialist**: a game where you have a statistically significant edge over the group

These should be surfaced as personality annotations, not mechanically imposed labels. "Priya is Dan's nemesis (4–11 record)" feels fun. A formal "Nemesis" badge with a skull icon feels try-hard.

---

### F6.5 — Achievements & Moments

Lightweight achievement system that highlights meaningful events — not a gamification scheme, more like a highlights reel.

**Meaningful achievements (automatically detected from play log):**
- Win streak milestones (3 in a row, 5 in a row, etc.)
- First win in a specific game after N losses
- Perfect attendance (all sessions in a season)
- Game specialist (won 70%+ of plays across 5+ plays)
- Comeback win (was last at halftime / scored lowest after round 1, won overall)
- Century: 100 plays logged
- Session marathon: longest single-session play time

**What high standard looks like:**
- Achievements are surfaced at the moment they happen — on the session recap, not buried in a profile.
- They're group-visible: "Dan hit a 5-game Wingspan streak last session" appears in the group feed.
- They're not grindable or exploitable (no "play 1-player games with yourself to farm stats").
- The list is short and curated — 15–20 meaningful ones, not 200 completionist badges.

**Failure mode:** A completionist badge system that creates anxiety rather than celebration; achievements no one cares about ("Logged your first play!").

---

### F6.6 — Cross-Group Personal Profile

A user's identity is the union of their stats across all groups. Their personal profile shows aggregated stats regardless of which group the play happened in.

**What high standard looks like:**
- Total plays, total wins, unique games played — all-time, all-groups.
- Favourite games across all groups (might differ from within any single group).
- Each group's leaderboard position shown as a summary — "1st in Wednesday Crew, 3rd in Family Night."
- Personal H-index across all play.
- Cross-group stats are private by default — one group can't see your stats from another group without you sharing them.

**Data consideration:** Player identity must be stable across groups — the same person logging plays in two groups should accumulate a single play history, not two separate ones.

---

## What's Deliberately Out of Scope

The following are real features that would add complexity without solving the core problems, or that can be added later once the core is solid:

- **Tournament bracket management** — different product; adds complexity to the session model
- **Public group discovery / open game nights** — the target is private friend groups, not strangers
- **Game trading or lending between members** — useful but not core to "is it on / what do we play"
- **In-session digital scorekeeping** — real-time score tracking during play is a different mode than post-session logging and competes with dedicated apps
- **Rules reference / how to play** — BGG and YouTube exist for this; don't recreate it
- **Chat / messaging** — the product should complement WhatsApp, not replace it

---

## Implementation Priority

### Phase 1 — Core Loop (MVP)
The minimum that makes the product usable and not embarrassing:

1. Groups with members
2. Recurring session schedule + per-occurrence instances
3. RSVP with quorum state visible on dashboard
4. Game library with BGG data pull
5. Session library filtered by attendance + player count
6. Play log (game, players, winner, optional scores)
7. Basic stats: win rate, play count, attendance (per player, per game)

This alone is better than the WhatsApp + Doodle + BGG Stats combination and gives the product a reason to exist.

### Phase 2 — Differentiation
What makes it good rather than just functional:

8. Game nomination + interest voting
9. Host assignment + rotation tracking
10. Nudge/reminder system
11. Quorum "Borderline" state with actionable messaging
12. Head-to-head stats
13. Group leaderboard with seasons
14. Session recap card (shareable)

### Phase 3 — Depth & Delight
What makes people tell others about it:

15. Achievements surfaced at the right moments
16. Cross-group personal profile
17. Rivalry / nemesis surfacing
18. BGG sync export
19. "Getting dusty" game flags
20. Time-based filtering on all stats

---

## Critical Technical Considerations

These aren't features but they determine whether the above features feel good or feel janky:

**Real-time RSVP updates.** When someone RSVPs, all group members should see the quorum state update without refreshing. WebSocket or SSE-based push, not polling. The live counter is a social signal — seeing "4 confirmed" tick up to 5 creates momentum.

**BGG API reliability.** BGG's API is public but rate-limited and sometimes slow or down. Game data should be fetched once and cached locally (keyed by BGG ID), with a background refresh cadence. Never block the UI on a BGG API call.

**Mobile-first UI.** The product is used on phones. RSVP, quorum status, and play logging are phone-use-cases. The dashboard — session status, my RSVP, shortlisted games — must work perfectly on a small screen with one thumb.

**No-friction entry points.** The most common user journey is: receive nudge notification → RSVP → done. This should not require a full app load or login. A signed URL in the notification that sets RSVP directly (with session context shown) reduces friction from 5 steps to 1.

**Score entry UX.** Score logging during or after a session needs to be genuinely fast — large tap targets, numeric keyboard, auto-advance between fields. A session with 5 players and 2 games shouldn't take 8 minutes to log.

**Graceful empty states.** A new group with no plays, no library, and no history should not show empty charts and "--" everywhere. Guide new groups through setup actively: "Add your games → Invite your crew → Log your first session." Every empty state is a call to action.