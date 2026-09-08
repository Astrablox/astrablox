# Scene <id> — gameplay

Owned by the `design` lane. Read by `code` (systems and bounds), `creatures` (enemy roles and
reads), `vfx` and `audio` (what must read and be heard), `ui` (what must be visible), `studio`
(playtest). The systems this file names are specified in `game/DESIGN.md`; this file never
respecifies a system, it names it and states what this scene does with it.

A heading with nothing true under it is deleted, not filled.

## Feel
<One paragraph: what the player experiences moving through this scene, in terms of what they do
and what happens to them. Not how it looks, and not a word for a sensation.>

## Systems used
<One line per system: the system's name and the section of game/DESIGN.md that specifies it. A
system this scene needs and DESIGN.md does not specify yet is written there first.>

## Space
<What the space gives the player and what it takes away: where the ground is safe, where it
narrows, what blocks sight, what can be crossed only with a movement verb, where a fight can go
when it is lost. Written from the target frames and the world lane's layout, and naming the
places the encounters below use.>

## Minute by minute
<Ordered beats from entering the scene to leaving it, each with what the player is doing and the
pace it is meant to have. Quiet stretches are beats too. If two consecutive beats ask the player
for the same thing, one of them changes or goes.>

## Encounters
<One block per encounter, in the order the player meets them. For each:>

### <encounter name>
- Space: <where in the scene, and what that ground gives and takes here>
- Enemies: <which, how many, and the role each plays in this fight>
- Mechanics: <the player verbs this encounter is about and the enemy mechanisms it uses, each
  named as it is named in game/DESIGN.md>
- Committed at once: <how many may be attacking at the same time; the rest reposition>
- Teaches or tests: <the mechanic, and whether this is where the player learns it or where the
  game assumes it>
- The answer: <what in the player's kit solves this, and that they already have it here>
- Feel target: <what the player should be experiencing, and the moment in a playtest where you
  would see it failing>
- Fail state: <what happens when the player loses, and where they resume>

## Teaching
<Each mechanic this scene introduces: the situation that cannot be passed without it, where
failure is cheap, and the later encounter that assumes it. Nothing here is taught in text.>

## Points of interest
<What a player finds by looking rather than by being told, what it changes for them, and what
makes it visible from the route. Purely narrative objects belong to story's script, not here.>

## Difficulty
<Which dials this scene uses and in what order — how many commit, which roles mix, what the space
takes away, how long enemies wait, how predictable they are. What the scene deliberately does not
use yet.>

## What this scene needs from other lanes
<Needs, not solutions: what code must build, what creatures must deliver so the reads survive,
what must read visually, what must be audible from outside the frame, what must be on screen.
Each named against the encounter that needs it.>

## Playtest scenarios
<What studio runs and what to watch: the route from a fresh start with ordinary input on the
input this game is designed for, the encounters played by someone who has not learned the mechanic
they teach, the hardest fight played until death with the reason for each death recorded, and a
run that abuses one verb to see whether the scene can be trivialised by it.>

## Tuning
<Empty until this scene has been played. Then one line per change: date, what changed, the
direction, and the report or capture that showed it. A change with no evidence behind it is
removed.>

## Assumptions and open questions
<Decisions taken where the story contract or the card was silent, and questions closed by another
lane. Each with the reading the studio is building on until it is answered.>
