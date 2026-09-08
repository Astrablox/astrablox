---
name: ui-premium
description: The craft of premium game interface and its Roblox implementation - hierarchy and the single anchor, what earns a place on the screen, diegetic and non-diegetic layers, typography, palette taken from the world, ornament and frames as image assets with 9-slice, control states and feedback, motion, touch and gamepad ergonomics, safe areas, and the 2026 Roblox stack (StyleSheet, StyleRule, StyleQuery, Styling Transitions, Foundation, UIShadow, fonts, icons, InputActionLabel). Use when designing or building any HUD, menu, prompt, dialogue, journal, result or transition screen, when writing a style sheet, and when diagnosing why a screen looks like a template. Not a source of gameplay rules, world art or effect craft.
---

# Premium game interface

Reference for building interfaces that read as a game somebody made on purpose. Values here are
facts and starting points to tune against what the screen actually shows, never targets to hit.
Nothing here is a quota: the number of screens, panels and states follows the game.

The judge checklist for this craft is `references/judge-checklist.md`. It is handed to a
fresh-context judge with the captures. Do not read it while you are designing: a catalogue of cheap
forms in front of the person drawing is a menu, not a warning.

## 1. What separates a premium interface from a template

Not polish added at the end. Four decisions taken early:

- **It belongs to one world.** Colour, material, frame craft and typeface come from the game's
  fiction and its rendered world. A dark panel with a blue accent fits every game and therefore
  belongs to none.
- **It is composed, not arranged.** One element carries each screen; the rest support it at lower
  weight. A template distributes weight evenly because nobody decided what matters.
- **Its surfaces are authored.** Frames, plates, ornaments and icons are drawn assets with alpha.
  A template builds a frame out of nested rectangles, strokes and gradients, which reads as engine
  furniture at every resolution.
- **Its values live in one place.** A style sheet holds colour, type, spacing, radius, stroke and
  shadow. A template carries values typed onto instances, which is why its third screen no longer
  matches its first.

## 2. Hierarchy and the single anchor

Every screen has one element the eye lands on first: the objective, the resource about to run out,
the button that continues. Everything else is quieter — by size, weight, contrast, colour
saturation or position. Tools of hierarchy, in the order they carry the most:

1. Position and size within the composition.
2. Value contrast against the plate behind it (not hue).
3. Weight of the typeface.
4. Saturation — the one saturated element on a desaturated screen is read first, which is why the
   accent colour is spent on one thing per screen.
5. Motion — the strongest and most expensive; reserved for change, never for decoration.

Grouping and negative space carry more than decoration: related things sit close, unrelated things
sit apart, and the space around an element is what makes it look expensive. Elements pressed
against the edge of their container read as cheap; every container has padding, and the important
thing sits in open space. Spacing is not uniform: generous between meaning groups, tight inside a
single entity.

## 3. What earns a place on the screen

Two axes, frequency and urgency (WANDR, 2026-07-29):

- Read often and urgent — a permanent slot in a fixed position.
- Read often, not urgent — contextual, or a compact form that never moves.
- Rare and urgent — appears when it applies, loudly.
- Rare and not urgent — a menu, not the HUD.

The test is removal: take the element off and play. If nothing about the player's decisions
changes, it was not earning its slot. The structure that survives contact with a real game is a
small persistent core in fixed positions that never move, plus contextual layers that answer what
is happening. The core is habit; the rest is response.

The opposite failure is real: minimalism does not remove the information need, it relocates the
cost. Hiding the health bar in a game where the player must judge whether to retreat moves that
work into guessing. Minimal is a choice that suits uncertainty as a product (horror), not a
default that suits everything.

## 4. Diegetic, spatial, meta, non-diegetic

The working framework is Fagerholt and Lorentzon's two axes (Beyond the HUD, Chalmers, 2009), still
the standard vocabulary: is the element part of the fiction (can characters perceive it), and is it
placed in the game's 3D space?

- **Diegetic** — in the fiction and in the space: a rune that lights on the blade, a lantern that
  dims as fuel burns, a marking on a door.
- **Spatial** — in the space, not in the fiction: an outline on an interactable, a marker pinned to
  a distant objective.
- **Meta** — in the fiction, not in the space: blood on the camera, frost creeping in from the
  screen edges.
- **Non-diegetic** — neither: the classic overlay panel.

