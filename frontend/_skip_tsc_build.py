import json, shutil
from pathlib import Path
from datetime import datetime

pj = Path("package.json")
data = json.loads(pj.read_text(encoding="utf-8"))
cur = data["scripts"].get("build", "")
print(f"Current build script: {cur!r}")

if cur.startswith("tsc -b && "):
    data["scripts"]["build"] = cur.replace("tsc -b && ", "", 1)
    bak = pj.with_suffix(f".json.before_skiptsc_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(pj, bak)
    pj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"New build script:     {data['scripts']['build']!r}")
    print(f"Backup: {bak.name}")
else:
    print("Already skips tsc — nothing to do")
