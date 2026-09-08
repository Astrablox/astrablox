# DESIGN — what the player does and how it feels

Owner: the `design` lane. Readers: `code` builds the systems of §4–§8 and cites the section each
value came from; `creatures` builds the bodies and animation of §7 so their tells survive;
`vfx` stages the moments §5–§8 call readable; `ui` shows what §9 requires; `audio` makes audible
what §9 requires; `studio` runs the scenarios of §12 and reports against the feel targets; `story`
owns the fiction this gameplay happens inside.

How this file changes. A system section is rewritten when play shows the system does not produce
its feel target. Values are not written here except in §13, and every entry there names the report
it came from. A system that no longer serves a pillar is deleted from this file, not marked
obsolete. Names of characters, places and creatures belong to `story`; the names used below are
working names until `game/LORE.md` gives others.

Direction from the owner that this design is built on, and that is not this lane's to reverse: the
player is fast, mobile and fragile — constant blinks, no heavy attacks, no parry, she evades and
cuts; the sword is quick and the chain from the fourth game's material is her second weapon;
Elder Blood plus what Yennefer and Triss taught her gives her spells as active abilities, fed by
fighting; traversal is acrobatic; enemies are fast, dangerous and individual, never a generic
swordsman; the input this game is designed for is keyboard and mouse; her animation is authored in
Blender.

Assumptions this file was written on, until `game/VISION.md` or a scene contract says otherwise:
the player is Ciri as a Roblox R15 avatar; the world is the world of the Alders after the events
of the third game; the first scene runs from a pier to the harbour where the Wild Hunt's ship
lies; the enemies of that scene are what remains of the Hunt.

---

## 1. Pillars

Three, in order. Each is a test another lane can apply to its own work and get a yes or a no.

**1. Speed is the whole character.** Ciri is never where the attack lands. Standing still is the
mistake the game punishes, and moving is the thing it rewards — with damage, with resources, with
the next opening. Test: in any encounter, name what the player gains by moving rather than what
they avoid. If moving only avoids, the encounter is a chase, not a fight.

**2. She dies fast and so does everything else.** Two or three mistakes end her, and her blade
ends them about as quickly. There is no trading, no attrition, no bar to grind down. Test: watch a
fight and count how long the player is safe. If the answer is "most of it", the encounter is
tuned for a character this game does not have.

**3. Every enemy is a different problem.** No two enemies in a scene are answered the same way.
Test: take any enemy out of the scene. If nothing about how the player fights changes, that enemy
was filler.

## 2. Core loop

**Moment to moment** (seconds): read what the enemy is committing to, blink through or past it,
cut on arrival, leave before the answer comes. Displacement is the defence, the approach and half
the offence.

**Encounter** (one to two minutes): enter a space that shows what it holds, spend blink charges
faster than they refill, get them back by landing hits, spend the Blood on a spell at the moment
the fight would otherwise catch her, leave with her health lower than when she arrived.

**Scene** (fifteen to thirty minutes): move through a place that opens as the player advances,
meet the same enemies in harder arrangements, gain one capability, reach the landmark that was
visible from the first frame.

The session is a scene. A player who leaves after one has finished something; a player who stays
starts the next from the landmark they just reached.

## 3. Character, camera, controls

**Character.** Ciri: R15 proportions, light on her feet, sword on her back and a chain at her
belt, no armour read anywhere on the silhouette. She jumps, vaults and runs across things that
look like obstacles; the animation lane authors her in Blender to that description — fast, springy,
acrobatic, with no wind-up long enough to feel heavy.

**Camera.** Third person over the shoulder, and in this game it is an aiming device as much as a
viewing one: the blink and the chain both go where the camera is pointed. Rules it obeys: it
follows a blink without a swing that costs the player their bearings; it widens as more enemies
commit; the enemy the player is answering stays in frame; there is no lock that survives a blink
aimed elsewhere. A player who cannot see what hit them calls the game broken before they call
themselves careless.

**Controls.** Nine verbs, no chords, no modifiers: move, jump, blink, attack, chain, two spells,
trace, interact. Every verb is one press or one hold, and every verb is reachable while moving. A
tenth verb is a design decision with a cost, not an addition.

## 4. The feel contract

What `code` implements before any specific system, and what `studio` watches for in the first
playtest.

