# Project Requirements: InstaAddict

**Project Name**: InstaAddict  
**Created**: 2026-09-11  
**Status**: Active  

---

## Overview

InstaAddict is a robust Instagram automation bot written in Python that interacts directly with an Android device or emulator running the official Instagram app via `uiautomator2` and `adb`. It simulates human behavior (scroll speeds, typing delays, random intervals, like/follow ratios) to grow audience engagement safely without using undocumented private web/mobile APIs that trigger instant bans.

---

## Goals and Objectives

### Primary Goals
1. **Human-like UI Automation**: Automate feed interactions, hashtag browsing, blogger follower interactions, and unfollowing with natural touch gestures and randomized delays.
2. **Anti-Detection & Safety**: Respect daily and hourly limits, filter ghost/inactive/business accounts, and detect action blocks gracefully.
3. **Multi-Account & Cloned App Support**: Enable seamless operation across multiple Instagram profiles and cloned apps (Dual Messenger / Parallel Space).

### Secondary Goals
1. **Real-time Reporting & Analytics**: Telegram notifications, session metrics, continuous Markdown run history, and SQLite logging.
2. **Modular Plugin Architecture**: Allow community contributors to add custom engagement strategies easily.
3. **Production Telemetry & Self-Learning**: Isolated error trace logging, unhandled crash interception, full state persistence (crashes and content queue uploads), and automated dog-feeding parameter optimization.
