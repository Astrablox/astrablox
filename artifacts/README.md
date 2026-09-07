# Demo build

`foundation-demo-v4-20260906T1256Z` is the first game AstraBlox built, reviewed and played end to end (September 6, 2026): a two-room dark-fantasy escape. Wake up in a cell, find the iron key, unlock the door, reach the shrine portal. 190 parts, 3 scripts, no enemies.

## Play it without Codex

Open `foundation-demo-v4-20260906T1256Z.rbxl` in Roblox Studio and press Play. The file is the exact Studio **Save to File** result (108342 bytes, SHA-256 `151912fd1a9a397ebe58a0dcbbf2b28f20eed713efed12232e6120e38e1cf5e4`); `foundation-demo-v4-20260906T1256Z.verification.json` records the tree, script hashes and audit inventory that a separate Studio reopen matched.

## Media

`images/cell.jpg`, `images/shrine.jpg` and `images/portal.jpg` are real Studio captures of this build, not renders. Two recordings are attached to the [v0.1.0 release](https://github.com/Astrablox/astrablox/releases/tag/v0.1.0): the 24-second first-person clip shown in the README (12 FPS source packaged at 30 FPS, no game audio) and the raw source recording.

## What the run proved

The player agent completed the route five times with ordinary keyboard input: no teleports, no state grants, no camera writes. The longest run reached a 321-second server clock with zero new console errors. Reset and death, multiplayer, mobile and publication were outside this run.

## Referenced Roblox content

The place references Creator Store audio `108689534998891` (Furnace_fire_crackle1, BlacklightGames) and `1843721367` (LowDrone19, APMOfficial), plus generated ashlar texture assets `76096544225233`, `98200993499019`, `109567810046176` and `132128447716680`. The MIT license covers the AstraBlox framework, not these assets; they keep their own Roblox permissions and were loaded from the original development account.
