# bpy patterns for Blender 4.x, headless

Working snippets for the operations the craft file describes, written for `blender -b --python script.py`. They are patterns to adapt, not a pipeline to run in order. API names below are the 4.x ones; when a call is rejected, read the operator's signature in this Blender build rather than trying remembered variants.

## Running and saving

```python
import bpy, math, os
from mathutils import Vector

def save(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)   # start from nothing, not from the startup cube
```

Arguments after `--` belong to the script: `args = sys.argv[sys.argv.index("--") + 1:]`.

## Selection and active object

Most operators act on the selection and the active object, and in background mode nothing is selected by default:

```python
def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
```

Data-level edits (`obj.data.vertices`, modifiers, materials) do not need selection; `bpy.ops` does.

## Transforms: apply scale before anything measured in metres

```python
activate(obj)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
```

Unapplied scale gives uneven bevels, wrong dimensions in the export verification, and wrong texel density.

## Origin at the base centre

```python
activate(obj)
bpy.context.scene.cursor.location = (
    (obj.bound_box[0][0] + obj.bound_box[6][0]) / 2 * obj.scale.x + obj.location.x,
    (obj.bound_box[0][1] + obj.bound_box[6][1]) / 2 * obj.scale.y + obj.location.y,
    min(v[2] for v in obj.bound_box) * obj.scale.z + obj.location.z,
)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.context.scene.cursor.location = (0, 0, 0)
obj.location = (0, 0, 0)
```

A piece exported with its origin anywhere else cannot be dropped on a surface by whoever places it.

## Bevel, smooth shading, weighted normals

```python
b = obj.modifiers.new("Bevel", "BEVEL")
b.width = 0.012            # metres; scale it to the object, not to a habit
b.segments = 2
b.limit_method = "ANGLE"
b.angle_limit = math.radians(35)
b.harden_normals = True    # needs smooth shading to have any effect

activate(obj)
bpy.ops.object.shade_auto_smooth(angle=math.radians(40))   # 4.1+; the old mesh.auto_smooth_angle is gone

w = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
w.keep_sharp = True
```

Order matters: bevel before weighted normals, both after applied scale.

## Array, mirror, boolean, and the cleanup they require

```python
a = obj.modifiers.new("Array", "ARRAY")
a.count = 6
a.use_relative_offset = False
a.use_constant_offset = True
a.constant_offset_displace[0] = 2.0        # the kit's grid step in metres

activate(obj)
for m in list(obj.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
```

After a boolean, also delete the faces that ended up inside the solid: in Edit mode, `bpy.ops.mesh.select_all(action="DESELECT")`, `bpy.ops.mesh.select_interior_faces()`, `bpy.ops.mesh.delete(type="FACE")`.

## Curvature and occlusion masks in a material

Edge wear and dirt come from the form, not from noise. Curvature is available as the Geometry node's Pointiness, remapped through a colour ramp; occlusion for the shader is the Ambient Occlusion node.

```python
mat = bpy.data.materials.new("M_TimberDark"); mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
geo  = nt.nodes.new("ShaderNodeNewGeometry")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.45      # narrow band = wear only on the sharpest edges
ramp.color_ramp.elements[1].position = 0.55
mix  = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
nt.links.new(geo.outputs["Pointiness"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
mix.inputs[6].default_value = (0.10, 0.08, 0.06, 1)   # base
mix.inputs[7].default_value = (0.38, 0.32, 0.25, 1)   # exposed edge
nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
```

Pointiness needs geometry to read: it is a per-vertex measure, so a face with four vertices gives it nothing. Bevel first, then mask.

A vertical gradient (waterline, dust settling, weathering from the top) comes from `ShaderNodeTexCoord` Object output separated with `ShaderNodeSeparateXYZ` and remapped through a ramp - not from a noise texture.

## UVs before baking

```python
activate(obj)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
```

For a piece the player inspects, mark seams where a real object has seams and use `bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.02)`; islands must not overlap, or the bake writes two surfaces into one place.

## Checking a baked image without opening it

```python
import numpy as np
px = np.array(bpy.data.images["Piece_color"].pixels[:]).reshape(-1, 4)
print("min", px[:, :3].min(), "max", px[:, :3].max(), "mean", px[:, :3].mean())
```

All zeros means the bake failed. A single value everywhere means the material had nothing to bake. Magenta means a missing image reference.

## Leaf cards and clustered scatter

A canopy is a few intersecting cards, not a volume of leaves:

```python
bpy.ops.mesh.primitive_plane_add(size=1.2)
card = bpy.context.object
card.data.materials.append(foliage_mat)          # alpha in the material, not modelled holes
```

Scatter with geometry nodes when the count is large, and cluster rather than spread evenly:

```python
mod = ground.modifiers.new("Scatter", "NODES")
ng = bpy.data.node_groups.new("Scatter", "GeometryNodeTree"); mod.node_group = ng
# distribute_points_on_faces (density from a texture or a weight group, not uniform)
# -> instance_on_points (collection of two or three card clusters)
# -> rotate_instances (random Z) -> scale_instances (random range)
```

Apply the modifier before export, and check the triangle count after applying: scatter is the easiest way to blow the mesh budget.

## Camera reconstructed from a reference image

```python
cam_data = bpy.data.cameras.new("RefCam"); cam = bpy.data.objects.new("RefCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam_data.lens = 35; cam_data.sensor_width = 36
cam.location = (0, -18, 1.7)                       # eye height and distance read off the reference
d = Vector((0, 0, 1.2)) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam_data.show_background_images = True             # background image + a flat render = the overlay check
bg = cam_data.background_images.new(); bg.image = bpy.data.images.load("game/scenes/x/target.png"); bg.alpha = 0.5
```

Set the render resolution to the reference's aspect before judging an overlay; a mismatched aspect makes every proportion look wrong.

## Human stand-in for scale

```python
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.7, location=(1.5, 0, 0.85))
stand_in = bpy.context.object; stand_in.name = "ScaleStandIn"
stand_in["is_ground"] = True        # the render and export scripts ignore flagged objects when framing
                                    # cameras and when exporting; the stand-in still appears in the render
```

Keep it in the working scene and out of the export.

## Measuring what you are about to hand over

```python
def stats(o):
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    dims = [round(max(v[i] for v in bb) - min(v[i] for v in bb), 3) for i in range(3)]
    return tris, dims, bool(o.data.uv_layers), [m.name for m in o.data.materials if m]
```

The export verification prints the same numbers from the re-imported file; when the two disagree, the export lost something.
