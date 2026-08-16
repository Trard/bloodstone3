param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$packRoot = (Resolve-Path -LiteralPath $Root).Path
$maceItemPath = Join-Path $packRoot 'assets\minecraft\items\mace.json'
$maceItem = Get-Content -Raw -LiteralPath $maceItemPath | ConvertFrom-Json
$modelRoot = Join-Path $packRoot 'assets\bloodstone\models\item\mace_skins\roulette'
$textureRoot = Join-Path $packRoot 'assets\bloodstone\textures\item\mace_skins\roulette'
$itemPath = Join-Path $packRoot 'assets\bloodstone\items\mace_skins\roulette.json'
New-Item -ItemType Directory -Path $modelRoot -Force | Out-Null
New-Item -ItemType Directory -Path $textureRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $itemPath) -Force | Out-Null

Add-Type -AssemblyName System.Drawing

function Write-NormalizedTexture {
    param(
        [string]$Source,
        [string]$Destination
    )

    $sourceBitmap = [System.Drawing.Bitmap]::new($Source)
    try {
        $frameSize = [Math]::Min($sourceBitmap.Width, $sourceBitmap.Height)
        if ($sourceBitmap.Width % $frameSize -ne 0 -or $sourceBitmap.Height % $frameSize -ne 0) {
            throw "Texture does not contain a regular frame grid: $Source"
        }
        $columns = $sourceBitmap.Width / $frameSize
        $rows = $sourceBitmap.Height / $frameSize
        $minX = $frameSize
        $minY = $frameSize
        $maxX = -1
        $maxY = -1

        for ($row = 0; $row -lt $rows; $row++) {
            for ($column = 0; $column -lt $columns; $column++) {
                for ($y = 0; $y -lt $frameSize; $y++) {
                    for ($x = 0; $x -lt $frameSize; $x++) {
                        $pixel = $sourceBitmap.GetPixel($column * $frameSize + $x, $row * $frameSize + $y)
                        if ($pixel.A -eq 0) {
                            continue
                        }
                        if ($x -lt $minX) { $minX = $x }
                        if ($x -gt $maxX) { $maxX = $x }
                        if ($y -lt $minY) { $minY = $y }
                        if ($y -gt $maxY) { $maxY = $y }
                    }
                }
            }
        }
        if ($maxX -lt $minX -or $maxY -lt $minY) {
            throw "Texture is fully transparent: $Source"
        }

        $contentWidth = $maxX - $minX + 1
        $contentHeight = $maxY - $minY + 1
        $scale = [Math]::Min(16.0 / $contentWidth, 16.0 / $contentHeight)
        $targetWidth = [Math]::Max(1, [Math]::Round($contentWidth * $scale))
        $targetHeight = [Math]::Max(1, [Math]::Round($contentHeight * $scale))
        $offsetX = [Math]::Floor((16 - $targetWidth) / 2.0)
        $offsetY = [Math]::Floor((16 - $targetHeight) / 2.0)
        $targetBitmap = [System.Drawing.Bitmap]::new($columns * 16, $rows * 16)
        try {
            for ($row = 0; $row -lt $rows; $row++) {
                for ($column = 0; $column -lt $columns; $column++) {
                    for ($y = 0; $y -lt $targetHeight; $y++) {
                        $sourceY = $minY + [Math]::Min(
                            $contentHeight - 1,
                            [Math]::Floor($y * $contentHeight / $targetHeight)
                        )
                        for ($x = 0; $x -lt $targetWidth; $x++) {
                            $sourceX = $minX + [Math]::Min(
                                $contentWidth - 1,
                                [Math]::Floor($x * $contentWidth / $targetWidth)
                            )
                            $pixel = $sourceBitmap.GetPixel(
                                $column * $frameSize + $sourceX,
                                $row * $frameSize + $sourceY
                            )
                            $targetBitmap.SetPixel(
                                $column * 16 + $offsetX + $x,
                                $row * 16 + $offsetY + $y,
                                $pixel
                            )
                        }
                    }
                }
            }
            $targetBitmap.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $targetBitmap.Dispose()
        }
    } finally {
        $sourceBitmap.Dispose()
    }
}

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
    $previewTexturePath = Join-Path $textureRoot "$skinId.png"
    Write-NormalizedTexture -Source $texturePath -Destination $previewTexturePath
    $textureMetadataPath = "$texturePath.mcmeta"
    if (Test-Path -LiteralPath $textureMetadataPath -PathType Leaf) {
        Copy-Item -LiteralPath $textureMetadataPath -Destination "$previewTexturePath.mcmeta" -Force
    }

    $model = [ordered]@{
        parent = 'minecraft:item/handheld_mace'
        textures = [ordered]@{
            layer0 = "bloodstone:item/mace_skins/roulette/$skinId"
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
