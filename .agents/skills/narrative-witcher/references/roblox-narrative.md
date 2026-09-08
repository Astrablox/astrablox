# What Roblox does to narrative

The craft in the other references was developed for a game with cutscenes, voice acting and a player
sitting still. Here the player is moving, often with other players, usually without sound, and can
leave any conversation. Nothing about the standard of writing changes; what changes is which channel
carries which piece of the story.

## How players actually meet story on this platform

- A developer who ships in the top of the platform puts it flatly: there is no time for tutorials and
  no time for world building here, and that makes it a different skillset. Read that as a constraint
  on delivery, not as permission to write less.
- The games that do carry story here do it through the world, through item and place descriptions,
  and through one memorable speaking character, rather than through exposition. One well-known
  survival game scatters its lore across NPC lines, books, item descriptions and the landscape with no
  official account of events. One well-known horror game gives the player a single talking merchant
  plus documents and announcements. Chapter-based games use the shape "new map, new character, a
  cutscene that answers the previous question and opens the next one".
- Characters that players remember on this platform are legible at a glance and carry exactly one
  intriguing detail that is not explained at first sight.

## The four channels, from Roblox's own case study

The official write-up of a first-party horror game names four channels and how each is used:

1. **Visual cues** — the arrangement of objects. The rule they held: a visual cue must have a reason
   to exist even if no player is ever there to see it.
2. **Lore text** — full-screen text on a deliberate click, written informationally.
3. **Thought reactions** — first-person, observational, triggered near an object.
4. **Announcements** — third-person, shown to everyone at once.

Their own rollback is the most useful part: they first put lore on everything clickable, players could
not tell what mattered, and most of it was removed so that visual cues could carry the rest and the
player's imagination could finish it. They also stopped highlighting objects except the dangerous or
corrupted ones, because highlighting everything is visual noise.

The platform's own quest documentation describes objectives, quantities, rewards and dailies — the
shopping list this studio does not write. Take the data shape from it (a quest has a trigger, an
objective, a reward, a chain) and take the content from the quest design reference. Even its single
narrative example makes the point: the text tells the player not only what to do but why, and the
reward is tied to the story rather than to the loot table.

## Text under motion

- A line has to be readable at a glance, in one bubble or one panel, without voice. That is a
  consequence of how it is read, not a style rule: the player is running while it is on screen.
- Long conversation is legitimate exactly where the player has stopped on their own and chosen to
  listen. That moment has to be earned by the scene, not assumed.
- Assume skipping. The published advice from studios that measured it: keep it short, make the
  emotional state readable from the body rather than the text, put a choice in the middle to pull
  attention back, keep a journal or a summary for whoever skipped, and never punish skipping.
- One strong speaking voice per location or line of quests, with everyone else living in barks and in
  the environment, is the shape that works here.
- The text-to-speech available on the platform is limited in length and mangles invented names; do not
  write anything that only works when spoken aloud.
- Text in a label is readable and translatable; text baked into an image is neither.

## Multiplayer

Other players are in the world while a story beat plays. Decide, per beat, whether it is private to
the player who triggered it or visible to everyone, and say so in the contract, because the code and
interface lanes build it differently. Consequences that change the place itself are seen by everyone
who walks in afterwards, which is what makes them worth writing.

## What this adds up to for a scene here

The environment carries the story first: what stands where, what is broken, what was left behind. Text
is the second layer and stays short. One speaking character per scene carries what only speech can
carry. A quest keeps a one-line summary for the player who skipped everything, and its consequence is
visible in a place the player can walk back into.
