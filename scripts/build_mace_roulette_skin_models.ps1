param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$packRoot = (Resolve-Path -LiteralPath $Root).Path
$maceItemPath = Join-Path $packRoot 'assets\minecraft\items\mace.json'
$maceItem = Get-Content -Raw -LiteralPath $maceItemPath | ConvertFrom-Json
$modelRoot = Join-Path $packRoot 'assets\bloodstone\models\item\mace_skins\roulette'
$itemPath = Join-Path $packRoot 'assets\bloodstone\items\mace_skins\roulette.json'
New-Item -ItemType Directory -Path $modelRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $itemPath) -Force | Out-Null

$previewEntries = [System.Collections.Generic.List[object]]::new()
foreach ($entry in $maceItem.model.entries) {
    $sourceModel = ([string]$entry.model.model) -replace '^minecraft:', ''
    if ($sourceModel -notmatch '^item/mace_skins/([a-z0-9_]+)$') {
        continue
    }
    $skinId = $Matches[1]
    $texturePath = Join-Path $packRoot "assets\minecraft\textures\item\mace_skins\$skinId.png"
    if (-not (Test-Path -LiteralPath $texturePath -PathType Leaf)) {
        continue
    }

    $model = [ordered]@{
        parent = 'minecraft:item/handheld_mace'
        textures = [ordered]@{
            layer0 = "minecraft:item/mace_skins/$skinId"
        }
    }
    $modelJson = ($model | ConvertTo-Json -Depth 5) + "`n"
    [System.IO.File]::WriteAllText(
        (Join-Path $modelRoot "$skinId.json"),
        $modelJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    $previewEntries.Add([ordered]@{
        threshold = $entry.threshold
        model = [ordered]@{
            type = 'minecraft:model'
            model = "bloodstone:item/mace_skins/roulette/$skinId"
        }
    })
}

$previewItem = [ordered]@{
    model = [ordered]@{
        type = 'minecraft:range_dispatch'
        property = 'minecraft:custom_model_data'
        entries = $previewEntries
        fallback = [ordered]@{
            type = 'minecraft:model'
            model = 'minecraft:item/mace'
        }
    }
}
$itemJson = ($previewItem | ConvertTo-Json -Depth 10) + "`n"
[System.IO.File]::WriteAllText($itemPath, $itemJson, [System.Text.UTF8Encoding]::new($false))

Write-Output "Generated $($previewEntries.Count) normalized Mace Roulette skin models."
