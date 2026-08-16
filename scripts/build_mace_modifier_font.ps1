param(
    [Parameter(Mandatory = $true)]
    [string]$ModifierTextureRoot,
    [Parameter(Mandatory = $true)]
    [string]$LightMaceTexture,
    [Parameter(Mandatory = $true)]
    [string]$FrozenHeartTexture,
    [string]$Output = "assets/bloodstone/textures/font/mace_modifiers.png"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$textureRoot = (Resolve-Path -LiteralPath $ModifierTextureRoot).Path
$lightMace = (Resolve-Path -LiteralPath $LightMaceTexture).Path
$frozenHeart = (Resolve-Path -LiteralPath $FrozenHeartTexture).Path
$outputPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Output))
$outputParent = Split-Path -Parent $outputPath
$frozenHeartOutput = Join-Path $outputParent "mace_freeze.png"

$icons = @(
    "umbrella.png",
    "levitation_burst.png",
    "donut_map.png",
    "square_map.png",
    "pillars.png",
    "mace_drop.png",
    "blocks.png",
    "cobwebs.png",
    "spikes.png",
    "minefield.png",
    "sweeper.png",
    "double_mace.png",
    "triple_mace.png",
    "quadruple_mace.png",
    "quadruple_mace.png",
    "quadruple_mace.png",
    "quadruple_mace.png",
    "quadruple_mace.png",
    "quadruple_mace.png",
    "big_mace.png",
    "tiny_mace.png",
    $lightMace,
    "random_size.png",
    "slow_time.png",
    "rewind.png",
    "no_jumping.png",
    "miss_equals_die.png",
    "shockwave_mace.png",
    "wind_burst.png",
    "fragile_floor.png",
    "icy_floor.png",
    "magnetic_burst.png",
    "freeze_burst.png",
    "punch_equals_freeze.png",
    "honey_burst.png",
    "explosive_burst.png",
    "steal_the_totem.png",
    "wind_storm.png",
    "lunge.png",
    "elytra_launch.png"
)

if ($icons.Count -ne 40) {
    throw "Expected 40 modifier icons, got $($icons.Count)"
}

$resolvedIcons = foreach ($icon in $icons) {
    $candidate = if ([System.IO.Path]::IsPathRooted($icon)) { $icon } else { Join-Path $textureRoot $icon }
    (Resolve-Path -LiteralPath $candidate).Path
}

function Set-KeyPixel {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [int]$X,
        [int]$Y,
        [System.Drawing.Color]$Color,
        [int]$Scale = 1
    )
    for ($offsetY = 0; $offsetY -lt $Scale; $offsetY++) {
        for ($offsetX = 0; $offsetX -lt $Scale; $offsetX++) {
            $Bitmap.SetPixel($X + $offsetX, $Y + $offsetY, $Color)
        }
    }
}

function Draw-Keycap {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [int]$CellX,
        [string[]]$Pattern
    )
    $border = [System.Drawing.Color]::FromArgb(255, 142, 164, 174)
    $surface = [System.Drawing.Color]::FromArgb(255, 47, 59, 66)
    $shadow = [System.Drawing.Color]::FromArgb(255, 15, 19, 23)
    $letter = [System.Drawing.Color]::FromArgb(255, 235, 255, 255)
    for ($y = 0; $y -le 10; $y++) {
        for ($x = 0; $x -le 10; $x++) {
            $color = if ($y -ge 9 -or $x -eq 10) {
                $shadow
            } elseif ($x -eq 0 -or $y -eq 0) {
                $border
            } else {
                $surface
            }
            Set-KeyPixel $Bitmap ($CellX + $x) $y $color
        }
    }
    for ($row = 0; $row -lt $Pattern.Count; $row++) {
        for ($column = 0; $column -lt $Pattern[$row].Length; $column++) {
            if ($Pattern[$row][$column] -eq "1") {
                Set-KeyPixel $Bitmap ($CellX + 3 + $column) (1 + $row) $letter
            }
        }
    }
}