**Anatomy.** Every damaging action, hers and theirs, is startup, active window, recovery. Startup
is where the read lives; recovery is where the punish lives. Hers are short at every stage —
short enough that an attack is never a commitment she regrets, because a fragile character who
cannot leave an animation is a dead character.

**Response.** Every press has a consequence on the frame it is pressed: she moves, the blade
starts, the blink shows, the chain leaves her hand. The server confirms afterwards; nothing waits
for an effect.

**Buffering.** A press during recovery or hitstun fires the moment the state allows it. The buffer
clears when she takes damage, because a buffered attack that fires out of a stagger is the player
being hit and then punished for it.

**Cancels.** The blink cancels the recovery of anything she does. Attacks chain into each other
along the light chain and into nothing else. Nothing cancels an active damage window, hers or
theirs. This one rule is what makes the kit feel like it belongs to the player.

**Invulnerability.** Only the blink grants it, only at its start, and it ends before the blink
ends. Two sources of invulnerability make every hit unreadable to the player who took it.

**Impact.** A landed hit interrupts the victim's motion; weight comes from the interruption and
the pause on contact, not from a larger number. `vfx` and `audio` dress that moment, they do not
create it.

**Refusal.** Blink with no charge, chain at nothing, spell with no Blood: each is a named refusal
that shows itself. Silence reads as a bug.

**Fragility.** She has few hits in her and nothing restores them inside a fight. That is the
design, not a difficulty setting: everything else in this file exists to give the player the tools
to not be hit. Any system that makes being hit survivable takes the game apart.

**Values.** This file states states, windows, priorities and what the player sees, not numbers.
`code` chooses the values a spec does not give, records them in the tuning module marked as
chosen, and hands them back; after the first playtest they move into §13 with the evidence that
set them.

## 5. Movement, blink and resources

### 5.1 Ground and air
A run that turns instantly and has no acceleration ramp worth feeling. A jump with real height, a
vault over anything at chest level and a mantle onto anything at head level, all from the same
key, decided by what is in front of her. In the air she keeps directional control and she can
blink, attack and throw the chain. Traversal in this game reads as parkour, and nothing about it
is a separate mode: the same verbs that cross a gap win a fight.

### 5.2 Blink
**What it is.** A short displacement in the direction the player is holding — instant, no wind-up,
usable on the ground and in the air, ending with her facing the way she went. It is the most
pressed verb in the game and it must never feel rationed.

**Charges.** The blink runs on charges, not on a bar: a small pool that refills on its own and
refills faster when she lands hits. This is what makes offence feed mobility and what gives a
fight its rhythm — spend, earn, spend. A single charge is never the difference between playing and
waiting: the pool empties only after a run of blinks the player chose to spend.

**States and windows.** Start: invulnerable, the shortest window in the game a player can still
aim. Travel: no damage in or out. Recovery: shorter than any attack she has, but real, so that
blinking on reflex against nothing leaves an opening.

**Priority.** Cancels the recovery of any attack, of the chain, of a spell's follow-through, and
the stagger a light hit caused. Does not cancel her own active damage window. Buffered like every
other input. Chaining blinks is allowed and expected; the limit is charges, never a lockout.

**Bounds and refusal.** Fixed distance, not charged. The destination is the first clear position
along the direction; a blocked path shortens it rather than cancelling it; no legal destination
means an audible refusal. The server re-derives it; nothing about the feel depends on the client
being trusted.

### 5.3 Blink strike
An attack pressed within the moment after a blink is a different strike: it starts instantly, it
comes from the direction she arrived from, and it is the reward for aiming a blink instead of
spamming one. This is the verb that makes displacement an attack rather than an escape, and it is
the heart of the kit. It costs nothing beyond the charge already spent.

### 5.4 The Blood
One pool, spent by the two spells and by the chain's heavier use, restored by landing hits and by
killing. It is not spent by the blink. Two economies exist here on purpose and they do different
jobs: charges are the rhythm of moving, the Blood is the decision of when to use power. Both are
visible at all times and neither needs reading a number.

## 6. Blade, chain and spells

### 6.1 Attack
One button, one chain of fast strikes, no heavy variant. Each strike starts before the previous
has finished mattering; any strike cancels into blink; the chain ends by itself rather than in a
long commitment. Landing hits refills blink charges and Blood. There is no charged attack in this
game: everything slow was cut because a fragile character standing in a wind-up is a corpse.

