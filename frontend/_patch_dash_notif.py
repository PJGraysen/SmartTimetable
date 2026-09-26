from pathlib import Path
p = Path("src/pages/inventory/Dashboard.tsx")
src = p.read_text(encoding="utf-8")

if "notifications" in src:
    print("[2] Dashboard already has notifications")
else:
    # Add notifications state + fetch
    src = src.replace(
        'const { data, err, loading } = useLoad<any>(() => (inventoryApi as any).dashboardV2());',
        '''const { data, err, loading } = useLoad<any>(() => (inventoryApi as any).dashboardV2());
  const notifications = useLoad<any>(() => (inventoryApi as any).notifications());''',
        1,
    )

    # Insert notifications block right after the stat row (before "Assets by Condition")
    anchor = '''      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <Card>
          <SectionTitle>Assets by Condition</SectionTitle>'''

    notif_block = '''      {notifications.data && notifications.data.count > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Card style={{ borderColor: "#F97316", background: "#fff7ed" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <SectionTitle>Notifications ({notifications.data.count})</SectionTitle>
            </div>
            {notifications.data.notifications.map((n: any, i: number) => (
              <div key={i} style={{
                padding: "0.5rem 0", borderBottom: "1px solid #fed7aa",
                display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center",
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "#9a3412" }}>{n.title}</div>
                  <div style={{ fontSize: "0.78rem", color: "#7c2d12" }}>{n.message}</div>
                </div>
                <button style={smallBtn} onClick={() => navigate(n.link)}>View</button>
              </div>
            ))}
          </Card>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <Card>
          <SectionTitle>Assets by Condition</SectionTitle>'''

    if anchor in src:
        src = src.replace(anchor, notif_block, 1)
        p.write_text(src, encoding="utf-8")
        print("[2] Dashboard notifications panel inserted")
    else:
        print("[2] WARN: anchor not found")
