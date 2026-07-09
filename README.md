An open-source application or rather a "System" which makes it easier to host a watch party in your non-technical friends, with hassel free experience.....

# OpenParty

> **The easiest way to host and join synchronized movie nights—without teaching your friends torrents, Syncplay, or media players.**

---

# Overview

**OpenParty** is a Windows desktop application that automates the entire process of setting up a synchronized watch party using **torrents**, **Syncplay**, and **VLC**.

Instead of asking everyone in a group to install multiple applications, configure media players, copy room names, download the correct file, and manually connect to Syncplay, OpenParty combines the entire workflow into a guided experience that almost anyone can use.

The host simply creates a party and shares a small configuration file.

Guests open that file inside OpenParty, and the application automatically handles everything else—from checking required software to downloading the movie and launching synchronized playback.

Voice and video communication remain intentionally outside the application. Users can continue using Discord, Google Meet, Teamspeak, or any other calling platform they already prefer.

The goal of OpenParty is simple:

> **Remove every unnecessary technical step between receiving a party invitation and watching together.**

---

# Why OpenParty Exists

Watching movies together remotely has always required combining multiple independent tools.

A typical setup usually involves:

* Finding the correct torrent
* Downloading the correct release
* Installing VLC
* Installing Syncplay
* Configuring Syncplay correctly
* Selecting the right room
* Selecting the correct media player
* Loading the correct video
* Ensuring everyone has identical files
* Troubleshooting when someone inevitably misconfigures something

For technical users, this process is manageable.

For everyone else, it quickly becomes frustrating.

OpenParty eliminates this complexity by acting as an intelligent launcher and workflow manager rather than replacing existing software.

Instead of reinventing media synchronization, OpenParty builds on proven open-source tools while hiding their complexity behind a clean graphical interface.

---

# Core Philosophy

OpenParty is built around several guiding principles.

### Simplicity First

Users should never need to understand:

* Magnet links
* Torrent clients
* Syncplay configuration
* VLC command-line arguments
* Download directories
* Media synchronization

If the software can automate something safely, it should.

---

### Existing Tools Are Better Than Reinventing Them

Rather than creating another media player or synchronization engine, OpenParty integrates mature, battle-tested software.

Each component continues doing what it already does well.

* **aria2c** downloads torrents efficiently.
* **Syncplay** synchronizes playback between users.
* **VLC** plays media.

OpenParty simply orchestrates them into one seamless experience.

---

### Beginner-Friendly

The target audience is not developers.

It is a friend who has never used:

* torrents
* command lines
* media synchronization software

Every workflow is designed around minimizing decisions.

---

### Automation Over Configuration

Instead of asking users dozens of questions, OpenParty attempts to:

* detect missing software
* install dependencies
* locate executables
* validate configuration
* launch applications
* recover from common failures

without requiring manual intervention.

---

# How It Works

The entire application revolves around a simple configuration file.

```
        One-Time Setup (run once, ever)
                    │
                    ▼
      Installs VLC, Syncplay, aria2c
                    │
════════════════════════════════════════
                    │
                   Host
                    │
                    ▼
Creates Party Configuration
    │
    ▼
Shares JSON file
    │
    ▼
Guest opens configuration
    │
    ▼
OpenParty validates it
    │
    ▼
Confirms required software is already present
    │
    ▼
Downloads media
    │
    ▼
Launches Syncplay
    │
    ▼
Starts VLC
    │
    ▼
Everyone watches together
```

The configuration file contains everything required to join the party, including:

* Party name
* Magnet link information
* Syncplay server
* Room details
* Optional subtitles
* Metadata

Guests never have to manually type room names or server addresses.

---

# Features

## One-Click Party Joining

Guests receive a single configuration file from the host.

Opening that file begins a guided setup process.

No manual configuration required.

---

## Automatic Dependency Detection

OpenParty automatically checks whether required software already exists.

This includes:

* Python 3.12+ and required packages
* VLC
* Syncplay
* aria2c

Installing this software happens once, through a separate one-time setup step—the everyday app never installs anything itself. If something is missing, OpenParty clearly says so and points back to that one-time setup, then continues normally once it's done.

---

## Guided Setup

Rather than exposing technical details, OpenParty guides users through clear stages:

1. Load Party
2. Check Setup
3. Download Media
4. Launch Watch Party

Each step provides clear feedback and progress information.

---

## Torrent Download Management

OpenParty manages torrent downloads automatically.

Supported sources include:

* Magnet links

During downloads users can monitor:

* Download speed
* Progress
* Estimated remaining time
* Connected peers