Diegetic is not automatically better. Information rendered at an angle on a curved surface in a
dark room is information the player cannot read. The workable rule for this game: state that
changes slowly and belongs to an object goes on the object; state the player reads under pressure
stays on the overlay, and gets a fiction-consistent frame instead of a fiction-consistent location.
In Roblox, diegetic and spatial layers are SurfaceGui and BillboardGui — they date a game far less
than another label pinned to the top of the screen, and they cost the screen nothing.

## 5. Readability against the world

The interface sits on whatever the renderer draws this frame: fog, fire, snow, a white wall. That
is the difference from product design, and it is settled with a surface, not with a brighter font
colour: a plate, a scrim, a gradient scrim at the screen edge, an outline, or a shadow behind the
glyphs. Validate against captures of the brightest and darkest place of the actual scene, never
against the mockup background.

Console and phone accessibility floors worth knowing (Xbox Accessibility Guidelines): text is sized
so it survives a small screen at a distance, and interactive targets survive a thumb. Touch targets
below roughly 44 points (Apple HIG) or 48 dp (Android) are missed; on phones the hand covers part
of the screen, so anything critical stays out of the bottom corners.

## 6. Typography

- **Two faces at most:** a display face that carries the world (for a dark fantasy world, a serif
  or a broken/blackletter-adjacent display face is the period-correct choice where the world is
  medieval; use it for titles, names and numbers of consequence) and a text face that stays neutral
  and legible at small sizes for everything the player reads under pressure. A single face used for
  both, with weight doing the work, is also a valid decision — two faces chosen at random is not.
- **Hierarchy comes from size and weight,** not from stretching, and not from letter-spacing. Letters
  set apart from each other read as a template treatment and destroy word shape at small sizes;
  where an eyebrow or a label needs separation, use weight, colour or a rule line.
- **A scale, not arbitrary sizes.** Pick a small set of steps and use only those, in the style sheet.
- **Line height is set, not inherited.** Long lines get more leading, single-line labels get less.
  Line length that runs past comfortable reading gets a narrower container, not a smaller face.
- **Numbers that update need reserved space** and a fixed alignment, or the layout jumps every time
  the value changes. Roblox has no tabular-figure switch: reserve the width of the widest value the
  field can hold, right-align, and test with the widest value.
- **Text scales inside a band.** Scale-driven text needs a size constraint so it stays readable on a
  phone and does not become a poster on a desktop.

## 7. Palette from the world

The palette is sampled from the built scene and the target frame: the dominant material colours,
the light colour, the shadow colour. The interface then lives in a narrow, mostly desaturated band
of that palette, so that one saturated accent — taken from a real thing in the world, not from a
generic UI blue — reads instantly. Colour never carries information alone: a state that is only red
is invisible to a colour-blind player and to anyone under a red sky, so it also changes shape, icon
or position.

Depth is built from value and transparency, not from a drop shadow with a hue: a plate slightly
darker than the world behind it, a thin light stroke on its top edge, a soft shadow underneath.
Shadows are neutral or the scene's shadow colour, never a coloured glow around a panel.

## 8. Ornament, frames and plates

Ornament is what a civilisation makes: if the smiths of this world beat iron into a specific leaf,
that leaf is on the frame. Ornament that appears nowhere on any object in the world is decoration,
not identity, and it reads as a store asset.

Where ornament goes: on the edges of what matters most, and nowhere else. Density is a hierarchy
tool - the quest panel can carry a worked frame while the ammo counter carries none.

Frames, plates, dividers, corner pieces and mask shapes are image assets with alpha, authored for
this game, imported and scaled with 9-slice so the corners never stretch. In Roblox this is
`ImageLabel.ScaleType = Enum.ScaleType.Slice` with `SliceCenter` set to the inner rectangle. Two
traps: `SliceScale` is in offset, so on a large viewport the border can look thin unless it is
scaled with the layout; and `UICorner` on a 9-slice image is applied to each sliced piece
separately, so round the art itself instead of adding a corner object.

Where a design wants a plain plate, a plain plate is right. The failure is engine primitives
pretending to be art: three nested frames with strokes standing in for a frame that should have
been drawn.

## 9. Icons

One icon set, one stroke weight, one optical size, aligned to the same grid; icons drawn at
different weights read as a collection of downloads. `lucide-roblox` gives the whole Lucide set as
uploaded Roblox images addressable by name (icons.rest, 2026-06-06; `@nrbx/lucide` for React, over
1,700 icons, 2026-06-23), which is the fastest way to a consistent set, tinted at runtime with
`ImageColor3`. Fantasy-specific glyphs that Lucide does not have are authored as assets in the same
weight.

