# OpenParty — Build Plan v3 (Split Architecture, Python-only UI locked)

This replaces the earlier single-app plan. Written in depth, assuming no prior technical background — if you're an AI coding agent reading this cold, or a person who's never seen this project before, everything you need is explained here, not assumed.

**Changes from v2:** GUI framework locked to PySide6, no exceptions (Global Rule 9); fixed misleading Syncplay port guidance (8995/8999 are the congested public ports, not good defaults); made Syncplay's winget availability an explicit unconfirmed risk with the direct-installer fallback built first; added `.oparty` file association, elevation strategy, and SmartScreen guidance to Phase 2; added the `compatibility.min_openparty_version` check to Phase 3 (schema had the field, no phase implemented it); added subtitle handling and an aria2c RPC secret to Phase 7; pulled a lightweight 2-machine sync smoke test into Phase 8 instead of leaving all multi-machine testing for Phase 10.

---

## 0. Read Me First — What Is This, In Plain Language

Right now, if a group of friends wants to watch a movie together over a call, someone has to walk everyone through installing several different programs, finding the right file, and getting everyone's video player into the same "room" at the same time. That's the whole problem OpenParty exists to remove.

Think of it like moving into a new apartment:

- **`setup.cmd`** is move-in day — the plumber, the electrician, the furniture delivery, all happening once. After that day, you never think about it again.
- **The OpenParty app** is what you use every single day after that. It assumes the apartment is already fully set up, and it only focuses on the thing you actually care about: hosting or joining a movie night.

Splitting these into two separate pieces (instead of one program that does both) means:
- The everyday app stays small, fast, and simple, because it never has to deal with installing software or asking for admin permission.
- The one-time setup step can take its time and be extra careful, because it only ever runs once.
- If something breaks, it's obvious which of the two pieces is responsible.

---

## 1. The Two Pieces

### Piece 1 — `setup.cmd`
A one-time Windows script. A friend downloads it once, double-clicks it, and it installs everything OpenParty needs: **VLC Media Player**, **Syncplay**, and **aria2c** (the tool that does the actual downloading). It uses `winget` — a tool already built into modern Windows for installing software from the command line — with a fallback plan for anything winget can't handle. Once it says "done," that friend never runs it again unless something needs reinstalling.

