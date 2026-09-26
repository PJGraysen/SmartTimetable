from pathlib import Path
import shutil
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
svc = Path("src/services/teachersAdmin.ts")
src = svc.read_text(encoding="utf-8")

OLD = 'export async function deleteTeacher(id: string): Promise<{ ok: boolean; deleted_assignments?: number }> {\n  const { data } = await http.delete(`/platform/admin/teachers/${id}/`);\n  return data || { ok: true };\n}'
NEW = 'export async function deleteTeacher(id: string): Promise<{ ok: boolean; deleted_assignments?: number }> {\n  // Dedicated endpoint avoids router <pk>/ shadowing\n  const { data } = await http.delete(`/platform/admin/teachers/${id}/delete/`);\n  return data || { ok: true };\n}'

if NEW in src:
    print("[1] deleteTeacher already repointed")
elif OLD in src:
    src = src.replace(OLD, NEW, 1)
    bak = svc.with_suffix(f".ts.before_delroute_{STAMP}")
    shutil.copy2(svc, bak)
    svc.write_text(src, encoding="utf-8")
    print(f"[1] deleteTeacher -> /delete/ endpoint  (backup {bak.name})")
else:
    print("[1] WARN: deleteTeacher pattern not found")
