# Characters, rigs, accessories and animation: Blender to Roblox

The engine facts here come from Roblox's creator documentation (linked at the end). Where a route is not documented end to end, it is marked VERIFY ON FIRST RUN: run it once, record what actually happened in the report, and do not describe it as settled before that.

## Do not model the player's body

The player is an R15 avatar. Roblox publishes reference project files with correct topology, UVs, cages, attachments and rig - among them a blocky-proportioned body and blank mannequins in the three body scales - at https://create.roblox.com/docs/avatar/character-bodies/project-files. Fetch the one that matches the game's proportions once, keep it in `assets/library/` with its licence, and use it as the base for everything the player wears: the accessory is modelled against that body, the clothing texture is baked through its UVs, and the animation is authored on its rig. Modelling a body from scratch to sit next to Roblox's own is how proportions drift.

## R15 body, when a character body is actually built

Fifteen mesh objects named `Head_Geo`, `UpperTorso_Geo`, `LowerTorso_Geo`, and `Left`/`Right` `UpperArm_Geo`, `LowerArm_Geo`, `Hand_Geo`, `UpperLeg_Geo`, `LowerLeg_Geo`, `Foot_Geo`. Hierarchy runs `Root > HumanoidRootNode > LowerTorso > UpperTorso > Head / arm chains / leg chains`; the LowerTorso and Root joint sit at 0,0,0. Attachments (`Hat_Att`, `FaceCenter_Att`, `LeftGrip_Att`, `RightGrip_Att`, collar and waist attachments, and the rest) overlap the mesh halfway at the joint they name; rigid accessories find them by exactly these names. Marketplace triangle budgets are head 4,000, torso 1,750, each limb 1,248 - about 10,742 for a body - and textures at most 2048. Those budgets are Marketplace validation, not engine limits; an in-game NPC only has to respect the 20,000-triangle mesh limit, but staying near the avatar budget is what keeps a crowd affordable.

## Avatar Setup: one mesh in, a rigged R15 body out

Studio's Avatar Setup (Avatar tab, on a Model of one or more MeshParts imported through the 3D importer) partitions a humanoid body mesh into the fifteen parts, adds the R15 armature, transfers skinning, builds the cages for layered accessories, adds attachments, and can generate facial rigging. Preset "Development Avatar" is the one for NPCs; "Platform Avatar" adds the Marketplace validation. The mesh must be a humanoid form, face front-facing and visible, exported in T-, A- or I-pose.

This is a Studio panel, not an API: it is driven by a person or by whatever automation the studio has for the Studio GUI, and `execute_luau` cannot press it. Plan for that - when the route is unavailable in a session, the honest result is the body exported and the setup unperformed, named as such, not a claim that it passed. VERIFY ON FIRST RUN: whether this Studio exposes any scripted path to Avatar Setup, and record the answer.

## Rigging in Blender, when the rig is authored

Engine requirements, all of them checkable before export: a vertex is influenced by at most four bones; bone transforms are frozen (scale 1,1,1, rotation 0,0,0); the root bone sits at 0,0,0 and carries no influences; geometry is watertight with no zero-thickness parts; one animation track per exported file. Author in metres with the character facing +Z, and keep symmetry where the body is symmetric.

Skinning is proved by deformation, not by weight colours: pose the rig into its extremes - shoulder raised, elbow fully bent, hip lifted, head turned - and render those poses from the fixed cameras. Candy-wrapper twists at the forearm, volume collapse at the elbow and shoulder, and geometry crossing itself at the hip are the three failures that show up in play and never in a bind-pose render.

For a monster that is not humanoid, an R15 rig is the wrong tool: build the skeleton the body needs and drive it in Roblox with an `AnimationController` and `Animator` rather than a `Humanoid`. Blocky proportions still apply to anything that must read as belonging next to the player's body, per the studio's style contract; a creature the story contract puts outside that language says so in its card.

## Animation: retarget or author

Roblox's own animation library and Mixamo both exist, and the generators used here (`tools/assets/gen3d.py --rig`) return a Mixamo-specification skeleton, not an R15 one; there is no automatic conversion between them. So there are two routes:

- **Retarget.** Import the source clip's armature and the target rig into one Blender file, map bone to bone, apply the rest pose, bake the retargeted action onto the target skeleton, and remove root motion where the game moves the character in code. This is the route for humanoid locomotion, where a hand-authored walk cycle is rarely better than a good retarget.
- **Author.** Key the clip on the rig in Blender. This is the route for monsters and for anything with a telegraph: the shape of the wind-up, the commitment and the recovery are gameplay, not decoration, and no library clip will carry the ones this fight needs.