Previously downloaded files are detected automatically to avoid unnecessary downloads.

---

## Automatic Playback Synchronization

Once the media is available, OpenParty launches Syncplay with all required parameters already configured.

Users do not need to manually:

* choose a room
* choose a media player
* load the video
* configure servers

Playback begins synchronized across everyone in the room.

---

## Host Mode

Creating a party is designed to be equally simple.

The host enters:

* Movie source
* Party name
* Room information
* Optional password

OpenParty generates a portable configuration file that can be shared through any messaging platform.

---

## Guest Mode

Guests can join by either:

* Opening the shared configuration file
* Pasting the configuration directly into the application

No additional setup is required beyond following the guided workflow.

---

## Intelligent Error Handling

Real-world failures are expected.

Instead of crashing, OpenParty provides clear explanations for situations such as:

* Missing software
* Network failures
* Invalid configuration
* Corrupted downloads
* Permission issues
* Disk space limitations
* Unexpected application exits

Technical details are recorded in log files for troubleshooting while keeping user-facing messages understandable.

---

## Windows-Native Experience

OpenParty is designed specifically for Windows.

This allows it to integrate naturally with:

* Windows installers
* Registry detection
* Native file dialogs
* Familiar installation workflows

Rather than targeting every operating system, the project focuses on providing the best possible Windows experience.

---

# Project Architecture

OpenParty functions as an orchestration layer between several mature open-source applications.

OpenParty consists of two independent pieces: a one-time setup step that installs VLC, Syncplay, and aria2c, and an everyday app that assumes they're already there and never installs anything itself.

```
        One-Time Setup (run once, ever)
                    │
                    ▼
      Installs VLC, Syncplay, aria2c
                    │
════════════════════════════════════════
                    │
             Party Configuration
                    │
                    ▼
          OpenParty App (Python)
                    │
     ┌──────────────┼──────────────┐
     │              │              │
     ▼              ▼              ▼
Dependency      Download      Launch
 Detection       Engine      Synchronizer
     │              │              │
     ▼              ▼              ▼
  VLC         aria2c Torrent    Syncplay
                    │
                    ▼
             Downloaded Media
                    │
                    ▼
            Synchronized Playback
```

Rather than replacing these applications, OpenParty coordinates them through a unified graphical interface.

---

# Intended Audience

OpenParty is designed for:

* Friend groups
* Long-distance movie nights
* Gaming communities
* Online clubs
* Student groups
* Families
* Communities already using Discord or similar platforms

It is particularly valuable for groups where only one or two members are technically experienced.

---

# Design Goals

The project prioritizes:

* Minimal user interaction
* Clear guidance
* Reliable automation
* Robust error recovery
* Predictable workflows
* Clean user interface
* Fast onboarding
* Zero command-line usage

Every feature is evaluated against one question:

> **Does this reduce the amount of technical knowledge required from the user?**

---

# Development Roadmap

OpenParty is developed incrementally through ten structured phases, ensuring the application remains functional after every milestone.

These phases cover:

* Foundation and project structure
* Configuration management
* One-time dependency setup, plus app-side detection
* Torrent downloading
* Syncplay integration
* Host and guest workflows
* Resilience and recovery
* User interface refinement
* Packaging and distribution
* End-to-end validation and documentation

This phased approach keeps the project maintainable while allowing continuous testing throughout development.

---

# Technology Stack

* **Python** — Application language for the entire everyday app
* **PySide6** — Native Qt-based graphical interface
* **aria2c** — Torrent downloading engine, driven over local JSON-RPC
* **Syncplay** — Playback synchronization
* **VLC Media Player** — Media playback
* **winget** — Powers the one-time setup step that installs dependencies
* **JSON Configuration (`.oparty`)** — Portable party definition format

---

# What OpenParty Is Not

OpenParty intentionally does **not** attempt to replace existing communication platforms.

It does not include:

* Voice chat
* Video calling
* Messaging
* Streaming servers
* Media transcoding
* Custom media playback engines

Instead, it focuses exclusively on automating the process of downloading and synchronizing local media playback.

---

# License & Attribution

OpenParty builds upon several excellent open-source projects, including VLC, Syncplay, and aria2c. These projects remain responsible for their respective functionality, while OpenParty provides the orchestration and user experience layer that brings them together into a single, beginner-friendly application.

---

# Vision

OpenParty aims to make remote movie nights as simple as opening a shared file.

No tutorials.

No command prompts.

No manual configuration.

No explaining what a magnet link is.

Just receive a party invitation, click through a guided setup, and start watching together.
