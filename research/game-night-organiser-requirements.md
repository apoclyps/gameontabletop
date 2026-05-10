# Game Night Organiser — Feature Research & Requirements

## The Core Problem Space

Organising a recurring games night involves four overlapping coordination problems that no existing tool solves together:

1. **Is it happening?** — Recurring attendance without re-polling every time
2. **Where?** — Hosting/venue coordination across the group
3. **What do we play?** — Smart game selection from a pooled library
4. **How are we doing?** — Shared stats and social identity across the group

The tools that exist today (Doodle/Calendly for scheduling, BGG Stats for tracking, BGG for game data) all solve *one* of these, but none of them are social-first or group-first. You always end up coordinating across WhatsApp, a spreadsheet, and an app someone forgot to install.

---

## Problem 1: Recurring Attendance & "Is It On?"

### The Real Friction

The most common scenario: a group has a standing game night — say, every other Saturday. The friction isn't finding the time (it's already agreed), it's the weekly micro-coordination:

- "Is it on this week?"
- "Who's coming?"
- "Do we have enough people to make it worth it?"
- Someone drops out last minute and the group collapses quietly into no one showing up

Doodle and Calendly are designed for *finding* a time from scratch. They're structurally wrong for a recurring event where the time is already fixed and you just need headcount.

### What Needs to Be Resolved

**Recurring session definition.** A group should define a standing schedule — "every second Saturday, 7pm" — and each occurrence auto-generates an RSVP for that session. No one needs to create a new poll; the system just asks "are you coming to Saturday's session?" on a timer (e.g., Tuesday nudge, Friday reminder).

**Simple attendance states.** Not just yes/no. The useful states are:
- **In** — confirmed attending
- **Out** — not coming this time
- **Maybe / Tentative** — likely in, but can't commit yet
- **No response** — ignored the nudge (treated as uncertain)

**Quorum threshold.** The group sets a minimum player count (e.g., "we need at least 4"). The system automatically surfaces the state: *On (6 confirmed)*, *Borderline (3 confirmed, 2 maybe)*, *Off (only 2 confirmed)*. This is the answer to "is it on?" and it should be the first thing anyone sees.

**One-off cancellation / skip.** Separate from attendance — sometimes the whole session is cancelled regardless of interest (host unavailable, bank holiday, etc.). The host or organiser should be able to flag a specific occurrence as skipped without affecting the recurring pattern.

**Ad-hoc sessions.** Beyond the recurring schedule, the group needs to create one-off sessions: "Want to do an extra one this Sunday?" These live alongside recurring sessions but don't pollute the pattern.

**Late RSVP window.** People update their status right up to the day. The system should track when someone flips from In to Out so the host can react (or the quorum state can change).

---

## Problem 2: Venue & Hosting

### The Real Friction

For home game nights, someone has to host. This rotates informally in most groups, but informally means it always falls on the same enthusiastic person, or someone hosts under-equipped (no table space, wrong neighbourhood for the group, etc.).

### What Needs to Be Resolved

**Host assignment per session.** Each session should have a declared host. This could be:
- Auto-assigned by a fair rotation queue
- Volunteered by whoever puts their hand up
- Explicitly nominated by the group

**Venue capacity per host.** Each person in the group can register their hosting capacity — "I can host up to 6 comfortably" — so the system can flag if confirmed attendance exceeds what the venue can handle.

**Hosting history.** Track who has hosted and how many times, so the rotation is visible and fair. People are less resentful about hosting when they can see the pattern is equitable.

**"Can't host this time" flag.** The default host for an occurrence should be able to mark themselves unavailable to host (distinct from not attending), triggering the system to prompt another member.

**Non-home venues.** Sometimes the group goes to a pub, games café, or similar. The venue field should support free-text or a place (optionally with address/map link), not just "someone's house."

**Travel context.** Optional: rough central postcode or area so the system can surface whose location is most central for the confirmed attendees.

---

## Problem 3: Game Selection

### The Real Friction

