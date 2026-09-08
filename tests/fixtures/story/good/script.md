# Scene millford — script

Synthetic fixture for tools/story/contract_check.py. Its content is deliberately plain: it exists to
exercise the parser, not to show anyone how a scene is written.

## Theme
The village lives off a crossing it can no longer keep open.

## Place
The mill stands above a ford that silted up two winters ago. The wheel is stopped and the race is dry;
the dry knocking of it (MillWheelDry) carries over the yard, and slack water (FerryWater) answers from
the landing. Grain Sacks stand where the carts should be, and the bottom row has gone sour.

## NPCs

### NPC: Aldo
Place: Mill Yard
Schedule:
- morning — Mill Yard — splitting the axle blocks he cannot use
- evening — Ferry Landing — counting the crossings nobody made
Lines:
- rain — "Water everywhere and none of it under the wheel."
- after the ferry is raised — "Now it floats. Now."

### NPC: Neska
Place: Ferry Landing
Schedule:
- morning — Ferry Landing — bailing the boat
- night — Burnt Barn — sleeping where the roof holds
Lines:
- first meeting — "Coin first, then the far bank."

## Quests

### Quest: The Sunken Ferry
Place: Ferry Landing
Trigger: The player finds the ferry rope cut and the boat under water at the landing.
Goal: Get the crossing working again before the miller's grain rots.
Choice:
- Raise the boat — costs the player two days of Neska's labour and her trust in the miller
- Buy the barge — costs the grain money the village kept for winter
Consequence:
- Raise the boat — FerryRaised: Neska stops working the landing and the boat leaks again by the third week
- Buy the barge — BargeBought: the grain store stands empty and the winter queue forms at the Mill Yard
Reward: The crossing opens and the far bank becomes walkable.

## Points of interest

### Point: The Burnt Barn
Place: Burnt Barn
Story: Someone slept here after the fire and left the Cut Rope under the straw.
Change: Once the crossing works, the barn is used for grain and the straw is cleared.

## Journal
The ferry sank, the crossing is shut, and the player either raised the old boat or paid for a barge.