### Piece 2 — The OpenParty App (Python GUI)
The actual watch-party app, built entirely in Python with PySide6 for every screen — no web-based UI technology anywhere in this piece (see Global Rule 9). It **never installs anything itself** — that rule matters, because mixing "installs software" and "everyday app" back together would bring back all the complexity we just removed. If the app notices something is missing, it simply says so and points back to `setup.cmd`. The app's whole job is:
1. Let a host fill out a short form and produce a **party file** (a `.json` file — think of it as a movie-night ticket containing everything a guest's computer needs to know).
2. Let a guest open that party file.
3. Download the movie (via aria2c), verify it downloaded correctly, launch Syncplay, open VLC, and join the room — automatically, showing live status the whole way.

### Text diagram
```
                setup.cmd  (run once, ever)
                     │
        checks Windows, installs what's missing
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      VLC        Syncplay       aria2c
        │            │            │
        └────────────┴────────────┘
                     │
              installation done
     (setup.cmd is not needed again unless updating)

════════════════════════════════════════════════════

              OpenParty App (Python GUI)
                     │
            Host chooses, or Guest chooses
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  Create Party               Join Party
        │                         │
  Fill in movie info      Open / paste party file
        │                         │
  Export party file        Validate party file
        │                         │
        └────────────┬────────────┘
                      ▼
        Check VLC / Syncplay / aria2c are present
      (if not: "Please run setup.cmd" — app stops here,
                it never installs anything itself)
                      │
                      ▼
             Download movie (aria2c)
                      │
                      ▼
              Verify the download
                      │
                      ▼
                Launch Syncplay
                      │
                      ▼
                  Open in VLC
                      │
                      ▼
             Everyone watches in sync
```

---

## 2. How To Use This Document

1. Give an AI coding agent **Section 3 (Global Rules)** as persistent context — paste it into `CLAUDE.md`, `.cursorrules`, or the first message of a new session.
2. Then feed it **one phase at a time**, in order, from Section 6.
3. After each phase, the agent writes a completion doc (template in Section 4) and **stops**. Read the doc, run the app yourself, then move on.
4. **Section 8 (Skills)** goes in too, as background reading — it's the "how to think about this codebase" reference, consulted throughout, not phase-specific.

---

## 3. Global Rules (apply to every phase, every time)

1. **One phase at a time.** Never start work that belongs to a later phase, even if it feels convenient. If a later phase's work is briefly unavoidable, stub the absolute minimum and say so plainly in that phase's doc.
2. **The app must run at the end of every phase.** No phase ends with something broken. If a feature can't be finished, it should fail gracefully with a clear message — never a crash.
3. **Document every phase**, using the template in Section 4, saved as an actual file in `docs/`. Not a spoken summary — a file.
4. **Stop after each phase** and wait for a clear go-ahead before starting the next one.
5. **Git commit per phase**, message format: `Phase N: <short summary>`.
6. **Real error handling, never silent failure.** Every risky operation (file access, network call, spawning VLC/Syncplay/aria2c) has a defined failure path with a plain-language message for the user and full detail in a log file.
7. **No hardcoded absolute paths or secrets.** Resolve things at runtime.
8. **When genuinely blocked or unsure, say so and state the assumption you're making** rather than silently guessing and moving on.
9. **The UI is 100% Python — PySide6, locked.** Every screen, dialog, form, and progress indicator in `/app` is built with PySide6. No web-based UI technology (Electron, embedded browser views, HTML/JS front ends) and no other Python GUI toolkit (Tkinter, CustomTkinter, wxPython, etc.) is used anywhere in this project. This is a fixed decision, not a per-phase choice. `setup.cmd` is exempt from this rule since it has no GUI — it's a one-time console installer script, not part of the app.

---

## 4. Phase Completion Doc Template

Save as `docs/PHASE_N.md` at the end of every phase:

```markdown
# Phase N — <Title>

## Status
✅ Complete / ⚠️ Partial (explain what's missing and why)

## What was built
- ...

## Files added / changed
- ...

## How to test this phase manually
1. ...

## Decisions & trade-offs made
- ...

## Known issues / carried forward to later phases
- ...
```

---

## 5. Phase Overview

| # | Phase | Core deliverable |
|---|-------|-------------------|
| 1 | Project Foundations | Two separate project folders, both runnable |
| 2 | The Setup Script | `setup.cmd` installs VLC, Syncplay, aria2c via winget |
| 3 | The Party File Format | JSON config schema + Python loader/validator |
| 4 | Dependency Detection (App-side) | App detects, never installs |
| 5 | Create Party (Host Flow) | Host form → exported party file |
| 6 | Join Party (Guest Flow) | Guest loads/pastes party file |
| 7 | Downloading the Movie | aria2c integration, live progress |
| 8 | Verify, Launch Syncplay, Open VLC | Full automated chain works |
| 9 | Making Failures Boring | Friendly errors, nothing crashes |
| 10 | Packaging & Real Multi-Friend Test | Shippable `.exe`, tested with real peers |

---

## 6. Phase Prompts

### PHASE 1 — Project Foundations

**Plain language:** two independent pieces means two independent project folders, right from day one. Neither should assume much about the other beyond "the app can check whether setup already ran."

**Tasks:**
- Repo root with two top-level folders: `/setup` (holds `setup.cmd` and its own notes) and `/app` (the Python GUI project).
- Inside `/app`: set up a Python project with a virtual environment and a dependency file (`requirements.txt` or `pyproject.toml`). GUI framework is **PySide6** (official Qt bindings for Python) — locked per Global Rule 9, not a per-phase choice. Native look on Windows, and a proper threading model for background downloads later, which matters a lot for this app.
- `/app/main.py` opens a single window titled "OpenParty" with a placeholder home screen showing two buttons, "Create Party" and "Join Party" — not wired to anything yet, just visible.
- Set up per-subsystem logging now, even though most subsystems don't exist yet: a small shared logging helper any module can import, writing to `/app/logs/launcher.log`. (`download.log`, `syncplay.log`, `vlc.log` get added as those subsystems are built in later phases.) This is cheap now and annoying to retrofit later.
- `/setup/setup.cmd`: for now, just prints "Setup will go here" and exits. Real logic is Phase 2.
- Root `README.md`: one paragraph per folder, plus how to run the app in dev mode.

**Definition of done:** `python app/main.py` opens the placeholder window with no errors; `setup/setup.cmd` runs and exits cleanly.

**Write `docs/PHASE_1.md`, then stop.**

---

### PHASE 2 — The Setup Script (`setup.cmd`)

**Plain language:** this is the one file a friend double-clicks exactly once, before ever opening OpenParty itself.

**Tasks:**
- Check for `winget` first (`winget --version`). If it's missing, stop with a clear message pointing to installing "App Installer" from the Microsoft Store — but note that the Store may itself be blocked on some school/corporate-managed laptops, so also point to the manual App Installer download from Microsoft's winget-cli GitHub releases as a fallback.
- For each dependency — VLC, Syncplay, aria2c — **check if it's already installed before doing anything** (`winget list`, or known install paths). Never reinstall something that already works.
- Look up the exact winget package ID for each tool with `winget search <name>` at build time rather than guessing from memory — package IDs occasionally change, and a wrong guess fails silently. **Syncplay in particular has an unconfirmed winget package as of writing** — build and test its direct-installer-download fallback first, don't treat it as a rare edge case.
- Where winget supports it, pin the specific tested version (`winget install --id <id> --version <version>`) rather than always grabbing latest — a friend running `setup.cmd` months from now shouldn't silently get a newer Syncplay with changed CLI flags that breaks Phase 8's assumptions.
- If a dependency isn't available via winget at all, fall back to downloading its official installer and running it silently (most Windows installers support a `/S` or `/silent` flag — check each tool's own documentation for the exact one rather than assuming).
- Decide and document an elevation strategy: some winget installs need admin rights. Either have `setup.cmd` self-elevate (re-launch itself elevated if needed) or clearly instruct the friend to right-click → "Run as Administrator" before double-clicking, and say which up front.
- Register the `.oparty` file association with OpenParty as part of setup, so that once setup is done, double-clicking a received party file opens the app directly with it pre-loaded — this removes a manual step from the Join Party flow in Phase 6.
- Log everything to `setup/install.log` (plain text) so a friend can screenshot it if something goes wrong.
- End with a clear human message — "Setup complete. You can now open OpenParty." — and a `pause` at the very end so the window doesn't just flash and vanish, which is confusing if you've never used a command window before.
- Note (for `docs/USER_GUIDE.md`, written in Phase 10) that Windows SmartScreen will likely show an "Unknown Publisher" warning the first time a friend runs `setup.cmd` or the packaged app — expected for unsigned software, not a sign of a virus. The guide should show exactly what "More info → Run anyway" looks like.