Game selection is where enthusiasm dies. The classic failure modes:
- Someone suggests a 3-hour heavy euro with 5 players when the game is only good at 3 or 4
- No one can remember what games are available or who owns what
- A group votes on a game but the person who owns it isn't coming
- Half the group has played something, half haven't, and the expert half doesn't want to re-explain it
- It's 9pm, energy is low, and the shortlist still has Twilight Imperium in it

### What Needs to Be Resolved

**Pooled library.** Each group member registers their games. The collective library is the union of all members' collections — but crucially, a game is only "available" for a session if its owner is attending. This solves the "oh, I didn't bring it" problem.

**BGG integration.** Games should be pulled from BGG by name or BGG ID, inheriting player count range (official + BGG-voted best/recommended), play time, weight (complexity), and categories. No one should manually type in "Wingspan, 1–5 players, 40–70 minutes, weight 2.4."

**Player-count filtering.** The primary smart filter: given the confirmed/expected attendance, show only games that work at that count — using BGG's community-voted "best" and "recommended" counts, not just the box range. (A game that plays 2–8 but is only good at 3–4 should be flagged, not boosted.)

**Session context filters.** Quick toggles the group sets per session (or per person voting):
- **Time available** — under 60 min / 60–120 / 120+
- **Complexity mood** — "light", "medium", "heavy" (map to BGG weight bands)
- **Already played** / **new to group** — surfaces games no one has tried vs. familiar ones

**Game voting / shortlist.** Any member can nominate games for the session. A simple upvote/interest system (not a full ranked vote — that becomes fatiguing) surfaces what the group is excited about. The host has final say but can see the pulse.

**Game teach flag.** Optional per-game: "someone in this session knows how to teach this." Useful when new players are present — games with a teacher feel less intimidating to suggest.

**"Never played by X" view.** Filter to show games that specific attendees have never played — helpful for introducing people to the collection without asking them one by one.

**Expansion tracking.** Expansions should be linkable to their base game and flagged as "also available" when the owner is present — but shouldn't clutter the primary list.

---

## Problem 4: Stats, Leaderboards & Social Identity

### The Real Friction

BGG Stats is genuinely good at individual tracking but is structurally single-user. The friction it creates for a group:

- Only one person logs the session; everyone else's records are either duplicated by hand or lost
- Stats are siloed — you can't compare win rates across the group
- There's no shared view of "our group's" play history
- When someone isn't using BGG Stats, they become an anonymous name in someone else's log
- The social/fun layer (rivalries, streaks, nemesis tracking) doesn't exist at all

### What Needs to Be Resolved

**Shared play log.** One person logs a session result; all players in that session get the record attributed to their group account. No double-entry, no syncing across devices. The log is the group's canonical source of truth.

**BGG sync (one-way optional).** For individuals who use BGG, the system can post plays to their BGG account after a session is logged. This is a nice-to-have export, not the core.

**Per-player stats (within the group context):**
- Win rate per game and overall
- Plays per game
- Favourite games (by play count and/or win rate)
- Longest win streak and current streak
- Attendance rate (sessions attended / sessions occurred)
- Most played against (who you play with most)
- Games never won (the long-suffering)
- H-index equivalent: number of games played N or more times

**Per-game stats:**
- Most wins (and by whom)
- Average play time for this group (vs BGG estimate)
- Play count and trend (is it getting stale?)
- Closest victories (score differential)

**Head-to-head records.** Player A vs Player B across all shared games. Surfaced as a "rivalry" view — not just win/loss but games where they're most evenly matched.

**Social identity elements (the fun layer):**
- **Nemesis**: the player who beats you most often in games you both care about
- **Arch-rival**: your most evenly matched opponent
- **Specialist badge**: games where one player has a standout win rate
- **Streaks**: current win/loss streaks highlighted at session start
- **Comeback award**: won after being last at the halfway point
- **Attendance streak**: X sessions in a row attended

**Cross-group stats.** A person belongs to multiple groups — Wednesday crew, family night, work colleagues. Their personal identity (wins, favourite games, total plays) should aggregate across all groups. The leaderboard within each group is separate, but your personal profile is holistic. This is the gap BGG Stats can't fill.

