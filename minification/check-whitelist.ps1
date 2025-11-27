param(
    [string]$FilePath
)

# Charger la configuration de la whitelist
$whitelistPath = "minification\console-whitelist.json"
if (-not (Test-Path $whitelistPath)) {
    Write-Output "NOT_WHITELISTED"
    exit
}

try {
    $whitelist = Get-Content $whitelistPath | ConvertFrom-Json

    # Normaliser le chemin du fichier entrant (backslashes)
    $normalizedFilePath = $FilePath -replace '/', '\'

    # Si le chemin est relatif, le rendre absolu
    if (-not [System.IO.Path]::IsPathRooted($normalizedFilePath)) {
        $normalizedFilePath = [System.IO.Path]::GetFullPath($normalizedFilePath)
    }

    # Vérifier les fichiers exacts
    foreach ($file in $whitelist.whitelistedFiles) {
        $normalizedWhitelistFile = $file -replace '/', '\'

        # Si le fichier whitelist est relatif, le rendre absolu
        if (-not [System.IO.Path]::IsPathRooted($normalizedWhitelistFile)) {
            $normalizedWhitelistFile = [System.IO.Path]::GetFullPath($normalizedWhitelistFile)
        }

        # Comparaison insensible à la casse (Windows)
        if ($normalizedFilePath -eq $normalizedWhitelistFile) {
            Write-Output "WHITELISTED"
            exit
        }
    }

    # Vérifier les patterns
    foreach ($pattern in $whitelist.whitelistedPatterns) {
        $normalizedPattern = $pattern -replace '/', '\'
        $regexPattern = [regex]::Escape($normalizedPattern) -replace '\\\*\\\*', '.*' -replace '\\\*', '[^\\]*'
        if ($normalizedFilePath -match $regexPattern) {
            Write-Output "WHITELISTED"
            exit
        }
    }

    Write-Output "NOT_WHITELISTED"
} catch {
    Write-Output "NOT_WHITELISTED"
}