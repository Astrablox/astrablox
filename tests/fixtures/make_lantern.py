"""Build the test scene used by tests/test_blender_tools.py: a lantern post (cylinder + cube head) with a
procedural stone material and a ground plane marked is_ground. The head carries the custom property
`piece` so layout_export.py has something to list.

Run: python tools/blender/blender.py tests/fixtures/make_lantern.py -- --out work/test.blend
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[argv.index("--out") + 1] if "--out" in argv else "work/test.blend")
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.12, depth=3.0, location=(0, 0, 1.5))
post = bpy.context.object
post.name = "LanternPost"
post["piece"] = "assets/world/lantern/LanternPost.glb"
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 3.2))
head = bpy.context.object
head.name = "LanternHead"
head["piece"] = "assets/world/lantern/LanternHead.glb"
m = bpy.data.materials.new("Stone")
m.use_nodes = True
nt = m.node_tree
bsdf = nt.nodes["Principled BSDF"]
n = nt.nodes.new("ShaderNodeTexNoise")
n.inputs["Scale"].default_value = 8
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.45, 0.4, 0.33, 1)
ramp.color_ramp.elements[1].color = (0.85, 0.8, 0.7, 1)
nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.8
for o in (post, head):
    o.data.materials.append(m)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
g = bpy.context.object
g.name = "Ground"
g["is_ground"] = True
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
