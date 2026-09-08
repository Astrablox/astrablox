# What to take from interfaces that worked

Mechanisms, not pictures. Each entry says what the game solved, the mechanism behind it, and what
breaks if it is copied without its context. None of these is a look to reproduce.

## The Witcher 3 — the interface as an artefact of the world

- **The document, not the panel.** The journal, bestiary and quest log read as written by someone in
  the world, on a material the world uses, in a display face that matches the period. The mechanism
  is fiction consistency in the frame and the voice, while the layout underneath stays a normal,
  legible two-column document. Take the frame and the voice; do not take a layout that is hard to
  scan because it imitates a manuscript.
- **The radial under pressure.** The sign wheel slows time and offers a small set of choices at
  thumb-reachable angles, so a controller can pick in combat. The mechanism is: a choice made under
  pressure gets a fixed spatial position per option, so it becomes muscle memory rather than reading.
- **Item identity by frame.** Rarity and type are read from the border treatment and colour of the
  slot before the name is read. The mechanism is: information encoded in the container, not added as
  another line of text.
- **Its failure is the lesson.** The launch interface was criticised for text too small to read at TV
  distance and an inventory dense enough to get lost in. Beautiful material work does not survive an
  unreadable size, and a scaling option is not a substitute for designing at the small size first.

## Elden Ring — the persistent core reduced to what changes under pressure

- **Only volatile state is permanent.** Health, stamina and the resource bars sit in one corner and
  never move; everything else — item pickups, area names, prompts — appears, says its piece and
  leaves. The mechanism is the frequency and urgency test applied ruthlessly.
- **Guidance in the world, not on the screen.** Direction comes from light, silhouette and level
  design rather than from a marker on the HUD. The mechanism is: an interface element removed after
  the world was given the job, not before.
- **Contextual prompts are strictly conditional.** The prompt exists only while the interaction is
  possible, in the same screen position every time.
- **Do not copy the sparseness by itself.** It works because the game is built so that the missing
  information is available in the world. Removing elements without moving their job somewhere else
  produces guessing, not elegance.

## Hades — art direction carried entirely by authored assets

- **Every surface is drawn.** Frames, portraits, boon cards and dividers are painted assets with
  their own edges and wear, not engine rectangles with a stroke. This is the single largest reason
  the interface reads as expensive, and it is the mechanism this studio copies most directly.
- **Faction colour as an information channel.** Each god owns a colour and an ornament, so the
  player knows the source of an offer before reading a word.
- **The card as a self-contained composition.** Icon, name, one line of effect, rarity in the frame:
  a choice screen readable at a glance mid-run because each unit is composed rather than listed.
- **Feedback is layered and immediate:** the same instant carries a visual pop, a sound and a short
  shake, which is what makes a menu feel responsive rather than merely fast.
- **Do not copy the density of ornament** onto elements the player reads constantly; in Hades the
  worked frames sit on choice moments, while the in-combat HUD is quiet.

## Genshin Impact — one interface across phone and desktop

- **Corner anchoring and thumb zones.** Everything actionable lives where a thumb reaches on a phone,
  and the same layout expands on desktop without redesign. The mechanism is designing the smallest
  viewport first and letting scale-driven sizing and constraints do the rest.
- **Cooldowns as shape, not text.** Ability state is a sweep and a fill on the icon, readable in
  peripheral vision, with the number secondary.
- **A narrow palette with one metal accent.** Gold on desaturated glass reads premium because it is
  spent on one thing per screen.
- **Thin ornament at corners only.** Frame decoration is applied to the corners of panels and nowhere
  else, so it never competes with content.
- **Do not copy its menu density** into a game with fewer systems: the density is a consequence of
  the number of systems, and imported wholesale it makes an empty game look padded.

## God of War (2018) — the HUD that leaves

- **Dynamic presence.** Elements fade out when nothing is at stake and return instantly when combat,
  low health or an interaction makes them matter. The mechanism is a state machine on visibility
  driven by gameplay events, not a player setting.
- **Edges hug the frame.** With an over-the-shoulder camera, the centre of the screen belongs to the
  action; the interface lives against the edges and never crosses the aim line.
- **Damage feedback as position, not just numbers.** Direction of incoming damage is shown as an
  indicator around the character rather than a text log.
- **Do not copy the fade** into a game where the player must plan with the hidden information; the
  fade works because the information is only needed during the moment it returns for.

## What all five share

- One anchor per screen, and everything else quieter.
- Authored surfaces, one icon language, one type scale.
- Information encoded in shape, colour and position before it is encoded in text.
- Contextual layers that appear and leave, over a small permanent core that never moves.
