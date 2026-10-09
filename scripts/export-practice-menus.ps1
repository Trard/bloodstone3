param([Parameter(Mandatory=$true)][string]$SessionId, [switch]$Refresh, [switch]$V3)
$ErrorActionPreference = 'Stop'
$packRoot = Split-Path $PSScriptRoot -Parent
$headers = @{Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$SessionId; 'MCP-Protocol-Version'='2025-03-26'}
function Invoke-BB([string]$Name, [hashtable]$Arguments) {
    $body = @{jsonrpc='2.0';id=70;method='tools/call';params=@{name=$Name;arguments=$Arguments}} | ConvertTo-Json -Depth 12 -Compress
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/bb-mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body $body
    if ($response.error -or $response.result.isError) {throw ($response | ConvertTo-Json -Depth 12)}
    return $response.result
}
$filter = if ($V3) {"t.name.startsWith('practice_v3_')"} else {"t.name.startsWith('practice_') && !t.name.startsWith('practice_icon_') && !t.name.startsWith('practice_v3_')"}
$result = Invoke-BB 'risky_eval' @{code="Texture.all.filter(t=>$filter).map(t=>({name:t.name,data:t.getDataURL()}))"}
$textures = $result.content[0].text | ConvertFrom-Json
foreach ($texture in $textures) {
    if ($texture.name -notmatch '^practice_(icon_)?[a-z0-9_]+$') {throw 'Unexpected texture name'}
    $icon = $texture.name.StartsWith('practice_icon_')
    $folder = if ($V3) {'assets/minecraft/textures/gui/practice_v3'} elseif ($icon) {'assets/minecraft/textures/item/practice/menu'} else {'assets/minecraft/textures/gui/practice'}
    $name = if ($V3) {$texture.name.Substring(12)} elseif ($icon) {$texture.name.Substring(14)} else {$texture.name.Substring(9)}
    $directory = Join-Path $packRoot $folder
    [void][System.IO.Directory]::CreateDirectory($directory)
    $destination = Join-Path $directory ($name + '.png')
    if ((Test-Path -LiteralPath $destination) -and -not $Refresh) {throw "Export already exists: $destination"}
    if ($texture.data -notmatch '^data:image/png;base64,') {throw 'Expected a PNG from Blockbench'}
    [System.IO.File]::WriteAllBytes($destination,[Convert]::FromBase64String($texture.data.Split(',')[1]))
}
[void](Invoke-BB 'list_export_formats' @{})
$sourceDir = Join-Path $packRoot 'sources/practice-menus'
[void][System.IO.Directory]::CreateDirectory($sourceDir)
$projectPath = Join-Path $sourceDir $(if ($V3) {'practice-menus-v3.bbmodel'} else {'practice-menus.bbmodel'})
[void](Invoke-BB 'export_model' @{codec_id='project';path=$projectPath;max_content_length=0;overwrite=[bool]$Refresh})
$capture = Invoke-BB 'capture_app_screenshot' @{max_size=1400;format='png'}
$captureImage = $capture.content | Where-Object {$_.type -eq 'image'} | Select-Object -First 1
if ($captureImage) {
    $previewName = if ($V3) {'blockbench-preview-v3.png'} else {'blockbench-preview.png'}
    [System.IO.File]::WriteAllBytes((Join-Path $sourceDir $previewName),[Convert]::FromBase64String($captureImage.data))
}
Write-Output "Exported $($textures.Count) native Blockbench textures and the editable project to $sourceDir"