### 6.2 Chain
Her second weapon, thrown at what the camera is pointing at, and one verb with three outcomes
decided by what it catches:

- A light enemy is pulled to her, arriving off balance and open, which is how she starts a fight
  she was not close enough to start.
- An enemy too heavy or anchored to pull becomes the anchor: she is pulled to it, arriving inside
  its guard. The same happens on a hooked surface, which is how the chain works as traversal — a
  gap crossing that is not a blink and does not spend a charge.
- Held rather than tapped, it binds: the caught enemy's next action is arrested for as long as she
  keeps the tension, and holding it keeps her from attacking. Binding is what she has instead of a
  parry — an answer she chooses in advance rather than one she times on reaction.

The chain has a visible flight time; it can miss and it can be aimed badly. Its heavier uses cost
Blood; the plain pull does not.

### 6.3 Spells
What Yennefer and Triss taught her, used the way a sorceress uses it, not the way a witcher uses
signs. Two in the slice, each on its own key, each costing Blood.

**Fire.** A burst that erupts where she aims and burns the ground briefly. It is the answer to
enemies that gather, and it takes space away from them the way they take it from her. She does not
need to be close to cast it, and casting it does not root her. She has it from the start of the
game: it is the spell that teaches what the Blood is for.

**Hold.** Found later than Fire, and harder to use well. A grip that arrests one enemy in the
middle of what it is doing, cancelling the action outright. This is the answer to the attack that cannot be avoided by moving — a single-target,
resource-priced, chosen-in-advance answer, which is what this game has instead of a defensive
reflex. It does not damage, and a held enemy is not a helpless one for long.

### 6.4 Trace
A pulse that makes a place legible for a short time: what was disturbed here, where a threat is
outside the frame, where the route continues. It costs a little Blood, works in and out of combat,
and it is how this game teaches its world without a line of text. It never marks a solution the
player could find by looking; it makes looking possible.

## 7. Enemies of the first scene

Each enemy below is written as: what player behaviour it exists to force, what its body shows
before it acts, what answers it, and what would make it unfair. None of them is a soldier who
walks up and swings. Every one has a mechanism that punishes standing still and rewards a blink
that was aimed rather than reflexive.

`creatures` builds the body and animation so the tells survive at R15 proportions and at the
distance the camera sits; `code` builds the states; `vfx` and `audio` make a tell louder, never
replace it. A read lives on the body and in sound first; an interface marker is a fallback `ui`
may add and is not this lane's answer to readability.

**Attack roles.** Every attack an enemy owns has one role: close pressure, ranged pressure, or
area denial. An attack with no role is cut before it is built.

**Committed attackers.** Only a stated number may be attacking at once; the rest reposition at
their own spacing. The bound is set per encounter in the scene's `gameplay.md`, and it is what
keeps a fast group fight readable instead of a pile-on.

**Wait time and predictability.** Pressure is set first by how long an enemy waits between actions
and how predictable its choice is, and only then by damage. The first scene stays predictable,
because it is teaching. Nothing in it is slow.

### 7.1 Hoarfrost hound
Forces movement, then forces it again. It runs faster than she does in a straight line and freezes
the ground it runs over, so the arena it lives in gets smaller the longer it lives. It never
attacks from a standstill: it circles wide, plants its feet, and lunges along a line the player
can see because the frost is already there. Answered by blinking across its line and cutting it
during the recovery of a missed lunge — or by killing it early, which is the lesson: some problems
are answered by removing them before they change the room. Unfair if two lunge from outside the
frame at once, so its committed bound in teaching encounters is one.

### 7.2 Riftblade
Forces precision. He blinks the way she does, always arriving at her flank, and his strike is
aimed where she is going rather than where she is: a player who blinks on reflex, in the same
rhythm every time, is hit by every single one of his attacks. His arrival is loud and his blade
comes a beat later; the beat is the read. Answered by blinking late, by blinking towards him
instead of away, or by binding him as he arrives. Killing him is fast — he is as fragile as she
is, which is the point: he is a mirror, and the fight is about who reads whom. Unfair if he can
open with an attack the player has never seen him telegraph, so his first appearance in a scene is
always alone.

