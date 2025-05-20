# Inicializace proměnné pro nasbíraný obsah
$allContent = ""

# Definice povolených přípon souborů (povolené pouze textové soubory relevantní pro dokumentaci a kód)
$allowedExtensions = @(
    ".yaml", ".yml", ".py", ".mdx", ".md", ".toml", ".txt"
)

# Prohledáme rekurzivně aktuální adresář, vynecháme soubor allcode.txt, skryté soubory
# a soubory nacházející se v adresářích .venv a __pycache__
Get-ChildItem -Path "." -Recurse -File -Exclude "allcode.txt" |
Where-Object {
    $_.Attributes -notmatch "Hidden" -and
    $_.FullName -notmatch '\\.venv\\' -and
    $_.FullName -notmatch '\\__pycache__\\' -and
    $allowedExtensions -contains $_.Extension.ToLower()
} |
ForEach-Object {
    $path = $_.FullName
    $content = Get-Content $path -Raw -ErrorAction SilentlyContinue

    $allContent += "File: $path`n"
    $allContent += $content + "`n"
    $allContent += "----------------------------------`n"
}

# Jednorázový zápis všech dat do souboru allcode.txt
Set-Content -Path "allcode.txt" -Value $allContent
