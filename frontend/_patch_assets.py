from pathlib import Path

p = Path("src/pages/inventory/Assets.tsx")
src = p.read_text(encoding="utf-8")

if "NewAssetModal" in src:
    print("[1] Assets.tsx already has + New Asset")
else:
    # Add import
    src = src.replace(
        'import {\n  TransferAssetModal, ScheduleMaintenanceModal, ChangeStatusModal,\n} from "./ActionModals";',
        'import {\n  TransferAssetModal, ScheduleMaintenanceModal, ChangeStatusModal,\n} from "./ActionModals";\nimport { NewAssetModal } from "./Forms";',
        1,
    )
    # Add showNew state
    src = src.replace(
        'const [showStatus, setShowStatus] = useState<number[] | null>(null);',
        'const [showStatus, setShowStatus] = useState<number[] | null>(null);\n  const [showNew, setShowNew] = useState(false);',
        1,
    )
    # Add + New Asset button in actions
    src = src.replace(
        '''      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }''',
        '''      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Asset</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }''',
        1,
    )
    # Add NewAssetModal at end (before closing PageShell tag)
    src = src.replace(
        '      <ChangeStatusModal\n        open={showStatus !== null}\n        onClose={() => setShowStatus(null)}\n        assetIds={showStatus || []}\n        onDone={reload}\n      />\n    </PageShell>',
        '      <ChangeStatusModal\n        open={showStatus !== null}\n        onClose={() => setShowStatus(null)}\n        assetIds={showStatus || []}\n        onDone={reload}\n      />\n      <NewAssetModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />\n    </PageShell>',
        1,
    )
    # Add btnPrimary to import if not there
    if "btnPrimary" not in src.split("} from")[0]:
        src = src.replace(
            'btnPrimary, btnSecondary',
            'btnPrimary, btnSecondary',
            1,
        )
    p.write_text(src, encoding="utf-8")
    print("[1] Assets.tsx patched with + New Asset button")
