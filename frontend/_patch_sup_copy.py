from pathlib import Path
p = Path("src/pages/inventory/Suppliers.tsx")
src = p.read_text(encoding="utf-8")

if "copyToClipboard" in src:
    print("[2] Suppliers already patched")
else:
    src = src.replace(
        'downloadCSV, useLoad, Modal, inputStyle,',
        'downloadCSV, useLoad, Modal, inputStyle, copyToClipboard,',
        1,
    )

    OLD = '''          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {d.phone && (
              <a href={`tel:${d.phone}`} style={{ ...smallBtn, textDecoration: "none" }}
                 onClick={() => logContact("call")}>📞 Call</a>
            )}
            {d.email && (
              <a href={`mailto:${d.email}`} style={{ ...smallBtn, textDecoration: "none" }}
                 onClick={() => logContact("email")}>✉️ Email</a>
            )}
            {d.whatsapp && (
              <a href={`https://wa.me/${String(d.whatsapp).replace(/\\D/g, "")}`} target="_blank" rel="noreferrer"
                 style={{ ...smallBtn, textDecoration: "none" }}
                 onClick={() => logContact("whatsapp")}>💬 WhatsApp</a>
            )}
            <button style={smallBtn} onClick={() => onEdit(d)}>Edit</button>
          </div>'''

    NEW = '''          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {d.phone && (
              <>
                <a href={`tel:${d.phone}`} style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("call")}>📞 Call</a>
                <button style={smallBtn} title="Copy phone"
                        onClick={() => copyToClipboard(d.phone, "Phone")}>📋</button>
              </>
            )}
            {d.email && (
              <>
                <a href={`mailto:${d.email}`} style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("email")}>✉️ Email</a>
                <button style={smallBtn} title="Copy email"
                        onClick={() => copyToClipboard(d.email, "Email")}>📋</button>
              </>
            )}
            {d.whatsapp && (
              <>
                <a href={`https://wa.me/${String(d.whatsapp).replace(/\\D/g, "")}`} target="_blank" rel="noreferrer"
                   style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("whatsapp")}>💬 WhatsApp</a>
                <button style={smallBtn} title="Copy WhatsApp"
                        onClick={() => copyToClipboard(d.whatsapp, "WhatsApp")}>📋</button>
              </>
            )}
            <button style={smallBtn} onClick={() => onEdit(d)}>Edit</button>
          </div>'''

    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        p.write_text(src, encoding="utf-8")
        print("[2] Suppliers drawer updated with copy buttons")
    else:
        print("[2] WARN: contact block not matched — paste this output")
