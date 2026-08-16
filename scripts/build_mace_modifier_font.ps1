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
    $border = [System.Drawing.Color]::FromArgb(255, 34, 216, 224)
    $surface = [System.Drawing.Color]::FromArgb(255, 20, 54, 74)
    $shadow = [System.Drawing.Color]::FromArgb(255, 9, 25, 39)
    $letter = [System.Drawing.Color]::FromArgb(255, 235, 255, 255)
    for ($y = 2; $y -le 13; $y++) {
        for ($x = 2; $x -le 13; $x++) {
            $color = if ($y -ge 12) { $shadow } elseif ($x -in 2, 13 -or $y -eq 2) { $border } else { $surface }
            Set-KeyPixel $Bitmap ($CellX + $x) (80 + $y) $color
        }
    }
    for ($row = 0; $row -lt $Pattern.Count; $row++) {
        for ($column = 0; $column -lt $Pattern[$row].Length; $column++) {
            if ($Pattern[$row][$column] -eq "1") {
                Set-KeyPixel $Bitmap ($CellX + 3 + $column * 2) (84 + $row * 2) $letter 2
            }
        }
    }
}

$sheet = [System.Drawing.Bitmap]::new(128, 96, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
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
    } finally {
        $graphics.Dispose()
    }

    Draw-Keycap $sheet 0 @("10001", "10001", "10101", "10101", "01010")
    Draw-Keycap $sheet 16 @("01110", "10001", "11111", "10001", "10001")
    Draw-Keycap $sheet 32 @("01111", "10000", "01110", "00001", "11110")
    Draw-Keycap $sheet 48 @("11110", "10001", "10001", "10001", "11110")

    [System.IO.Directory]::CreateDirectory($outputParent) | Out-Null
    $sheet.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $sheet.Dispose()
}

Write-Output $outputPath

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
