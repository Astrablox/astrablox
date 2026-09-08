# Roblox UI API, as of September 2026

Names and behaviour confirmed from official announcements and documentation on the dates given.
The live class schema wins over this file: read the properties of a class in Studio before authoring
against it, and record any difference in the run report.

## Styling

| Instance | What it does |
|---|---|
| `StyleSheet` | Holds style rules; can import other sheets. The single source of values. |
| `StyleRule` | A selector plus a set of property overrides. |
| `StyleLink` | Attaches a sheet to a GUI container; descendants resolve through it. |
| `StyleDerive` | Inherits from another rule set. |
| `StyleQuery` | Activates its child rules while its conditions hold. |

Released out of beta 2026-01-20 (`devforum 4275082`), including the no-code Style Editor.

Selector syntax that is confirmed working:

- class selector: `Frame`, `TextButton`
- name selector: `#InputImage`
- tag selector: CollectionService tags
- child combinator: `>ImageLabel #InputImage`
- pseudo-instances, including several of one class and nested ones: `::UIStroke #1`, `::UIStroke #2`,
  `::UIListLayout`
- global query prefix: `@PreferredInputTouch`

`StyleQuery` properties: `MinSize`, `MaxSize`, `AspectRatioRange`, plus the global device queries
`ViewportDisplaySize`, `PreferredInput`, `ReducedMotionEnabled`, `PreferredTextSize`. Read-only
`IsActive` is true while all conditions hold. Built-in query selectors:
`@PreferredInputKeyboardAndMouse`, `@PreferredInputTouch`, `@PreferredInputGamepad`,
`@ViewportDisplaySizeSmall`, `@ViewportDisplaySizeMedium`, `@ViewportDisplaySizeLarge`,
`@PreferredTextSizeMedium`, `@PreferredTextSizeLarge`, `@PreferredTextSizeLarger`,
`@PreferredTextSizeLargest`, `@ReducedMotionEnabled`. Full release 2026-04-09 (`devforum 4566519`);
`PreferredTextSize` added to the device queries 2026-05-15.

**Styling Transitions** (full release 2026-05-21, `devforum 4646870`): a rule declares how its
property changes tween, so state changes animate without a script or a tween per element. Transition
timing is expressed with TweenInfo attributes on the rule. Use it for hover, press, open, close and
device-variant changes; keep hand-written `TweenService` for motion with a shape a property tween
cannot express (sequenced entrances, motion driven by gameplay values).

## Depth, shape and edge

- `UIShadow` — native elevation shadow. Blur radius is clamped by the engine. Full release
  2026-05-14 (`devforum 4636263`).
- `UICorner` — uniform `CornerRadius` or the four per-corner radius properties; both are styleable,
  and a sheet should style one form or the other, not both.
- `UIStroke` — outline with `ApplyStrokeMode`, thickness in offset; a `UIGradient` inside it gives an
  edge that catches light.
- `UIGradient` — gradient fill and transparency ramp on a frame, image or text.
- `CanvasGroup` — renders a subtree to one surface: `GroupTransparency` fades a whole panel in one
  property instead of a tween per descendant, and `GroupColor3` tints it.

## 9-slice

`ImageLabel`/`ImageButton` with `ScaleType = Enum.ScaleType.Slice` and `SliceCenter` (a `Rect` in
image pixels) keeps corners unscaled while the edges and centre stretch. `SliceScale` multiplies the
border size and is expressed in offset, so at a large viewport a border authored for a phone can
read as thin unless it is scaled with the layout (`devforum 4698112`, 2026-06-22). `UICorner` on a
9-sliced image is applied to every sliced piece separately and produces visible seams
(`devforum 4713370`, 2026-07-02): round the artwork itself instead.

`ScaleType.Tile` with `TileSize` is the equivalent for a repeating pattern (a woven backdrop, a
parchment grain).

## Fonts

- `FontFace` carries family, weight and style; `Font.fromEnum`, `Font.fromName` and `Font.fromId`
  construct it. Weight comes from the family's faces, not from a second family.
