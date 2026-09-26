from pathlib import Path
p = Path("src/pages/inventory/Departments.tsx")
src = p.read_text(encoding="utf-8")
if "NewDepartmentModal" in src:
    print("[5] Departments.tsx already has + New")
else:
    src = src.replace(
        'import { inventoryApi } from "../../services/inventory";',
        'import { inventoryApi } from "../../services/inventory";\nimport { NewDepartmentModal } from "./Forms2";',
        1,
    )
    src = src.replace(
        'const [drawerId, setDrawerId] = useState<number | null>(null);',
        'const [drawerId, setDrawerId] = useState<number | null>(null);\n  const [showNew, setShowNew] = useState(false);',
        1,
    )
    src = src.replace(
        '''      actions={<button style={btnSecondary} onClick={exportCSV}>CSV</button>}''',
        '''      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Department</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }''',
        1,
    )
    src = src.replace(
        '      <DepartmentDrawer departmentId={drawerId} onClose={() => setDrawerId(null)} />',
        '      <DepartmentDrawer departmentId={drawerId} onClose={() => setDrawerId(null)} />\n      <NewDepartmentModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />',
        1,
    )
    if "btnPrimary" not in src:
        src = src.replace('btnSecondary', 'btnPrimary, btnSecondary', 1)
    p.write_text(src, encoding="utf-8")
    print("[5] Departments.tsx patched")