function Draw-RewindIcon {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [int]$CellX,
        [int]$CellY
    )
    $transparent = [System.Drawing.Color]::Transparent
    $outline = [System.Drawing.Color]::FromArgb(255, 4, 28, 43)
    $cyan = [System.Drawing.Color]::FromArgb(255, 19, 228, 216)
    $highlight = [System.Drawing.Color]::FromArgb(255, 181, 255, 255)
    $shadow = [System.Drawing.Color]::FromArgb(255, 5, 120, 145)
    for ($y = 0; $y -lt 16; $y++) {
        for ($x = 0; $x -lt 16; $x++) {
            $Bitmap.SetPixel($CellX + $x, $CellY + $y, $transparent)
        }
    }
    $pixels = @{}
    for ($y = 2; $y -le 13; $y++) {
        $halfWidth = [math]::Min($y - 2, 13 - $y)
        foreach ($rightEdge in 7, 14) {
            for ($x = $rightEdge - $halfWidth; $x -le $rightEdge; $x++) {
                $pixels["$x,$y"] = $true
            }
        }
    }
    foreach ($key in $pixels.Keys) {
        $parts = $key.Split(',')
        $x = [int]$parts[0]
        $y = [int]$parts[1]
        foreach ($offsetY in -1..1) {
            foreach ($offsetX in -1..1) {
                $targetX = $x + $offsetX
                $targetY = $y + $offsetY
                if ($targetX -in 0..15 -and $targetY -in 0..15) {
                    $Bitmap.SetPixel($CellX + $targetX, $CellY + $targetY, $outline)
                }
            }
        }
    }
    foreach ($key in $pixels.Keys) {
        $parts = $key.Split(',')
        $x = [int]$parts[0]
        $y = [int]$parts[1]
        $color = if ($y -le 4) { $highlight } elseif ($y -ge 11) { $shadow } else { $cyan }
        $Bitmap.SetPixel($CellX + $x, $CellY + $y, $color)
    }
}

$sheet = [System.Drawing.Bitmap]::new(128, 80, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
try {
    $graphics = [System.Drawing.Graphics]::FromImage($sheet)
    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
        for ($index = 0; $index -lt $resolvedIcons.Count; $index++) {
            $image = [System.Drawing.Bitmap]::FromFile($resolvedIcons[$index])
            try {
                $destination = [System.Drawing.Rectangle]::new(($index % 8) * 16, [math]::Floor($index / 8) * 16, 16, 16)
                $graphics.DrawImage($image, $destination, 0, 0, $image.Width, $image.Height, [System.Drawing.GraphicsUnit]::Pixel)
            } finally {
                $image.Dispose()
            }
        }
        Draw-RewindIcon $sheet 0 48
    } finally {
        $graphics.Dispose()
    }

    [System.IO.Directory]::CreateDirectory($outputParent) | Out-Null
    $sheet.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $sheet.Dispose()
}

Write-Output $outputPath

$keyOutputPath = Join-Path $outputParent "mace_keys.png"
$keySheet = [System.Drawing.Bitmap]::new(48, 12, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
try {
    Draw-Keycap $keySheet 0 @("10001", "10001", "10001", "10101", "10101", "11011", "10001")
    Draw-Keycap $keySheet 12 @("01110", "10001", "10001", "11111", "10001", "10001", "10001")
    Draw-Keycap $keySheet 24 @("01111", "10000", "10000", "01110", "00001", "00001", "11110")
    Draw-Keycap $keySheet 36 @("11110", "10001", "10001", "10001", "10001", "10001", "11110")
    $keySheet.Save($keyOutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $keySheet.Dispose()
}

Write-Output $keyOutputPath

$heartSource = [System.Drawing.Bitmap]::FromFile($frozenHeart)
try {
    $heartOutput = [System.Drawing.Bitmap]::new(16, 16, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $heartGraphics = [System.Drawing.Graphics]::FromImage($heartOutput)
        try {
            $heartGraphics.Clear([System.Drawing.Color]::Transparent)
            $heartGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
            $heartGraphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
            $heartGraphics.DrawImage(
                $heartSource,
                [System.Drawing.Rectangle]::new(0, 0, 16, 16),
                0,
                0,
                $heartSource.Width,
                $heartSource.Height,
                [System.Drawing.GraphicsUnit]::Pixel
            )
        } finally {
            $heartGraphics.Dispose()
        }
        $heartOutput.Save($frozenHeartOutput, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $heartOutput.Dispose()
    }
} finally {
    $heartSource.Dispose()
}

Write-Output $frozenHeartOutput