### 7.3 Harrower
Forces the chain, and forces the player off the ground. He drives an anchor into the ground and
swings a weighted line around himself, a rotating denial that owns a radius and cannot be
approached at ground level while it runs. Waiting it out is not an answer: the anchor pulls frost
out of the ground and the safe ring shrinks. Answered by going over it — a jump, an air blink, a
blink strike from above — or by hooking the anchor itself with the chain, which rips it out and
leaves him staggered and open. Unfair if the swing outruns her jump, so the arc has a gap she can
see coming and pass through.

### 7.4 Navigator
Forces the player to use his own machinery. He never fights in melee: he opens rifts, steps
through them, sends what is on the other side, and closes the ground with hoarfrost while he does
it. He raises the committed bound of every other enemy while he lives, so the fight gets louder
until he is dealt with. He cannot be reached across the arena by running, and blinking at him
lands the player in the frost — the way through is his own rifts, entered with a chain pull or a
blink, and his rifts stay open a moment after he uses one. Answered by taking his mechanism away
from him. Unfair if the ground closes faster than the player can cross it with the charges a fight
leaves them.

## 8. Damage, reactions and death

Everything in this game is fragile, including her. Enemies stagger from any clean hit except
during their own active windows; nothing in the first scene has armour that ignores her blade,
because a fragile character with no way to interrupt is a character with no offence.

Her health is small and nothing inside a fight restores it. The reward for playing well is not
health, it is charges, Blood and the enemy being dead sooner.

Ragdoll is for death, not for hits: a ragdoll on every hit destroys the position and facing the
player was reading.

Damage taken always names its source in the frame or in sound; an off-screen hit that arrives with
no sound is a defect in the encounter, not in the player.

Death returns the player to the start of the encounter, immediately, with a short restart and no
travel. Death is frequent by design in a game this fragile, so it has to be cheap, and its lesson
has to be visible: after every death, a player should be able to say what they should have done.

## 9. What the other lanes need from this file

`code`: §4 whole; the systems of §5 and §6 with their states, windows, priorities and refusals;
the enemy behaviours and bounds of §7; the per-encounter bounds in the scene's `gameplay.md`.
Values not stated are chosen by `code`, marked as chosen, and returned to this lane.

`creatures`: Ciri animated as §3 describes her — acrobatic, light, no long wind-ups; the bodies of
§7 built so their tells survive at R15 proportions and at combat distance: the hound planting
before a lunge, the riftblade's arrival, the harrower's anchor and the gap in his arc, the
navigator's rift opening. Authored in Blender.

`vfx`: the moments that must read, in priority order — an enemy's startup, the blink's start and
arrival, the blink strike, the chain's flight and catch, a hit that interrupted something. A cue
that hides a tell is a defect in the fight, not in the effect. The frost on the ground is
gameplay, not decoration: where it is drawn is where it hurts.

`ui`: blink charges and the Blood, always, readable without looking away from the fight; the fact
that an action was refused; her health, which matters more here than in most games because there
is so little of it. Nothing else during a fight unless a scene asks for it.

`audio`: every tell has a sound that arrives before the damage and is audible from outside the
frame; the riftblade's arrival and the navigator's rift are heard before they are seen. This is
what makes a fast fight fair.

`studio`: the scenarios of §12 and the feel targets in each scene's `gameplay.md`.

## 10. Input

The game is designed for keyboard and mouse. Movement on the keys; jump where every Roblox player
already expects it; camera and aim on the mouse; attack on the primary mouse button; blink under
the thumb of the movement hand, where it can be pressed at any moment without the fingers leaving
the movement keys; chain on the secondary mouse button, so that aiming it and throwing it are the
same hand; the two spells on the keys next to the movement hand; trace and interact on the keys
Roblox players already expect. Nothing requires two simultaneous presses, and nothing that has to
be pressed mid-fight is far from the movement hand.

A gamepad mapping exists and follows the same rule — blink and chain on the shoulders, attack and
jump on face buttons, spells on the remaining shoulders — and it is not what the encounters are
tuned against.

Touch is not designed for yet, and this file does not pretend otherwise: the kit as written does
not fit four thumb buttons, and a touch layout would change what the kit is. When the studio wants
phones, that is a design decision with a cost, made here, not a layout task handed to `ui`. Until
then, the interface still has to be correct at phone and tablet viewports, because `ui` is judged
at all three.

## 11. Onboarding, teaching and difficulty