- Custom `.ttf`/`.otf` files placed in Studio's local `content/fonts` directory render in Studio only
  and do not replicate to players (`devforum 4524733`, 2026-03-15). Shipping a font means either an
  engine family or a Creator Store font asset used through `Font.fromId` (`devforum 4587295`,
  2026-04-20).
- 85 official font families exist; the period-plausible display candidates for a dark fantasy world
  include Fantasy, Antique, Garamond, GrenzeGotisch, Fondamento, Bodoni and Merriweather. Judge them
  in a capture at the real size, not by name.
- `RichText` supports per-run markup inside a label; `<font face=...>` accepts engine family names.

## Icons

- `lucide-roblox` — the Lucide set uploaded as Roblox images, addressable by name. Browser and
  copy-out at icons.rest (`devforum 4670716`, 2026-06-06); `@nrbx/lucide` exposes over 1,700 icons as
  typed React components (2026-06-23). Tint at runtime with `ImageColor3`.
- Emoji render through the platform emoji font: they ignore `TextColor3` and vary in weight between
  glyphs, so they cannot hold one visual language (2026-06-13).

## Input and focus

- Input Action System, full release 2026-06-11 (`devforum 4678416`): `InputAction`, `InputBinding`,
  `InputContext`; default player scripts can be moved onto it with
  `Workspace.PlayerScriptsUseInputActionSystem`. The Input Action Manager is a Studio panel for the
  action table (beta 2026-07-14).
- `InputActionLabel` (Studio beta 2026-08-06, `devforum 4779420`) displays the current binding of an
  `InputAction` per device with no code, through `PreferredBinding`. This is how a prompt shows the
  right glyph on keyboard, gamepad and touch without three assets and a branch.
- `UserInputService.LastInputType` and `LastInputTypeChanged` — branch on the last input used, not on
  device capability.
- Gamepad focus: `GuiService.SelectedObject`, the `NextSelectionUp/Down/Left/Right` properties,
  `SelectionGroup` with its `SelectionBehavior` for modal containment, `SelectionImageObject` to
  replace the default highlight, `GuiService.MenuOpened`/`MenuClosed` to yield to the platform menu.

## Screen, safe area and layout

- `ScreenGui.ScreenInsets = Enum.ScreenInsets.DeviceSafeInsets` keeps content clear of notches and
  rounded corners; `Enum.ScreenInsets.CoreUISafeInsets` clears the Roblox top bar. The legacy
  `IgnoreGuiInset` boolean handles neither.
- `GuiService:GetGuiInset()` returns the reserved top-bar area.
- `Camera:GetPropertyChangedSignal("ViewportSize")` is the signal to recompute anything derived from
  the viewport; reading the viewport once at startup breaks on rotation and window resize.
- Constraints: `UIAspectRatioConstraint`, `UISizeConstraint`, `UITextSizeConstraint`, `UIScale`.
- Layouts: `UIListLayout`, `UIGridLayout`, `UITableLayout`, `UIPageLayout`, `UIPadding`.
- Scale for anything that adapts, with `AnchorPoint` doing the alignment; Offset for strokes, icon
  padding and fixed insets.

## Cost

- Recycle rows in long `ScrollingFrame` lists (a pool rebound on scroll) instead of instantiating
  every row.
- Turn a screen off with `ScreenGui.Enabled = false`, not with a tree of `Visible` toggles.
- Update labels from change signals; never from `RenderStepped`.
- Fade groups with `CanvasGroup.GroupTransparency` rather than per-descendant tweens.

## To verify on the first real run in this place

Whether `InputActionLabel` is enabled in this Studio (it is a beta flag); whether the Creator Store
font assets this game wants are accessible to the account; how `SliceScale` behaves against the
viewport range this game supports; whether `screen_capture` in Edit mode reproduces the same
rendering as Play for GUI (JPEG softening makes fine stroke work hard to judge — capture at the
largest viewport when judging stroke weight).
