#!/usr/bin/env python3
"""Build a catalog of CC0 kit assets (glb/gltf) for the AstraBlox asset library.

Usage: kit_catalog.py <kits_root> <out_dir>
Writes out_dir/catalog.json, out_dir/INDEX.md and out_dir/thumbs/<pack>/<name>.png (software-rendered).
"""
import sys, os, json, glob, math, re, collections
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(OUT, 'thumbs'), exist_ok=True)

TAG_WORDS = {
    'wall':'structure','floor':'structure','stairs':'structure','pillar':'structure','column':'structure','arch':'structure','door':'structure','gate':'structure','window':'structure','roof':'structure','tower':'structure','bridge':'structure','fence':'structure','corner':'structure','tile':'structure','ceiling':'structure','scaffold':'structure',
    'torch':'light','candle':'light','lantern':'light','brazier':'light','chandelier':'light','lamp':'light','fire':'light',
    'banner':'decor','flag':'decor','carpet':'decor','rug':'decor','painting':'decor','shield':'decor','tapestry':'decor','statue':'decor','skull':'decor','bones':'decor',
    'table':'furniture','chair':'furniture','bed':'furniture','shelf':'furniture','bookcase':'furniture','stool':'furniture','bench':'furniture','throne':'furniture','desk':'furniture','cabinet':'furniture',
    'barrel':'prop','crate':'prop','box':'prop','chest':'prop','trunk':'prop','bottle':'prop','bucket':'prop','pot':'prop','plate':'prop','mug':'prop','coin':'prop','keyring':'prop','key':'prop','book':'prop','sack':'prop','cage':'prop','anvil':'prop','cauldron':'prop','wheel':'prop','ladder':'prop','rope':'prop',
    'sword':'weapon','axe':'weapon','bow':'weapon','crossbow':'weapon','staff':'weapon','dagger':'weapon','spear':'weapon','hammer':'weapon','mace':'weapon','arrow':'weapon','quiver':'weapon','spellbook':'weapon','wand':'weapon',
    'spikes':'hazard','trap':'hazard','grate':'hazard','coffin':'hazard',
    'tree':'nature','rock':'nature','bush':'nature','grass':'nature','stone':'nature','hex':'terrain','river':'terrain','coast':'terrain','road':'terrain','water':'terrain','mountain':'terrain','forest':'terrain','hill':'terrain','sand':'terrain',
    'knight':'character','rogue':'character','mage':'character','barbarian':'character','skeleton':'character','minion':'character','warrior':'character','archer':'character',
    'castle':'building','house':'building','mill':'building','church':'building','tavern':'building','market':'building','barracks':'building','mine':'building','farm':'building','watchtower':'building','well':'building','lumbermill':'building','blacksmith':'building',
}

def tags_for(name):
    low = name.lower()
    tags = set()
    for w, t in TAG_WORDS.items():
        if re.search(r'(^|[_\-\s])' + w, low):
            tags.add(t)
    return sorted(tags) or ['misc']

def render_thumb(scene, path, size=192):
    """Flat-shaded software render, 3/4 view, painter's algorithm. Good enough to recognise an asset."""
    try:
        mesh = scene.dump(concatenate=True) if isinstance(scene, trimesh.Scene) else scene
    except Exception:
        return False
    if mesh.faces.shape[0] == 0:
        return False
    v = mesh.vertices - mesh.bounding_box.centroid
    scale = 1.0 / max(mesh.extents.max(), 1e-6)
    v = v * scale
    # rotate: yaw 35deg, pitch 25deg (Y up)
    yaw, pitch = math.radians(35), math.radians(-25)
    Ry = np.array([[math.cos(yaw),0,math.sin(yaw)],[0,1,0],[-math.sin(yaw),0,math.cos(yaw)]])
    Rx = np.array([[1,0,0],[0,math.cos(pitch),-math.sin(pitch)],[0,math.sin(pitch),math.cos(pitch)]])
    v = v @ Ry.T @ Rx.T
    f = mesh.faces
    # face colours: vertex colours or material base colour
    base = np.array([180,170,160])
    try:
        vc = mesh.visual.to_color().vertex_colors[:, :3] if mesh.visual.kind != 'face' else None
        fc = vc[f].mean(axis=1) if vc is not None else np.tile(base, (len(f),1))
    except Exception:
        fc = np.tile(base, (len(f),1))
    n = mesh.face_normals @ Ry.T @ Rx.T
    light = np.array([0.4, 0.8, 0.45]); light /= np.linalg.norm(light)
    shade = np.clip(n @ light, 0, 1) * 0.65 + 0.35
    depth = v[f][:, :, 2].mean(axis=1)
    order = np.argsort(depth)  # far first (z towards viewer positive after rotation? use ascending)
    img = Image.new('RGB', (size, size), (28, 30, 36))
    d = ImageDraw.Draw(img)
    pad = size * 0.08
    def P(p):
        return (pad + (p[0] + 0.5) * (size - 2*pad), size - (pad + (p[1] + 0.5) * (size - 2*pad)))
    limit = 60000
    if len(order) > limit:
        order = order[np.linspace(0, len(order)-1, limit).astype(int)]
    for i in order:
        tri = v[f[i]]
        col = tuple(int(c) for c in (fc[i] * shade[i]))
        d.polygon([P(tri[0]), P(tri[1]), P(tri[2])], fill=col)
    img.save(path)
    return True