Nothing is explained in text. A mechanic is taught by a situation that cannot be passed without
it, in a place where failure costs seconds, and it is tested later in an arrangement that assumes
it. The order of teaching is the order of the scene.

The first thirty to ninety seconds decide whether the player stays and contain no reading: she
moves, the landmark she is heading for is visible, and the first thing she does works. The first
small win comes within the first minutes.

Because she is fragile, the teaching order puts survival before damage: movement, then the blink,
then the strike that comes out of it, then the tools that solve specific enemies.

Difficulty rises in this order: how many may commit at once; which enemies are mixed, since each
demands a different answer; what the space takes away; how long enemies wait between actions; how
predictable their choices are. Health and damage are the last dials, and giving an enemy more
health is not a difficulty change — it is the same fight for longer, which in this game mostly
means more chances to die to something the player already solved.

## 12. The first scene: pier to the harbour

The vertical slice. `story` owns why this happens; this section owns what the player does. The
scene's own file is `game/scenes/<id>/gameplay.md` and holds the encounters in full; what follows
is the shape the scene has to keep. The durations describe intended pace, not targets; the first
playtest replaces them with what was observed.

1. **The pier, alone** (about a minute). Movement, jumps and blink only. Mist, water, a broken
   pier, and the ship at the far end of the harbour visible from the first frame — the landmark
   that makes the scene legible without a word. Broken decking teaches the jump and the vault; a
   gap too wide for either teaches the blink and gives the first win.
2. **Hounds** (about a minute). One, then two, then a pack that arrives together and clusters,
   which is where Fire is worth spending. Teaches the attack chain, the blink strike, that hits
   give charges back, and what the Blood is for. The frost they leave teaches that the ground
   changes.
3. **The first riftblade** (a minute and a half). Alone, in a place with room. Teaches that
   blinking in a rhythm gets punished and that arriving at an enemy is better than fleeing one.
4. **The harbour mouth** (about two minutes). A harrower with hounds around him. The chain is
   found or given just before this — first used to cross a gap, then, in the fight, to rip the
   anchor out. Teaches the chain by needing it twice for different reasons.
5. **The quiet** (about a minute and a half). No enemies. The harbour opens; trace makes the place
   readable. Hold is found here, in the calm, so the set-piece can test it against the one thing
   the player cannot simply move away from.
6. **Under the hull** (two to three minutes). A navigator shaping the ground while riftblades and
   hounds arrive through his rifts, in arrangements the player has met separately. Everything at
   once, and where the pillars are visible or absent.
7. **The ramp.** The landmark reached; the scene ends where the next one starts.

Playtest scenarios for this scene, run by `studio`: the route completed from a fresh start with
ordinary keyboard input; each teaching encounter attempted without using the mechanic it teaches,
to see what the game does with a player who has not learned it; the set-piece played until death
at least three separate times with the reason for each death recorded; a run where the player only
blinks and never attacks, to see whether the fights can be outrun; a run where the player never
blinks, to see how quickly she dies.

## 13. Tuning

Every entry: date, the value or rule changed, the direction, the evidence. Empty until the first
playtest exists; a value in this table with no report path behind it is removed.

| Date | What changed | Direction | Evidence |
|---|---|---|---|
| — | — | — | — |

## 14. Economy and progression

The slice has no currency, no shop and no timers. Progression inside a scene is capability: the
player leaves with something they can do that they could not do before — in the first scene, the
chain and the second spell — and the next scene assumes it. Progression across scenes adds depth
to these nine verbs before it adds a tenth.

What this game will not do: sell power, gate an encounter behind a wait, or spend a player's
attention on a mechanic that exists to bring them back rather than to be played.

## 15. Open questions

Carried here rather than closed silently; each is settled by the lane or person named, and until
then the reading above is what the studio builds.

- Touch support and what it would cost the kit: a design decision for this lane once the owner
  wants phones. The kit above is keyboard-first by the owner's direction.
- Whether the player character is Ciri herself is `story`'s and the owner's call; the kit assumes
  the blink and the Elder Blood belong to the player either way.
- The fiction of the scene — who the Hunt's remnants answer to and what the ship is now — is
  `story`'s; the enemy roles above do not depend on the answer.
- Multiplayer: the slice is written for one player. Nothing above forbids a second and nothing
  above supports one yet.