**Definition of done:** on a clean Windows machine, double-clicking `setup.cmd` installs VLC, Syncplay, and aria2c (or gives a specific, clear error for whichever one couldn't install), with a full log saved.

**Write `docs/PHASE_2.md`** — record the exact winget package IDs you confirmed, and note which (if any) dependency needed the silent-installer fallback instead of winget. **Then stop.**

---

### PHASE 3 — The Party File Format (JSON Config)

**Plain language:** this is the "movie-night ticket" — one JSON file containing everything a guest's computer needs to join, so nobody has to explain anything by voice.

**Tasks:**
- Design the schema to be genuinely human-readable — someone should be able to open it in Notepad and roughly understand it. Suggested fields:

```json
{
  "config_version": 1,
  "party_name": "Friday Movie Night",
  "torrent": "magnet:?xt=urn:btih:EXAMPLE",
  "file_name_hint": "Movie.Name.2024.1080p.mkv",
  "subtitle_url": null,
  "syncplay_server": "syncplay.pl:8997",
  "room": "friday-movie-night",
  "room_password": ""
}
```

> **Verify before hardcoding:** Syncplay's own docs advise avoiding the public servers on ports 8995 and 8999 specifically, since they're the most congested. `8997` above is a placeholder for "a less-congested port," not a confirmed recommendation — check the current public server list at syncplay.pl before finalizing a default.

- Implement a small Python module to load and validate this (`pydantic` is a good fit for clean, specific validation errors — or a hand-written validator if you'd rather avoid the extra dependency). Loading either succeeds with a clean object, or fails with **one specific, human-readable reason** ("room is missing", "torrent must be a magnet link or a .torrent file") — never a raw Python traceback shown to a user.
- Write `docs/config-schema.md`: every field, which are required, and a full real example.
- Write a small test that feeds this loader a handful of deliberately broken example files and confirms each produces the right specific error. This becomes the safety net every later phase leans on.
- Implement the `compatibility.min_openparty_version` check as part of this same loader — it's a validation concern, not a later add-on. If a party file requires a newer OpenParty than what's running, fail with the friendly message from the party file spec ("This party requires OpenParty X.Y.Z or newer.") instead of a generic validation error.

**Definition of done:** a valid example config loads cleanly; several broken examples each produce a clear, specific error, never a crash; an example with a too-high `min_openparty_version` produces the specific version-mismatch message.

**Write `docs/PHASE_3.md`, then stop.**

---

### PHASE 4 — Dependency Detection (App-Side, No Installing)

**Plain language:** the app's only job here is to look around and say "yes, I see VLC/Syncplay/aria2c" or "no — please run setup.cmd first." It never installs anything itself; that split is what keeps the everyday app simple and avoids Windows permission headaches.

**Tasks:**
- Build a detection module: check for VLC, Syncplay, and aria2c using the same kind of check `setup.cmd` uses to confirm them (known install paths, `PATH` lookups, or `winget list` if available). **This module only reports — it never installs.**
- Build an "Environment Check" screen shown before anything else in the app can proceed — a simple checklist, ✔ or ✘ per dependency.
- If anything is missing, show exactly one message: **"Required software is missing. Please run setup.cmd and restart OpenParty."** Nothing more technical on-screen — full detail goes to `launcher.log` only.
- If everything is found, unlock the rest of the app (Create Party / Join Party become usable).

**Definition of done:** on a machine where `setup.cmd` hasn't run, the app clearly blocks with the message above; after running `setup.cmd`, restarting the app unlocks normally.

**Write `docs/PHASE_4.md`, then stop.**

---

### PHASE 5 — Create Party (Host Flow)

**Tasks:**
- Build the host form: party name, magnet link or `.torrent` file (file picker for local files, text field for magnet links), optional subtitle URL, syncplay server (default to a sensible public one, editable), room name (offer a "generate random name" button), optional room password (offer "generate random password" button).
- Validate inputs live as the host types, using the Phase 3 config module.
- "Export" saves a `.json` file via a save dialog **and** offers "Copy to Clipboard" — this file usually gets shared by pasting straight into a Discord message, not as an attachment.
- If the password is left blank, show one line of caution: anyone who knows the room name on the same Syncplay server could join.

**Definition of done:** a host can produce a valid, shareable party file in under a minute, with real-time validation preventing obviously broken output.

**Write `docs/PHASE_5.md`, then stop.**

---

### PHASE 6 — Join Party (Guest Flow)

**Tasks:**
- Build the guest screen: "Open Party File" (file picker) and "Paste Party File" (text box, for guests who got raw JSON pasted into a chat rather than a file).
- Validate using the Phase 3 module. On success, show the parsed details clearly (party name, room name, and anything else useful) plus a "Start Party" button. On failure, show the specific validation error.

**Definition of done:** a guest can load a party file either way and see accurate details before anything else happens.

**Write `docs/PHASE_6.md`, then stop.**

---

### PHASE 7 — Downloading the Movie (aria2c)

**Plain language:** this is where the app actually goes and fetches the file — with real, live progress the whole time, so nobody thinks it's frozen.

**Tasks:**
- Spawn aria2c with its RPC interface enabled (`--enable-rpc`) and a random `--rpc-secret` token generated at launch, rather than reading its console output — RPC gives clean, structured progress data instead of text that changes shape between versions, and the secret keeps the local RPC port from being usable by any other process on the machine.
- Talk to aria2c over local JSON-RPC from a background thread, so the GUI never freezes while a download is running.
- Support both magnet links and `.torrent` files. If the torrent contains multiple files, use `file_name_hint` to pick the right one, or fall back to the largest video file.
- If the party file specifies `subtitles`, download each one to a location next to the media file once the main download completes, so Phase 8 can hand a matching subtitle path to VLC/Syncplay. If this isn't implemented in v1, say so explicitly under known issues in `docs/PHASE_7.md` — the schema already advertises the field, so silently skipping it should be a stated decision, not an oversight.
- Before starting, check free disk space against the reported torrent size; stop early with a clear message if there isn't enough room.
- If the target file already exists and matches the expected size, skip re-downloading.
- Show a live status panel through this whole phase: connecting → resolving swarm → downloading (percent, speed, ETA) → complete.
- Log all of this to `download.log`.

**Definition of done:** given a party file with a real magnet link, starting the party shows accurate live progress and ends with the correct file saved locally.

**Write `docs/PHASE_7.md`, then stop.**

---

### PHASE 8 — Verify, Launch Syncplay, Open VLC

**Tasks:**
- After download completes, verify the file (size check at minimum; a checksum too if the torrent metadata provides one).
- Launch Syncplay pointed at: the downloaded file, the syncplay server from the config, the room name/password, and the VLC path found in Phase 4's detection.
- Before hardcoding Syncplay's command-line flags, run `syncplay --help` against the exact installed version and use what it reports — flag names have changed between Syncplay versions before, so don't rely on memory or old docs.
- Monitor the Syncplay process. If it exits early or fails to start, show a plain message ("Couldn't start Syncplay. Try reinstalling it via setup.cmd.") with full detail only in `syncplay.log`.
- Update the live status panel through each step: ✔ Verifying Download → ✔ Launching Syncplay → ✔ Opening VLC → ✔ Connected to Room → ✔ Ready.

**Definition of done:** starting from a loaded party file, the full chain — download → verify → Syncplay launches → VLC opens with the file loaded → connects to the room — works end to end on one machine, **and** a lightweight 2-machine smoke test (host + one guest, real Syncplay room, real pause/play/seek) confirms actual playback sync. Don't wait until Phase 10 to discover sync bugs for the first time — they're cheaper to fix here.

**Write `docs/PHASE_8.md`, then stop.**

---

### PHASE 9 — Making Failures Boring (Error Handling & Recovery)

**Plain language:** the goal here is that this app should never show a scary wall of red text. Every failure should read like a short, calm note: what went wrong, why, and what to do about it.

**Tasks:**
- Build a central error-handling layer, used by every subsystem, producing messages shaped like this:

```
Problem: <what went wrong, one sentence>
Likely cause: <the probable reason, one sentence>
Suggested fix: <what to do, one sentence>
```

- Explicitly trigger and handle: VLC or Syncplay missing/uninstalled mid-use, party file deleted or corrupted between loading and use, torrent stalled with zero peers, disk fills up mid-download, network drops mid-download (retry with backoff), Syncplay server unreachable, a port already in use.
- Nothing should crash the whole app — every failure returns the user to a safe screen with "Try Again" or "Start Over."
- Add a "View Logs" screen that opens the log folder, for when a friend needs to ask someone technical for help.

**Definition of done:** every scenario above was deliberately triggered by hand and produced the Problem/Likely cause/Suggested fix message, never a crash.

**Write `docs/PHASE_9.md`**, listing every scenario tested and its outcome. **Then stop.**

---

### PHASE 10 — Packaging, Real Multi-Friend Test, and Handoff Docs

**Tasks:**
- Package `/app` into a single Windows `.exe` using PyInstaller (or document why you chose something else), so a guest never needs Python installed — only `setup.cmd` first.
- Test the packaged app on a clean Windows machine/VM with nothing pre-installed except after running `setup.cmd`.
- Run a real multi-machine test: one host + at least two guests, party file shared exactly the way it would be in real use (pasted into a Discord message). Confirm playback actually stays in sync, including pause/play/seek. Fix anything that only shows up once multiple real machines are involved.
- Write `docs/USER_GUIDE.md` (host guide + guest guide, written for someone who has never seen the app before), `docs/DEVELOPER_GUIDE.md` (architecture, how to build/run/package, how to extend), and `docs/PROGRESS.md` (summary of all ten phases with links).
- Tag `v1.0.0`.

**Definition of done:** OpenParty v1.0 — `setup.cmd` + packaged app — tested with real multiple peers, fully documented, ready to send to friends.

**Write `docs/PHASE_10.md`.**

---

## 7. Appendix

### Repo structure
```
/setup
  setup.cmd
  install.log          (generated)
/app
  main.py
  /gui                 (screens/windows)
  /config              (load/validate party files)
  /downloader          (aria2c integration)
  /syncplay             (spawn + monitor syncplay/vlc)
  /vlc                  (detection + path resolution)
  /updater              (reserved — not built in this v1 plan)
  /logs
    launcher.log
    download.log
    syncplay.log
    vlc.log
/docs
  PHASE_1.md ... PHASE_10.md
  config-schema.md
  USER_GUIDE.md
  DEVELOPER_GUIDE.md
  PROGRESS.md
README.md
```

### Party file — full example
See Phase 3 for the schema; that JSON block is the single source of truth for what a "party" is.

---

## 8. Skills — How To Think About This Codebase

This section is background reading for every phase, not tied to any one of them.

### Philosophy
- Never optimize for lines of code. Optimize for maintainability.
- Working software beats "almost complete" software. A feature that's 95% done is still not done.
- Finish one subsystem before touching another.
- Every commit should leave the application runnable.

### Architecture Advice
The Launcher (the app's main coordinator) should **orchestrate, not perform work itself**. Each real job belongs to its own small module:

```
setup.cmd   (installs, once, then gets out of the way)

OpenParty App (Launcher)
      │
──────────────────────────
Config      — load/validate party files
Downloader  — aria2c integration
Syncplay    — spawn + monitor
VLC         — detection + path resolution
Updater     — reserved for future use
```

Loose coupling: the Launcher calls these modules, but they don't need to know about each other.

### Don't Fight Existing Software
One of the most common mistakes is rebuilding something that already exists. Don't.
- VLC already exposes a remote-control interface — use it, don't reimplement playback control.
- Syncplay already handles synchronization — use it, don't build your own sync protocol.
- aria2c already handles resuming interrupted downloads — use it, don't build your own resume logic.

Glue existing software together. Don't replace it.

### Failure Philosophy
Everything fails eventually. Design assuming:
- VLC or Syncplay is missing or gets uninstalled mid-use
- The user deletes or corrupts the party file
- The torrent stalls
- The disk fills up
- The network disappears
- The Syncplay server is unreachable

Nothing should crash. Everything should recover to a safe screen.

### Logging
Every subsystem gets its own log file:
```
launcher.log
download.log
syncplay.log
vlc.log
install.log   (setup.cmd only)
```
If something breaks, there should be exactly one obvious place to look.

### Installer Advice (setup.cmd)
Never assume anything is or isn't already there. Check:
```
VLC?
Syncplay?
aria2c?
winget available?
```
Only install what's missing. Never reinstall software that already works.

### UI Advice
Users are not technical. Never show:
```
Spawn failed with exit code 2
```
Show:
```
Couldn't start VLC.
Try reinstalling VLC.
```
One sentence for the problem. One sentence for the fix.

### Configuration
Human-editable JSON. Never generate unreadable configs.

Bad:
```json
{"a":true,"b":1}
```

Good:
```json
{
  "room": "Movie Night",
  "syncplay_server": "syncplay.pl:8997",
  "torrent": "magnet:...",
  "room_password": ""
}
```

### Documentation
Every folder should explain itself:
```
downloader/
  README.md
  Architecture.md
```
A future contributor should be able to understand the code without needing to ask an AI first.

### Testing
Every phase ends with:
```
Manual Test Checklist
Expected Behaviour
Known Issues
Next Phase
```
(This is exactly what the Phase Completion Doc template in Section 4 captures.)

### Error Messages
Every error shown to a user should contain:
```
Problem
Likely Cause
Suggested Fix
```
Never a raw, unhandled exception.

### Performance
Avoid premature optimization. Focus on:
- startup speed
- install speed
- responsiveness

Don't chase microseconds, memory allocations, or tiny abstractions until real profiling says it matters.

### Security
Never execute arbitrary content from a party file. Validate everything. Never fully trust:
- file paths
- URLs
- filenames
- torrent metadata
- anything typed by a user

### Code Quality
Prefer: small modules, pure functions, descriptive names, composition, dependency injection.
Avoid: god classes, 500-line files, hidden globals, magic numbers.

### AI Working Rules
The agent building this should never:
- rewrite a completed module without a real reason
- change a public interface casually
- refactor working code while building an unrelated feature
- introduce "unrelated improvements" mid-phase

Only solve the current phase's task.

### When Unsure
If two implementations both work, choose the one that's simpler, more maintainable, and easier to debug — in that order.

---

## `/caveman ultra` mode

This mode is **not** the default writing or coding style for this project — richer explanations are usually more useful during planning and architecture work, which is most of what these phases involve. It only activates on request.

When the user types:
```
/caveman ultra
```
switch to engineering mode for the rest of that exchange:

- No motivational text.
- No unnecessary explanations.
- No compliments.
- No filler.
- No "Here's what we'll do."
- Be concise.
- Think first.
- Produce implementation-quality output.
- If information is missing, ask only the minimum number of questions.
- Prefer bullets over paragraphs.
- Prefer concrete examples over abstract discussion.
- Prefer working solutions over theoretical perfection.
- Do not speculate.
- State assumptions explicitly.
- If something is risky, explain why in one sentence.
- Stay focused on the current task.


## Guiding Principles

OpenParty is an orchestrator, not a replacement.

It does not replace VLC.
It does not replace Syncplay.
It does not replace aria2c.

Instead, it automates and coordinates these mature open-source tools into a single, beginner-friendly workflow.

Whenever faced with a design decision, prefer integrating existing software over rebuilding functionality that already exists.



# Party File Specification (`.oparty`)

> **Purpose:** Define the structure, validation rules, and design philosophy of the OpenParty Party File.
>
> This document is the **single source of truth** for the file format used by OpenParty.
>
> Every part of the application that creates, reads, validates, or modifies a party file must follow this specification.
>
> This document intentionally focuses on **the data format**, not the implementation.

---

# Philosophy

The party file is **not** an application configuration file.

It is a **portable description of a watch party**.

Think of it like a boarding pass or an invitation card.

It should contain everything another computer needs to participate in the same watch party, while remaining:

- Human readable
- Human editable
- Versioned
- Future-proof
- Platform independent

The party file should **never** contain information about:

- GUI preferences
- Local file paths
- User settings
- Download locations
- Installed software
- Window size
- Anything specific to one user's computer

A party file should be transferable between completely different computers without modification.

---

# File Extension

Although the file contents are JSON, OpenParty should use its own file extension.

Example:

```
MovieNight.oparty
```

instead of

```
MovieNight.json
```

Internally, the file is still standard UTF-8 JSON.

Using a dedicated extension allows:

- File association with OpenParty
- Easier identification
- Cleaner user experience
- Room for future enhancements

---

# Design Principles

## 1. Human Readable

Someone opening the file in Notepad should roughly understand what every field means.

Avoid abbreviations.

Prefer:

```json
"party_name"
```

over

```json
"pn"
```

---

## 2. Explicit

Never rely on hidden assumptions.

Instead of:

```json
"room":"abc"
```

prefer structured sections:

```json
"sync":{
    "room":"abc"
}
```

---

## 3. Forward Compatible

Future versions of OpenParty should continue supporting older party files whenever reasonably possible.

Every file begins with:

```json
"schema_version": 2
```

The loader is responsible for deciding whether:

- the file is supported
- migration is required
- the file is too new

---

## 4. Platform Independent

Nothing in this file should assume:

- Windows
- Linux
- macOS

No absolute paths.

Never store:

```
C:\Movies\Movie.mkv
```

or

```
/home/user/movie.mkv
```

---

## 5. Portable

Copying this file to another computer should be enough to recreate the same watch party.

---

# Root Structure

The file consists of several independent sections.

```
Root
│
├── schema_version
├── party
├── media
├── sync
├── playback
├── integrity
├── compatibility
└── extensions
```

Each section has a single responsibility.

---

# schema_version

Purpose:

Identifies which version of this specification the file follows.

Example:

```json
"schema_version":1
```

Rules:

- Required
- Integer
- Must be positive
- Never omitted

Future versions should increase this number whenever the file format changes in a breaking way.

---

# party

Contains metadata describing the watch party.

Example

```json
"party":{
    "name":"Friday Movie Night",
    "description":"Marvel Marathon",
    "created_at":"2026-07-09T18:00:00Z",
    "created_by":"Aditya"
}
```

Fields

## name

Human-readable party title.

Required.

Example

```
Movie Night
```

Maximum length should be reasonable.

---

## description

Optional.

Allows the host to include notes.

Examples

```
Bring popcorn

Marvel marathon

Episode 5 watch party
```

---

## created_at

ISO-8601 UTC timestamp.

Example

```
2026-07-09T18:00:00Z
```

---

## created_by

Display name of the host.

Purely informational.

Never used for authentication.

---

# media

Everything related to the media being watched.

```
media
│
├── source
├── file
└── subtitles
```

---

# source

Describes where the movie comes from.

Example

```json
"source":{
    "type":"magnet",
    "value":"magnet:?xt=..."
}
```

Supported types

Initially:

- magnet

Future possibilities:

- http
- https
- ftp
- local-network
- (removed in v2: torrent-file)

Using a type field keeps the format extensible.

---

# file

Information about the expected media.

Example

```json
"file":{
    "name_hint":"Movie.2026.1080p.mkv",
    "size":null
}
```

## name_hint

Optional.

Useful when a torrent contains many files.

Allows OpenParty to automatically select the correct media.

---

## size

Optional.

Expected file size in bytes.

Useful for validation.

---

# subtitles

List of subtitle files.

Example

```json
"subtitles":[
    {
        "language":"English",
        "url":"https://example.com/subtitle.srt"
    }
]
```

Multiple subtitles should be supported.

Do not limit the format to one subtitle.

---

# sync

Everything required by Syncplay.

Example

```json
"sync":{
    "server":"syncplay.pl",
    "port":8997,
    "room":"movie-night",
    "password":""
}
```

---

## server

Hostname only.

Example

```
syncplay.pl
```

---

## port

Integer.

Default

```
8997
```

> Avoid defaulting to 8995 or 8999 — Syncplay's own documentation flags these specific public ports as the most congested. Confirm the current recommended public server/port at syncplay.pl before finalizing this default.

---

## room

Required.

Shared room name.

---

## password

Optional.

Blank means no password.

The application should warn the host when exporting a party with an empty password.

---

# playback

Playback preferences.

Example

```json
"playback":{
    "start_paused":true
}
```

Initially minimal.

Future additions may include:

- fullscreen
- preferred audio language
- preferred subtitle language
- default volume

These are preferences, not requirements.

---

# integrity

Used to verify downloads.

Example

```json
"integrity":{
    "sha256":null
}
```

Optional.

If present:

OpenParty should verify the downloaded media.

If absent:

Normal torrent verification is sufficient.

---

# compatibility

Specifies application compatibility.

Example

```json
"compatibility":{
    "min_openparty_version":"1.0.0"
}
```

Purpose:

If a future feature requires OpenParty 3.0,

older clients should display

```
This party requires OpenParty 3.0 or newer.
```

instead of failing unpredictably.

---

# extensions

Reserved for future plugins.

Example

```json
"extensions":{}
```

Core OpenParty should ignore unknown extension data.

This prevents plugins from breaking compatibility.

---

# Validation Rules

The loader should validate every field.

Validation should stop with a single clear error.

Examples

Good

```
Room name is missing.
```

Good

```
Invalid magnet link.
```

Bad

```
KeyError
```

Bad

```
Object reference not set...
```

Never expose raw exceptions to end users.

---

# Example File

```json
{
    "schema_version": 2,

    "party":{
        "name":"Friday Movie Night",
        "description":"Marvel Marathon",
        "created_at":"2026-07-09T18:00:00Z",
        "created_by":"Aditya"
    },

    "media":{
        "source":{
            "type":"magnet",
            "value":"magnet:?xt=urn:btih:..."
        },

        "file":{
            "name_hint":"Movie.2026.1080p.mkv",
            "size":null
        },

        "subtitles":[
            {
                "language":"English",
                "url":"https://example.com/subtitles.srt"
            }
        ]
    },

    "sync":{
        "server":"syncplay.pl",
        "port":8997,
        "room":"movie-night",
        "password":""
    },

    "playback":{
        "start_paused":true
    },

    "integrity":{
        "sha256":null
    },

    "compatibility":{
        "min_openparty_version":"1.0.0"
    },

    "extensions":{}
}
```

---

# Future Expansion

The schema is intentionally modular.

Future versions may add sections such as:

- chat
- playlist
- chapters
- thumbnail
- poster
- metadata
- host capabilities
- streaming support

without modifying existing sections.

---

# Guiding Principle

The party file should describe **the party**, not **the application**.

If deleting a field would only affect one user's local computer, it probably does **not** belong in the party file.

If deleting a field would prevent another participant from joining the same watch party, it probably **does** belong in the party file.