**Season structure (optional but high-value).** A group can define a season (e.g., "2025") with a leaderboard that resets annually. This creates natural narrative arcs — someone who was bottom last season can reclaim the title. Seasons also make it easier to surface "this season so far" stats without needing full historical context.

**Session recap.** After each session is logged, auto-generate a short summary the group can share: "Saturday's session — Wingspan (Dan won), Brass Birmingham (Priya's 3rd win in a row), 5 players, 4.5 hours."

---

## Cross-Cutting Requirements

### Group Flexibility

**Multiple groups per person.** A user might be in a regular crew, a family group, and a work group. Each group is independent (separate library, separate schedule, separate leaderboard) but the user's personal identity carries across.

**Guest players.** Occasional players who aren't "members" of the group — track their plays and names but don't clutter the group roster. Guest plays count for host stats but guests don't appear in the leaderboard by default.

**Group roles.** Organiser (can edit sessions, manage the group), member (full participant), guest (tracked but limited). Not a complex permissions model — just three meaningful states.

### Notifications & Nudges

Notifications are where most social apps go wrong by being too aggressive. The model here should be:

- **Recurring nudge** — "This week's session: are you in?" sent once (e.g., Tuesday for a Saturday session)
- **Quorum alert** — "You're borderline (3/4 needed). 2 maybes haven't responded."
- **Status flip alert** — sent to organiser only when someone flips In→Out close to the session
- **Session confirmed / cancelled** — broadcast when quorum is clearly met or failed
- **Post-session log reminder** — gentle nudge to log results if the session happened with no log by midnight

No engagement spam. No "you haven't visited in 3 days" nonsense.

### The "Is it on?" Dashboard State

The single most important UI surface: at any given moment, a group member should open the app and immediately see:

- **Next session**: when, where, who's hosting
- **Attendance**: confirmed / maybe / out counts vs. quorum
- **My status**: am I in or not, with a one-tap toggle
- **Shortlisted games**: what's been proposed so far

This is the information that currently requires three WhatsApp messages and an abandoned Doodle poll to obtain.

---

## What Existing Tools Get Wrong (and Why This Gap Exists)

| Tool | What it does | What's missing |
|---|---|---|
| **Doodle / Calendly** | Find a meeting time from scratch | Not designed for recurring events; no game context; no stats |
| **BGG Stats** | Rich individual play tracking | Single-user only; no shared group log; no scheduling |
| **BGG (site)** | Game data, ratings, forums | Not a coordination tool; no group scheduling or attendance |
| **WhatsApp / group chat** | De facto coordination | No structure; history lost; RSVP is chaos |
| **Games Night Planner (app)** | Attendance + game voting | No shared stats; no recurring schedule model; minimal BGG integration |
| **Meetup** | Event RSVPs for communities | Overkill for private friend groups; no game-specific features |

The gap is precisely at the intersection of *recurring private group coordination* + *game-aware tooling* + *shared social stats*. No tool occupies this space.

---

## Summary of Domain Requirements by Priority

### Must-Solve (Core)
- Recurring session with per-occurrence attendance RSVP
- Quorum threshold and "is it on?" status surfacing
- Host/venue per session with capacity awareness
- Pooled game library with BGG-sourced player count and weight data
- Player-count-aware game filtering based on confirmed attendees
- Shared play log (one entry, all players get credit)
- Group leaderboard: win rates, play counts, streaks

### High Value (Differentiating)
- Game voting / nomination per session
- Cross-group personal stats identity
- Head-to-head rivalry stats
- Season/annual leaderboard resets
- Social badges and streak identity
- Session recap shareable summary
- BGG sync (post plays to individual accounts)

### Nice to Have (Depth)
- Hosting rotation fairness tracking
- "Never played by X" game filter
- Travel/centrality suggestions for venue
- Guest player handling
- Expansion linking to base games
- Custom game weight/time overrides for this specific group

---

*Research compiled May 2026. Sources: BGG community threads, BGG Stats feature wishlist, scheduling tool comparisons, board game hosting guides, and direct analysis of the coordination problem space.*