catalog = []
packs = sorted([p for p in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, p))])
for pack in packs:
    pdir = os.path.join(ROOT, pack)
    files = sorted(glob.glob(pdir + '/**/*.glb', recursive=True) + glob.glob(pdir + '/**/*.gltf', recursive=True))
    # prefer glb when both exist with same stem
    stems = {}
    for fp in files:
        stem = re.sub(r'\.gltf$', '', os.path.splitext(os.path.basename(fp))[0])
        if stem not in stems or fp.endswith('.glb'):
            stems[stem] = fp
    lic = ''
    for lf in glob.glob(pdir + '/**/LICENSE*', recursive=True):
        lic = open(lf, errors='ignore').read()[:400]
        break
    os.makedirs(os.path.join(OUT, 'thumbs', pack), exist_ok=True)
    print(pack, len(stems), 'assets', file=sys.stderr)
    for stem, fp in sorted(stems.items()):
        try:
            sc = trimesh.load(fp, force='scene')
        except Exception as e:
            print('  FAIL', fp, e, file=sys.stderr); continue
        tris = int(sum(g.faces.shape[0] for g in sc.geometry.values()))
        ext = [round(float(x), 2) for x in sc.extents] if len(sc.geometry) else [0,0,0]
        anims = []
        try:
            import pygltflib
            g = pygltflib.GLTF2().load(fp)
            anims = [a.name or f'anim{i}' for i, a in enumerate(g.animations)]
            skinned = len(g.skins) > 0
            nmat = len(g.materials); nimg = len(g.images)
        except Exception:
            skinned = False; nmat = nimg = -1
        thumb = os.path.join('thumbs', pack, stem + '.png')
        ok = render_thumb(sc, os.path.join(OUT, thumb))
        catalog.append({
            'pack': pack, 'name': stem, 'file': os.path.relpath(fp, ROOT), 'format': os.path.splitext(fp)[1][1:],
            'triangles': tris, 'extents': ext, 'animations': anims, 'skinned': skinned,
            'materials': nmat, 'images': nimg, 'tags': tags_for(stem), 'thumb': thumb if ok else None,
            'license': 'CC0-1.0', 'roblox_ok': tris <= 20000,
        })

json.dump(catalog, open(os.path.join(OUT, 'catalog.json'), 'w'), indent=1)
# INDEX.md grouped by pack and tag
lines = ['# CC0 kit catalog', '', f'{len(catalog)} assets from {len(packs)} packs. All CC0. Triangle counts are per asset; Roblox accepts up to 20 000 per MeshPart.', '']
by_pack = collections.defaultdict(list)
for a in catalog: by_pack[a['pack']].append(a)
for pack, items in by_pack.items():
    lines.append(f'## {pack} ({len(items)})')
    by_tag = collections.defaultdict(list)
    for a in items:
        by_tag[a['tags'][0]].append(a)
    for tag, its in sorted(by_tag.items()):
        names = ', '.join(f"{a['name']} ({a['triangles']}t{', anim' if a['animations'] else ''})" for a in its)
        lines.append(f'- **{tag}**: {names}')
    lines.append('')
open(os.path.join(OUT, 'INDEX.md'), 'w').write('\n'.join(lines))
print(json.dumps({'assets': len(catalog), 'packs': len(packs), 'with_anims': sum(1 for a in catalog if a['animations']), 'max_tris': max(a['triangles'] for a in catalog)}))
