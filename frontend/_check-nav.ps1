# nav-audit.ps1 — verify every "icon: X" reference in navigation.tsx
# is present in the lucide-react import block.
$ErrorActionPreference = 'Stop'
$navPath = Join-Path $PSScriptRoot 'src\navigation.tsx'
$txt = [IO.File]::ReadAllText($navPath)

$m = [regex]::Match($txt, '(?s)import\s*\{([^}]+)\}\s*from\s*"lucide-react"')
if (-not $m.Success) { Write-Host 'FAIL: lucide import block not found' -ForegroundColor Red; exit 1 }

# Extract imported identifiers, resolving `Home as HomeIcon` -> HomeIcon
$imports = @()
foreach ($piece in ($m.Groups[1].Value -split ',')) {
    $p = $piece.Trim()
    if (-not $p) { continue }
    if ($p -match '^(\w+)\s+as\s+(\w+)$') { $imports += $matches[2] }
    else { $imports += $p }
}

# Match only real usages: `icon: X` followed by `,` or `}` (array literals),
# NOT `icon: X<...>` (the NavItem type definition).
$used = [regex]::Matches($txt, 'icon:\s*([A-Z][A-Za-z0-9]*)\s*[,}]') |
    ForEach-Object { $_.Groups[1].Value } |
    Sort-Object -Unique

$missing = @()
foreach ($u in $used) { if ($imports -notcontains $u) { $missing += $u } }

Write-Host ('Icons referenced: ' + ($used -join ', '))
Write-Host ('Icons imported:   ' + ($imports -join ', '))
if ($missing.Count -gt 0) {
    Write-Host ('MISSING: ' + ($missing -join ', ')) -ForegroundColor Red
    exit 1
}
Write-Host 'OK — every referenced icon is imported.' -ForegroundColor Green