Craft that decides whether a clip reads: anticipation, then the impact pose with exaggeration, then recovery; easing carries more than speed, and slowing the anticipation reads better than accelerating the strike; the silhouette must be readable at each of those three moments, because that is what a player reacts to. Different attacks need visibly different wind-ups, or the player has nothing to read. The vocabulary players use for failures - stiff, too fast, floaty, lost all its momentum, cannot tell what is going on - names the same defects.

Export one clip per file, named for what it is, and keep the naming stable: the code lane binds to those names.

## Getting a rig and its clips into Roblox

- **Model.** Export GLB and upload through Open Cloud (`tools/assets/upload.py`), which returns a Model package of MeshParts; PBR maps are expected to arrive as a `SurfaceAppearance` but that is VERIFY ON FIRST RUN on this account. The Studio 3D importer is the other route and is a GUI. Rig and skinning data survive both in `.fbx` and `.glb`.
- **Animation.** Open Cloud accepts the Animation asset type as `.rbxm`/`.rbxmx` containing a `KeyframeSequence`, with the documentation's own warning that files edited outside Studio may not function. Studio's Animation Editor imports an animation file onto a rig in the workspace and publishes it, which is a GUI route. VERIFY ON FIRST RUN which of these works unattended here, and record the answer with the evidence.
- **Playing it.** A character with a `Humanoid` loads clips through `Humanoid.Animator:LoadAnimation(animation)`; a rig without one needs an `AnimationController` with an `Animator` child. The lane that writes gameplay code owns when clips play; the lane that made them owns that they exist, are named, and play.

## Accessories

A rigid accessory is a single watertight mesh, at most 4,000 triangles for Marketplace validation, attached at one of the named attachment points; Studio's Accessory Fitting Tool sets up the attachment and previews it on the body scales. Shoulder items on `ShoulderAttachment` move with the arm while `CollarAttachment` items stay put - the choice changes how the piece reads in motion. Before publishing anything: material Plastic, transparency 0, vertex colour at default, no scripts or extra parts inside.

A layered accessory (clothing that deforms with the body - a cloak, a coat) needs inner and outer cages named with the `_InnerCage` and `_OuterCage` suffixes, with vertices and UVs unaltered from the reference cage, and the body it wears must have its own outer cage. Automatic skinning transfer can generate the deformation data at runtime through the `WrapLayer.AutoSkin` property when layered clothing is enabled for the place. Layered is more work and more failure modes than rigid; a cloak that can be rigid without looking wrong should be rigid.

Weapons and hand-held props are rigid accessories on the grip attachments, or ordinary MeshParts welded by code - the second is usual when the item is picked up and dropped in gameplay.

## Classic clothing

Shirts, pants and t-shirts are textures on a fixed UV template, applied through `Shirt.ShirtTemplate`, `Pants.PantsTemplate` and `ShirtGraphic.Graphic`. The template lays the body out in panels - front and back torso squares, side rectangles for torso, arms and legs, and the small squares at the extremities - and designs that run past a panel's edge visibly break at the joints. Roblox's template files and the layout are at https://create.roblox.com/docs/avatar/classic-clothing.

The reliable way to produce one headless is to bake rather than paint: take the reference body, whose UVs already match the template, apply the material built in Blender, bake colour at the template's resolution, and the resulting image is the template image. Painting panels directly in an image editor is the fallback when the design is flat graphics rather than material. Either way the check is the same: apply it to a rig in Studio and look at the joints, where a template error always shows first.

## Sources

R15 body specifications, budgets and attachments: https://create.roblox.com/docs/avatar/character-bodies/specifications - reference project files: https://create.roblox.com/docs/avatar/character-bodies/project-files - Avatar Setup: https://create.roblox.com/docs/avatar-setup - general mesh and skinning rules: https://create.roblox.com/docs/art/modeling/specifications - rigid accessories: https://create.roblox.com/docs/avatar/rigid-accessories/specifications - accessory fitting tool: https://create.roblox.com/docs/avatar/accessory-fitting-tool - layered accessories and automatic skinning transfer: https://create.roblox.com/docs/avatar/layered-accessories and https://create.roblox.com/docs/avatar/automatic-skinning-transfer - classic clothing: https://create.roblox.com/docs/avatar/classic-clothing - playing animations: https://create.roblox.com/docs/animation/using - Open Cloud asset types and limits: https://create.roblox.com/docs/cloud/guides/usage-assets