Emoji are not icons: they render through the platform emoji font, ignore `TextColor3`, and vary
between glyphs, so a screen using them cannot hold one visual language (`@rbxts-ui/icons`,
2026-06-13).

An icon alone is a guess unless its meaning is conventional; pair it with a label wherever the
player must be sure, and keep the icon-only form for controls the player uses constantly.

## 10. States and feedback

The states that exist for controls: default, hover, pressed, disabled, selected, focused, loading,
empty, error. Which ones a control needs is a decision; a control with no pressed state feels dead
on touch, where most players are, and hover does not exist there at all — anything reachable only
by hover is unreachable for them.

- **Pressed is felt, not just seen:** the change starts at the moment of touch, not at release.
- **Disabled says why,** or at least what would enable it. A grey button with no explanation reads
  as a broken game.
- **Refusals are answered where the player was looking** — at the control they pressed, not in a
  log at the top of the screen. Feedback that arrives noticeably late reads as a bug in the game.
  The practical threshold quoted across game UI practice is about a tenth of a second.
- **Empty is designed:** an empty journal says what will appear there and what fills it.
- **Loading is bounded:** if a screen can wait on the server, it shows that it is waiting, in place.

## 11. Motion

Motion exists to say something changed, and it ends. Principles, not numbers:

- **Enter and exit are not symmetric.** Something arriving deserves more time than something
  leaving; a dismissal that lingers makes the game feel slow.
- **Easing carries meaning.** Deceleration reads as a thing settling into place; acceleration reads
  as a thing leaving; a slight overshoot reads as physical weight and is spent on rare, important
  arrivals. Linear reads as mechanical and belongs to progress and timers.
- **Duration is set by distance and importance,** and by the fact that the player will see it
  hundreds of times. A frequently repeated transition is short enough to never be waited on; a
  once-per-session transition can breathe.
- **Animate transform and transparency,** which are cheap; animating layout properties reflows the
  tree. In Roblox, group fades run through `CanvasGroup.GroupTransparency` rather than one tween per
  descendant.
- **Nothing loops without carrying information.** A continuous shimmer costs attention every second
  the player is on the screen and is the first thing a reviewer sees.
- **Respect reduced motion.** The styling system exposes it as a query (`@ReducedMotionEnabled`),
  and the fallback is an instant state change, not a broken screen.

## 12. Ergonomics: touch, gamepad, screen

- **Design at the smallest supported viewport first.** A HUD designed at desktop and shrunk becomes
  unreadable; one designed at a phone viewport and expanded gains air.
- **Safe areas are read, not guessed:** `ScreenGui.ScreenInsets = Enum.ScreenInsets.DeviceSafeInsets`
  keeps content out of notches and rounded corners, and `GuiService:GetGuiInset()` returns what the
  top bar reserves. React to `Camera:GetPropertyChangedSignal("ViewportSize")` rather than reading
  the viewport once.
- **The mobile control zones belong to the player:** the thumbstick and the jump button own the
  bottom corners, and a hand covers part of the screen. Nothing important lives there.
- **Branch on the last input, not on the device:** `UserInputService.LastInputType` and
  `LastInputTypeChanged`, because a desktop player can pick up a gamepad mid-session.
- **Gamepad needs a focus model:** `GuiService.SelectedObject` is set when a menu opens, the
  `NextSelection*` properties wire the order, `SelectionGroup` contains focus inside a modal, and
  `SelectionImageObject` replaces the default highlight so the selection looks like your game.
  `InputActionLabel` (Studio beta, 2026-08-06) shows the correct binding glyph per device with no
  code, driven by `PreferredBinding` from the Input Action System (full release, 2026-06-11).
- **Navigation is a stack, not a set of booleans,** so the platform back button and the gamepad B
  button behave the same everywhere.

## 13. The Roblox stack in 2026

Full API names, dates and sources: `references/roblox-ui-api.md`. In short:

- **Styling is native.** `StyleSheet` holds `StyleRule`s; a `StyleLink` attaches a sheet to a
  container; rules select by class, by name and by tag, with child combinators and pseudo-instances
  (`::UIStroke #1`, `::UIListLayout`). Fully released 2026-01-20. This is where every colour, size,
  spacing, radius, stroke and shadow value lives.
- **Responsiveness is declarative.** `StyleQuery` activates rules on `MinSize`, `MaxSize`,
  `AspectRatioRange` and on global queries — `@PreferredInputTouch`, `@PreferredInputGamepad`,
  `@ViewportDisplaySizeSmall/Medium/Large`, `@PreferredTextSize*`, `@ReducedMotionEnabled`. Fully
  released 2026-04-09. Device variants are rules, not scripts.
