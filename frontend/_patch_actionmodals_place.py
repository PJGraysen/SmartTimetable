from pathlib import Path
p = Path("src/pages/inventory/ActionModals.tsx")
src = p.read_text(encoding="utf-8")

if 'placement="right"' in src:
    print("[2] ActionModals already anchored right")
else:
    count = 0
    new = src
    # Target every <Modal ... with title= and add placement right before title
    import re
    new, count = re.subn(
        r'<Modal open=\{open\} onClose=\{onClose\} title=',
        '<Modal open={open} onClose={onClose} placement="right" title=',
        new,
    )
    p.write_text(new, encoding="utf-8")
    print(f"[2] {count} modals anchored right")
