# Judge checklist — interface

For a fresh-context judge only. You did not build these screens and you do not fix them: you
report where they fail, with the capture and the place named, so the lane can fix an addressed list.

## What you are given

The target mockup, the built captures at phone, tablet and desktop viewports, the style sheet, and
the acceptance criteria from the task card. Judge the captures, not the report about them.

## How to judge

1. Look at every capture in full before writing anything.
2. Go criterion by criterion. For each one, name the places where it fails: which capture, which
   element, what exactly is wrong, and the mechanism — why it reads badly, not that it reads badly.
   A finding without a location is not a finding.
3. Name the single worst place in the whole set and say why it is the worst.
4. State the verdict last, after the evidence. Pass and fail both cost something: passing a template
   screen puts it in front of the owner and into every later scene as a precedent; failing a screen
   that is actually good spends a scene's time on nothing. A verdict of pass is not free either — it
   requires saying, per criterion, what you examined.
5. If a criterion has no violations, say which elements you checked to conclude that. Do not invent
   findings to justify the pass. Once the real problems are exhausted, invented ones make the next
   revision worse.

## Signs that a screen is a template, not a design

Each of these is observable in a capture. Report the ones you see, with locations.

**Surfaces and shape**
- A frame built from nested rectangles, strokes or gradients where drawn art belongs.
- Corner radius that is uniform everywhere and matches the engine default look.
- A grey or black translucent rectangle used as the only plate on every panel.
- A drop shadow with a hue, or a glow around a panel.
- Stretched border art: corners visibly distorted, which means 9-slice is missing or its centre is
  wrong.
- A visible seam or a doubled corner on a sliced image.
- An image that did not resolve: a flat block, a default texture, a broken aspect.

**Composition**
- Every element at the same visual weight; no single thing the eye lands on.
- A row of equal boxes standing in for a designed set.
- Elements pressed against the edge of their container, or against the screen edge.
- Uniform spacing everywhere, so grouping carries no meaning.
- Content centred by default because nothing else was decided.

**Type**
- A system or engine-default face anywhere.
- Letters set apart from each other in labels, eyebrows or titles.
- More than two families, or a display face used for body text the player reads under pressure.
- Sizes that do not belong to a scale.
- Text with nothing behind it over a bright or busy part of the world.
- A number field that changes width as its value changes, moving the layout.

**Colour**
- An accent colour that appears nowhere in the world.
- Several saturated colours competing on one screen.
- A state communicated by colour alone.
- Palette that would fit any game: neutral dark panel, generic blue or purple accent.

**Controls and state**
- A control with no pressed appearance.
- A disabled control that gives no reason and no path.
- Behaviour that exists only on hover, in a game most players play on touch.
- An empty panel that is simply blank.

**Devices**
- Content under the platform inset, the notch or the top bar.
- Anything important behind the thumbstick or the jump button.
- Text at the phone viewport that cannot be read at the size it renders.
- A layout that only holds at one aspect ratio.

**Motion and life** (judge from a capture sequence where one exists)
- Something looping forever that carries no information.
- A state change with no visible transition at all, in a set where other changes have one.

**Belonging**
- The interface could be moved to an unrelated game unchanged.
- Ornament that appears on no object anywhere in the world.
- Icons of mixed weights and styles, or emoji used as icons.

## What is not a defect

- A detail that means nothing in particular. Not every element has to be justified.
- A difference from the mockup that the lane named as an engine limit, with what it substituted.
- A choice you would have made differently that is internally consistent and holds the criteria.
- Plainness where the design wanted plainness: a quiet plate is not the same failure as a plate
  pretending to be art.

## Output

A list of addresses: capture, element, what is wrong, why. Then the worst place. Then the verdict,
per criterion, with what you examined. Keep each address short enough to be handed to the builder
without rewriting.
