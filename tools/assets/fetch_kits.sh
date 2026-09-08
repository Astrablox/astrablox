#!/usr/bin/env bash
# Reproduce the CC0 kit sources behind assets-library/: KayKit packs (GitHub, CC0) and the Quaternius
# fantasy packs (v-sekai-fabric/quaternius-stage mirror, USD, CC0), converted to GLB with headless Blender.
# Usage: fetch_kits.sh <work_dir> [blender_binary]
# Result: <work_dir>/kits_glb/<Pack>/*.glb (+ textures) ready for kit_catalog.py and upload.py --batch.
# Quaternius animations are not in the USD mirror; for animated monsters fetch the FBX packs from
# quaternius.com and convert them the same way.
set -euo pipefail
WORK="${1:?work dir}"; BLENDER="${2:-blender}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORK/kits" "$WORK/kits_glb"; cd "$WORK/kits"
for r in KayKit-Dungeon-Remastered-1.0 KayKit-Character-Pack-Adventures-1.0 KayKit-Character-Pack-Skeletons-1.0 KayKit-Medieval-Hexagon-Pack-1.0; do
  [ -d "$r-main" ] || { curl -sL "https://github.com/KayKit-Game-Assets/$r/archive/refs/heads/main.zip" -o "$r.zip" && unzip -q -o "$r.zip" && rm "$r.zip"; }
  ln -sfn "$PWD/$r-main" "$WORK/kits_glb/${r%-1.0}"
done
if [ ! -d quaternius ]; then
  git clone -q --filter=blob:none --sparse https://github.com/v-sekai-fabric/quaternius-stage.git quaternius
  (cd quaternius && git sparse-checkout set models/MedievalVillageMegaKit models/FantasyPropsMegaKit models/ModularDungeon models/MedievalDungeon models/UltimateFantasyRTS models/KnightCharacter models/RPGCharacters models/StylizedNatureMegaKit models/AnimatedMonster models/TexturedFantasyNature models/MedievalWeapons models/ModularCharacterOutfitsFantasy models/ModularMedievalBuildings models/CuteMonsters models/UltimateAnimatedAnimals models/EasyEnemy models/RPG models/3DCardKitFantasy)
fi
cd quaternius/models
for pack in *; do
  out="$WORK/kits_glb/Quaternius-$pack"; mkdir -p "$out"
  for u in "$pack"/*.usda; do
    n=$(basename "$u" .usda); [ -f "$out/$n.glb" ] && continue
    "$BLENDER" -b --python "$HERE/blender_convert.py" -- "$u" "$out/$n.glb" 2>&1 | grep RESULT || echo "FAIL $u"
  done
  cp "$pack"/*.png "$out/" 2>/dev/null || true
done
echo "kits ready in $WORK/kits_glb; next: python3 $HERE/kit_catalog.py $WORK/kits_glb $WORK/catalog"