- **Transitions are declarative.** Styling Transitions tween property changes defined in the sheet
  (full release 2026-05-21), so hover, press and open states animate without a tween per element.
  Hand-written tweens remain for motion with a shape the sheet cannot express.
- **Depth is native.** `UIShadow` for elevation and per-corner radii on `UICorner` (full release
  2026-05-14), `UIStroke` with a gradient for an edge that catches light, `UIGradient` for the plate
  itself. Blur radius on shadows is clamped by the engine.
- **Foundation** is Roblox's own React-lua component set (the one the client, Studio and website are
  built with), with a community Fusion port (2026-06-27). Read it as the reference for how a
  finished control behaves — focus, states, keyboard and gamepad handling — even when building the
  control by hand.
- **Fonts.** Custom `.ttf`/`.otf` files cannot be shipped: local font files work only in a Studio
  content directory and do not replicate to players. The shippable choices are the engine font
  families (85 official families, including the fantasy-usable ones) and fonts from the Creator
  Store loaded with `Font.fromId`. Weight and style are set on the `FontFace`, not by picking a
  second family.
- **Layout.** `UIListLayout`, `UIGridLayout`, `UIPadding` over manual positioning; Scale plus
  `AnchorPoint` for anything that must adapt; Offset for strokes, icon padding and fixed insets;
  `UIAspectRatioConstraint` where a shape must not distort; `UISizeConstraint` to stop panels
  becoming absurd on ultrawide; `UITextSizeConstraint` to keep scaled text in a readable band;
  `UIScale` for a single global scale control.
- **Cost.** Long lists recycle rows instead of instantiating everything; a screen that is not on is
  `ScreenGui.Enabled = false` rather than a tree of `Visible` toggles; labels update on change
  signals, never on `RenderStepped`.

## 14. Sources

- UI Styling full release (StyleSheet, StyleRule, Style Editor), 2026-01-20:
  https://devforum.roblox.com/t/full-release-ui-styling-is-officially-released/4275082
- StyleQuery and pseudo-instance styling, full release 2026-04-09:
  https://devforum.roblox.com/t/full-release-stylequery-more-styling-features/4566519
- Styling Transitions, full release 2026-05-21:
  https://devforum.roblox.com/t/full-release-styling-transitions/4646870
- Shadows and individual corners, full release 2026-05-14:
  https://devforum.roblox.com/t/full-release-new-ui-capabilities-shadows-individual-corners/4636263
- Input Action System full release 2026-06-11:
  https://devforum.roblox.com/t/full-release-input-action-system-ias-newly-converted-player-scripts/4678416
  and InputActionLabel Studio beta 2026-08-06:
  https://devforum.roblox.com/t/studio-beta-no-code-hotkey-hints-with-inputactionlabel/4779420
- Fusion port of Roblox's Foundation library, 2026-06-27:
  https://devforum.roblox.com/t/fusion-foundation-a-fusion-port-of-robloxs-foundation-library-used-to-create-native-components/4706377
- lucide-roblox icon library (icons.rest), 2026-06-06:
  https://devforum.roblox.com/t/iconsrest-the-easy-lucide-roblox-icon-library/4670716
- Custom font files in Studio and why they do not ship, 2026-03-15:
  https://devforum.roblox.com/t/how-to-actually-load-custom-font-files-ttfotf-in-studio-and-use-them/4524733
- 9-slice `SliceScale` in offset, 2026-06-22:
  https://devforum.roblox.com/t/introduce-enumslicescalemode-for-9-slice-ui/4698112 ; UICorner applied
  per slice piece, 2026-07-02: https://devforum.roblox.com/t/uicorner-applies-individually-to-each-section-of-a-9-slice-image/4713370
- Roblox UI across phone, console and PC — safe areas, input model, gamepad focus, list recycling,
  2026-07-13: https://simplified.media/guides/roblox-ui-systems
- HUD design: frequency/urgency, the removal test, contrast against renderer output, feedback
  latency, the minimal-HUD trap, 2026-07-29: https://www.wandr.studio/blog/game-hud-design
- Diegetic / spatial / meta / non-diegetic framework, 2026-05-14:
  https://nastyrodent.com/diegetic-and-non-diegetic-ui/ (after Fagerholt and Lorentzon, 2009)
- Roblox UI documentation: https://create.roblox.com/docs/ui/styling ,
  https://create.roblox.com/docs/ui/9-slice , https://create.roblox.com/docs/ui/size-and-position
