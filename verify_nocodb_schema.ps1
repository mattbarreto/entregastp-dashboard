<#
.SYNOPSIS
    Verifica el esquema de NocoDB contra la estructura esperada por el dashboard.
    Usa la API REST de NocoDB (skill nocodb).

.DESCRIPTION
    Conecta a la instancia de NocoDB usando el API token y verifica:
    - Existencia de las 4 tablas: Cohortes, Actividades, Estudiantes, Entregas
    - Que las relaciones sean BelongsTo (FK directa) y no M2M
    - Que las columnas requeridas existan

.EXAMPLE
    $env:NOCODB_TOKEN = "tu-api-token"
    $env:NOCODB_URL = "https://nocodb.matiasbarreto.com"
    .\verify_nocodb_schema.ps1
#>

# === Configuración ===
$ErrorActionPreference = "Stop"

$NOCODB_URL = if ($env:NOCODB_URL) { $env:NOCODB_URL.TrimEnd('/') } else { "https://nocodb.matiasbarreto.com" }
$NOCODB_TOKEN = $env:NOCODB_TOKEN

if (-not $NOCODB_TOKEN) {
    Write-Host "ERROR: Variable NOCODB_TOKEN no configurada." -ForegroundColor Red
    Write-Host "  Usa: `$env:NOCODB_TOKEN = 'tu-api-token'" -ForegroundColor Yellow
    Write-Host "  Token name: entregastp-cli" -ForegroundColor Yellow
    exit 1
}

$headers = @{
    "xc-token" = $NOCODB_TOKEN
    "Content-Type" = "application/json"
}

# Tablas esperadas
$expectedTables = @("Cohortes", "Actividades", "Estudiantes", "Entregas")

# Relaciones esperadas: tabla_hija -> columna -> tabla_padre
$expectedRelations = @(
    @{ Child = "Estudiantes"; Column = "Cohorte"; Parent = "Cohortes" }
    @{ Child = "Actividades"; Column = "Cohorte"; Parent = "Cohortes" }
    @{ Child = "Entregas"; Column = "Estudiante"; Parent = "Estudiantes" }
    @{ Child = "Entregas"; Column = "Actividad"; Parent = "Actividades" }
)

# === Funciones ===
function Write-Status {
    param([string]$Symbol, [string]$Message, [string]$Color = "White")
    Write-Host "  $Symbol " -ForegroundColor $Color -NoNewline
    Write-Host $Message
}

function Invoke-NocoApi {
    param([string]$Path)
    try {
        $response = Invoke-RestMethod -Uri "$NOCODB_URL$Path" -Headers $headers -Method Get
        return $response
    }
    catch {
        Write-Host "ERROR en API: $Path" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        return $null
    }
}

# === Verificación ===
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  NocoDB Schema Verifier - entregastp-dashboard   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL: $NOCODB_URL" -ForegroundColor Gray
Write-Host ""

# 1. Listar bases
Write-Host "1. Buscando bases..." -ForegroundColor Yellow
$bases = Invoke-NocoApi "/api/v1/db/meta/projects/"
if (-not $bases) { exit 1 }

$baseList = $bases.list
if ($baseList.Count -eq 0) {
    Write-Host "  No se encontraron bases." -ForegroundColor Red
    exit 1
}

Write-Host "  Bases encontradas: $($baseList.Count)" -ForegroundColor Green
$baseId = $baseList[0].id
$baseName = $baseList[0].title
Write-Host "  Usando: '$baseName' (ID: $baseId)" -ForegroundColor Gray

# 2. Listar tablas
Write-Host ""
Write-Host "2. Verificando tablas..." -ForegroundColor Yellow
$tables = Invoke-NocoApi "/api/v1/db/meta/projects/$baseId/tables"
if (-not $tables) { exit 1 }

$tableList = $tables.list
$tableMap = @{}
$warnings = @()
$errors = @()

foreach ($table in $tableList) {
    $tableMap[$table.title] = $table
}

foreach ($expected in $expectedTables) {
    if ($tableMap.ContainsKey($expected)) {
        Write-Status "✓" "Tabla '$expected' encontrada (ID: $($tableMap[$expected].id))" "Green"
    } else {
        Write-Status "✗" "Tabla '$expected' NO encontrada" "Red"
        $errors += "Tabla '$expected' faltante"
    }
}

# 3. Verificar columnas y relaciones
Write-Host ""
Write-Host "3. Verificando relaciones..." -ForegroundColor Yellow

foreach ($rel in $expectedRelations) {
    $childTable = $tableMap[$rel.Child]
    if (-not $childTable) { continue }

    $fields = Invoke-NocoApi "/api/v1/db/meta/tables/$($childTable.id)/columns"
    if (-not $fields) { continue }

    $linkField = $fields.list | Where-Object { $_.title -eq $rel.Column -and $_.uidt -eq "LinkToAnotherRecord" }

    if ($linkField) {
        # Verificar si es BelongsTo o HasMany/ManyToMany
        $relType = $linkField.colOptions.type
        if ($relType -eq "bt") {
            Write-Status "✓" "$($rel.Child).$($rel.Column) → $($rel.Parent) (BelongsTo ✓)" "Green"
        } elseif ($relType -eq "mm") {
            Write-Status "⚠" "$($rel.Child).$($rel.Column) → $($rel.Parent) (ManyToMany ✗)" "Red"
            $errors += "Relación M2M detectada: $($rel.Child).$($rel.Column). Debe ser BelongsTo."
            $warnings += @"
  CORREGIR: En NocoDB, ir a tabla '$($rel.Child)', eliminar el campo '$($rel.Column)',
  recrearlo como LinkToAnotherRecord apuntando a '$($rel.Parent)' con
  'Permitir enlazar múltiples registros' DESACTIVADO.
"@
        } elseif ($relType -eq "hm") {
            Write-Status "⚠" "$($rel.Child).$($rel.Column) → $($rel.Parent) (HasMany ✗)" "Yellow"
            $warnings += "Relación HasMany en $($rel.Child).$($rel.Column). Debería ser BelongsTo."
        } else {
            Write-Status "?" "$($rel.Child).$($rel.Column) → $($rel.Parent) (Tipo: $relType)" "Yellow"
        }
    } else {
        # Buscar si existe como campo no-link (FK pura)
        $fkField = $fields.list | Where-Object { $_.title -eq $rel.Column }
        if ($fkField) {
            Write-Status "~" "$($rel.Child).$($rel.Column) existe pero no es LinkToAnotherRecord" "Yellow"
        } else {
            Write-Status "✗" "$($rel.Child).$($rel.Column) NO encontrado" "Red"
            $errors += "Campo '$($rel.Column)' faltante en tabla '$($rel.Child)'"
        }
    }
}

# 4. Resumen
Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "  RESULTADO: ✓ Esquema correcto" -ForegroundColor Green
} elseif ($errors.Count -gt 0) {
    Write-Host "  RESULTADO: ✗ Errores detectados ($($errors.Count))" -ForegroundColor Red
    foreach ($e in $errors) {
        Write-Host "    - $e" -ForegroundColor Red
    }
} else {
    Write-Host "  RESULTADO: ⚠ Advertencias ($($warnings.Count))" -ForegroundColor Yellow
}

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "  Instrucciones de corrección:" -ForegroundColor Yellow
    foreach ($w in $warnings) {
        Write-Host $w -ForegroundColor Yellow
    }
}
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
