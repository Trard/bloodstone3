param(
    [Parameter(Mandatory=$true)][string]$SessionId,
    [ValidateSet('Menus','Biomes','RefineBiomes','EnlargeBiomes','CubeBiomes','Capture')][string]$Task='Menus',
    [switch]$Refresh,
    [string]$ClientJar
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$headers=@{Accept='application/json, text/event-stream';'Mcp-Session-Id'=$SessionId;'MCP-Protocol-Version'='2025-03-26'}
function Invoke-BB([string]$Name,[hashtable]$Arguments) {
    $body=@{jsonrpc='2.0';id=210;method='tools/call';params=@{name=$Name;arguments=$Arguments}}|ConvertTo-Json -Depth 20 -Compress
    $response=Invoke-RestMethod -Uri 'http://127.0.0.1:3000/bb-mcp' -Method Post -ContentType 'application/json; charset=utf-8' -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if($response.error -or $response.result.isError){throw ($response|ConvertTo-Json -Depth 20)}
    return $response.result
}
function Eval-BB([string]$Code) {
    $result=Invoke-BB 'risky_eval' @{code=$Code}
    return ($result.content[0].text|ConvertFrom-Json)
}
function Export-Project([string]$Path) {
    if((Test-Path -LiteralPath $Path) -and -not $Refresh){throw "Project already exists: $Path"}
    $data=Eval-BB 'Codecs.project.compile()'
    if($data -isnot [string]){$data=$data|ConvertTo-Json -Depth 100}
    [System.IO.File]::WriteAllText($Path,$data,[System.Text.UTF8Encoding]::new($false))
}
if($Task -eq 'Menus') {
    $state=Eval-BB '({name:Project?.name,textures:Texture.all.map(t=>t.name)})'
    if($state.name -and $state.name -ne 'Bloodstone practice menus v4'){throw 'Select an empty Blockbench tab; another project is active.'}
    if(-not $state.name) {
        $model=Get-Content -LiteralPath (Join-Path $root 'sources/practice-menus/practice-menus-v3.bbmodel') -Raw
        $model=$model.Replace('/','\u002f')
        [void](Eval-BB "(()=>{Codecs.project.load($model,{path:'practice-menus-v4.bbmodel',no_file:true});Project.name='Bloodstone practice menus v4';return true})()")
    }
    $font=Get-Content -LiteralPath (Join-Path $root 'sources/practice-menus/title-glyphs-v4.json') -Raw
    $numberFont=Get-Content -LiteralPath (Join-Path $root 'sources/practice-menus/title-glyphs.json') -Raw
    $layout=Get-Content -LiteralPath (Join-Path $root 'sources/practice-menus/v4-layouts.json') -Raw
    $script=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'practice-menus-v4-blockbench.js') -Raw
    $script=[regex]::Replace($script,'(?m)^\s*//[^\r\n]*','')
    Eval-BB "($script)($font,$layout,$numberFont)"
    $textures=Eval-BB "Texture.all.filter(t=>t.name.startsWith('practice_v4_')).map(t=>({name:t.name,data:t.getDataURL()}))"
    $folder=Join-Path $root 'assets/minecraft/textures/gui/practice_v4'
    [void][System.IO.Directory]::CreateDirectory($folder)
    foreach($texture in $textures){
        if($texture.name -notmatch '^practice_v4_[a-z0-9_]+$'){throw 'Invalid texture name'}
        $path=Join-Path $folder ($texture.name.Substring(12)+'.png')
        if((Test-Path -LiteralPath $path) -and -not $Refresh){throw "Texture already exists: $path"}
        [System.IO.File]::WriteAllBytes($path,[Convert]::FromBase64String($texture.data.Split(',')[1]))
    }
    Export-Project (Join-Path $root 'sources/practice-menus/practice-menus-v4.bbmodel')
    Write-Output "Exported $($textures.Count) Blockbench menu textures."
}
if($Task -eq 'CubeBiomes') {
    if(-not (Test-Path -LiteralPath $ClientJar)){throw 'Vanilla texture references required'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[System.IO.Compression.ZipFile]::OpenRead($ClientJar)
    $images=@{}
    try {
        foreach($name in @('dirt','grass_block_top','grass_block_side','grass_block_side_overlay','sand','red_sand','orange_terracotta','white_terracotta','terracotta','brown_terracotta','mycelium_top','mycelium_side','snow','grass_block_snow','bedrock')) {
            $entry=$archive.GetEntry("assets/minecraft/textures/block/$name.png")
            if(-not $entry){throw "Missing texture $name"}
            $stream=$entry.Open();$memory=[IO.MemoryStream]::new()
            try {$stream.CopyTo($memory);$images[$name]='data:image/png;base64,'+[Convert]::ToBase64String($memory.ToArray())}
            finally {$stream.Dispose();$memory.Dispose()}
        }
    } finally {$archive.Dispose()}
    $json=($images|ConvertTo-Json -Compress).Replace('/','\u002f')
    $script=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'practice-biome-cubes-blockbench.js') -Raw
    $directory=Join-Path $root 'sources/practice-biomes'
    [void](Invoke-BB 'create_offscreen_view' @{id='biome-cube-proof';width=320;height=320;antialias=$false;copy_view='none'})
    try {
        foreach($biome in @('plains','desert','badlands','mushroom','snowy_fields','hub')) {
            $path=Join-Path $directory "$biome-cube-v42.bbmodel"
            if((Test-Path -LiteralPath $path) -and -not $Refresh){throw "Cube exists: $path"}
            [void](Invoke-BB 'create_project' @{name="Practice biome $biome cube v4.2";format='java_block'})
            Eval-BB "($script)('$biome',$json)"
            Export-Project $path
            $capture=Invoke-BB 'set_camera_angle' @{view='biome-cube-proof';position=@(40,34.128,40);target=@(8,8,8);projection='orthographic';zoom=0.25;format='png'}
            $img=$capture.content|Where-Object type -eq 'image'|Select-Object -First 1
            [IO.File]::WriteAllBytes((Join-Path $directory "$biome-cube-v42.png"),[Convert]::FromBase64String($img.data))
        }
    } finally {
        try {[void](Invoke-BB 'delete_offscreen_view' @{view='biome-cube-proof'})}
        catch {if(((Invoke-BB 'list_views' @{})|ConvertTo-Json -Depth 20).Contains('biome-cube-proof')){throw}}
    }
}
if($Task -eq 'EnlargeBiomes') {
    $script=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'resize-practice-biome-icons.js') -Raw
    $directory=Join-Path $root 'sources/practice-biomes'
    foreach($biome in @('plains','desert','badlands','mushroom','snowy_fields','hub')) {
        $path=Join-Path $directory "$biome-v42.bbmodel"
        if((Test-Path -LiteralPath $path) -and -not $Refresh){throw "Biome exists: $path"}
        $model=(Get-Content -LiteralPath (Join-Path $directory "$biome-v41.bbmodel") -Raw).Replace('/','\u002f')
        [void](Eval-BB "(()=>{Codecs.project.load($model,{path:'$biome-v42.bbmodel',no_file:true});Project.name='Practice biome $biome v4.2';return true})()")
        Eval-BB "($script)('$biome')"
        Export-Project $path
    }
}
if($Task -eq 'RefineBiomes') {
    $script=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'refine-practice-biome-blocks.js') -Raw
    $directory=Join-Path $root 'sources/practice-biomes'
    [void](Invoke-BB 'create_offscreen_view' @{id='biome-proof-v41';width=320;height=320;antialias=$false;copy_view='none'})
    try {
        foreach($biome in @('plains','desert','badlands','mushroom','snowy_fields','hub')) {
            $path=Join-Path $directory "$biome-v41.bbmodel"
            if((Test-Path -LiteralPath $path) -and -not $Refresh){throw "Biome exists: $path"}
            $model=(Get-Content -LiteralPath (Join-Path $directory "$biome.bbmodel") -Raw).Replace('/','\u002f')
            [void](Eval-BB "(()=>{Codecs.project.load($model,{path:'$biome-v41.bbmodel',no_file:true});Project.name='Practice biome $biome v4.1';return true})()")
            Eval-BB "($script)('$biome')"
            Export-Project $path
            $capture=Invoke-BB 'set_camera_angle' @{view='biome-proof-v41';position=@(40,34,40);target=@(8,10,8);projection='orthographic';zoom=0.24;format='png'}
            $img=$capture.content|Where-Object type -eq 'image'|Select-Object -First 1
            [System.IO.File]::WriteAllBytes((Join-Path $directory "$biome-v41.png"),[Convert]::FromBase64String($img.data))
        }
    } finally {
        try {[void](Invoke-BB 'delete_offscreen_view' @{view='biome-proof-v41'})}
        catch {
            $views=Invoke-BB 'list_views' @{}
            if(($views|ConvertTo-Json -Depth 20).Contains('biome-proof-v41')){throw}
        }
    }
}
if($Task -eq 'Capture') {
    $capture=Invoke-BB 'capture_app_screenshot' @{max_size=1400;format='png'}
    $img=$capture.content|Where-Object type -eq 'image'|Select-Object -First 1
    [System.IO.File]::WriteAllBytes((Join-Path $root 'sources/practice-menus/blockbench-preview-v4.png'),[Convert]::FromBase64String($img.data))
}
if($Task -eq 'Biomes') {
    if(-not (Test-Path -LiteralPath $ClientJar)){throw 'A vanilla client JAR is required for texture references'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[System.IO.Compression.ZipFile]::OpenRead($ClientJar)
    $images=@{}
    try {
        foreach($name in @('dirt','grass_block_top','oak_log','oak_log_top','oak_leaves','red_wool','stone','sandstone','sand','cactus_side','cactus_top','red_sandstone','red_sand','orange_terracotta','white_terracotta','brown_terracotta','terracotta','mycelium_top','mushroom_stem','red_mushroom_block','brown_mushroom_block','snow','spruce_log','spruce_leaves','packed_ice','bedrock','magma','obsidian','netherrack')) {
            $entry=$archive.GetEntry("assets/minecraft/textures/block/$name.png")
            if(-not $entry){throw "Missing vanilla texture $name"}
            $stream=$entry.Open();$bytes=[System.IO.MemoryStream]::new()
            try {$stream.CopyTo($bytes);$images[$name]='data:image/png;base64,'+[Convert]::ToBase64String($bytes.ToArray())}finally{$stream.Dispose();$bytes.Dispose()}
        }
    } finally {$archive.Dispose()}
    $json=($images|ConvertTo-Json -Depth 5 -Compress).Replace('/','\u002f')
    $script=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'practice-biomes-blockbench.js') -Raw
    $directory=Join-Path $root 'sources/practice-biomes'
    [void][System.IO.Directory]::CreateDirectory($directory)
    [void](Invoke-BB 'create_offscreen_view' @{id='biome-proof';width=320;height=320;antialias=$false;copy_view='none'})
    try {
        foreach($biome in @('plains','desert','badlands','mushroom','snowy_fields','hub')) {
            $path=Join-Path $directory "$biome.bbmodel"
            if((Test-Path -LiteralPath $path) -and -not $Refresh){throw "Biome exists: $path"}
            [void](Invoke-BB 'create_project' @{name="Practice biome $biome";format='java_block'})
            Eval-BB "($script)('$biome',$json)"
            Export-Project $path
            $capture=Invoke-BB 'set_camera_angle' @{view='biome-proof';position=@(40,32,40);target=@(8,8,8);projection='orthographic';zoom=0.25;format='png'}
            $img=$capture.content|Where-Object type -eq 'image'|Select-Object -First 1
            [System.IO.File]::WriteAllBytes((Join-Path $directory "$biome.png"),[Convert]::FromBase64String($img.data))
        }
    } finally {
        try {[void](Invoke-BB 'delete_offscreen_view' @{view='biome-proof'})}
        catch {
            # MCP Server 1.10.0 removes the view but may throw during context-menu disposal.
            $views=Invoke-BB 'list_views' @{}
            if(($views|ConvertTo-Json -Depth 20).Contains('biome-proof')){throw}
        }
    }
}
