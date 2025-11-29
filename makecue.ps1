# POWERJAIL SERATO IMPORTER (V12: Wrap Support - No Popup)

# --- CONFIGURATION ---
function Get-Config {
    $configPath = Join-Path (Get-ScriptPath) "config.json"
    if (Test-Path $configPath) { return Get-Content $configPath | ConvertFrom-Json }
    return $null
}

function Save-Config($performer, $lastMode) {
    $data = @{ DefaultPerformer = $performer; LastMode = $lastMode }
    $data | ConvertTo-Json | Set-Content (Join-Path (Get-ScriptPath) "config.json")
}

function Get-ScriptPath {
    if ($PSScriptRoot) { return $PSScriptRoot }
    return $PWD.Path
}

function Clean-Text($str) {
    if ($null -eq $str) { return "" }
    $str = $str -replace "<[^>]+>", "" 
    $str = [System.Net.WebUtility]::HtmlDecode($str)
    return $str.Trim()
}

# --- PARSER: LOCAL CLIPBOARD (Multiline Smart Logic) ---
function Parse-SeratoHistoryText($rawLines) {
    $parsedTracks = @()
    $firstStartTime = $null
    $mixDate = ""
    $dateFormat = "dd/MM/yyyy HH:mm:ss"
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $timeRegex = "(\d{1,2}:\d{2}:\d{2})"

    # 1. Extract Date from Header
    foreach ($line in $rawLines) {
        if ($line -match "^(\d{2}/\d{2}/\d{4})") { $mixDate = $matches[1]; break }
    }

    # 2. Iterate lines with a "Line Buffer"
    $lineBuffer = ""

    foreach ($line in $rawLines) {
        $line = $line.Trim()
        # Skip junk
        if ($line -eq "" -or $line -match "^-" -or $line -match "^Song\s+.*Start Time") { continue }
        
        # Check if this line has the "Start Time" (The trigger to process the track)
        if ($line -match $timeRegex) {
            $foundTime = $matches[1]
            
            # Get text on this specific line before the time
            $textOnTimeLine = ($line -split $timeRegex)[0].Trim()
            
            # Combine with whatever was in the buffer (previous lines)
            $fullTrackString = "$lineBuffer $textOnTimeLine".Trim()
            
            # Reset buffer for next track
            $lineBuffer = ""
            
            # SPLIT BY 2+ SPACES (Serato's visual column separator)
            $cols = $fullTrackString -split "\s{2,}"
            
            if ($cols.Count -ge 2) {
                # Logic: Last column is Artist, everything before is Title
                $artist = $cols[-1]
                $title = ($cols[0..($cols.Count-2)] -join " ")
            } else {
                $title = $cols[0]
                $artist = "Unknown"
            }

            # Relative Time Logic
            try {
                $dateBase = if ($mixDate) { $mixDate } else { (Get-Date).ToString("dd/MM/yyyy") }
                $fullDateTimeStr = "$dateBase $foundTime"
                $currDate = [DateTime]::ParseExact($fullDateTimeStr, $dateFormat, $culture)
                
                if ($null -eq $firstStartTime) {
                    $firstStartTime = $currDate
                    $relTime = "00:00:00"
                } else {
                    $diff = $currDate - $firstStartTime
                    if ($diff.TotalSeconds -lt 0) { $diff = $diff.Add([TimeSpan]::FromDays(1)) }
                    $relTime = $diff.ToString("hh\:mm\:ss")
                }

                $parsedTracks += [PSCustomObject]@{
                    Time = $relTime
                    Title = Clean-Text $title
                    Artist = Clean-Text $artist
                }
            } catch { }

        } else {
            # No time on this line? It must be a wrapped Title/Artist.
            # Add it to the buffer and wait for the time line.
            if ($line -notmatch "^\d{2}/\d{2}/\d{4}") {
                $lineBuffer += " $line"
            }
        }
    }
    return @{ Date = $mixDate; Tracks = $parsedTracks }
}

# --- PARSER: WEB SCRAPER ---
function Get-SeratoPlaylist($url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing
        $contentStream = [System.IO.MemoryStream][System.Text.Encoding]::UTF8.GetBytes($response.Content)
        $streamReader = New-Object System.IO.StreamReader($contentStream, [System.Text.Encoding]::UTF8)
        $html = $streamReader.ReadToEnd()
        
        $albumTitle = "Unknown Mix"; $performer = "Unknown DJ"; $mixDate = ""
        
        if ($html -match "<title>(.*?)</title>") {
            $rawTitle = Clean-Text ($matches[1] -replace " - Serato DJ Playlists", "")
            $parts = $rawTitle -split " - "
            if ($parts.Count -ge 3) {
                $performer = $parts[-1].Trim()
                $dateIndex = $parts.Count - 2
                $albumTitle = ($parts[0..($dateIndex-1)] -join " - ").Trim()
            } elseif ($parts.Count -eq 2) {
                $albumTitle = $parts[0].Trim(); $performer = $parts[1].Trim()
            } else { $albumTitle = $rawTitle }
        }
        if ($html -match 'class="playlist-date">\s*(.*?)\s*<') { $mixDate = $matches[1].Trim() }
        elseif ($html -match '(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})') { $mixDate = $matches[1].Trim() }

        $trackData = @()
        $pattern = 'class="playlist-tracktime">\s*([\d:]+)\s*</div>.*?class="playlist-trackname">\s*(.*?)\s*</div>'
        $matches = [regex]::Matches($html, $pattern, "Singleline")
        foreach ($m in $matches) {
            $rawName = Clean-Text $m.Groups[2].Value
            if ($rawName -match " - ") {
                $p = $rawName -split " - ", 2
                $tArtist = $p[0]; $tTitle = $p[1]
            } else {
                $tArtist = "Unknown"; $tTitle = $rawName
            }
            $trackData += [PSCustomObject]@{ Time = $m.Groups[1].Value; Title = $tTitle; Artist = $tArtist }
        }
        return [PSCustomObject]@{ Title = $albumTitle; Performer = $performer; Date = $mixDate; Tracks = $trackData }
    } catch { return $null }
}

# --- GENERATOR: CUE FILE ---
function Save-CueFile($playlistObj, $filenameOverride) {
    $cleanTitle = $playlistObj.Title.Replace('"', "'")
    $cleanPerformer = $playlistObj.Performer.Replace('"', "'")
    $cleanDate = $playlistObj.Date
    
    if ($filenameOverride) { $baseName = $filenameOverride } else { $baseName = $playlistObj.Title }
    $baseName = $baseName -replace "\.mp3$", "" -replace "\.MP3$", ""
    $safeBaseName = $baseName -replace '[<>:"/\\|?*]', ''
    
    $saveDir = Get-ScriptPath
    $counter = 1
    $finalBaseName = $safeBaseName
    while (Test-Path (Join-Path $saveDir "$finalBaseName.cue")) {
        $finalBaseName = "$safeBaseName ($counter)"; $counter++
    }
    $outputFile = Join-Path $saveDir "$finalBaseName.cue"
    $finalAudioFile = "$baseName.mp3"

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine("PERFORMER `"$cleanPerformer`"")
    [void]$sb.AppendLine("TITLE `"$cleanTitle`"")
    if ($cleanDate) { [void]$sb.AppendLine("REM DATE `"$cleanDate`"") }
    [void]$sb.AppendLine("FILE `"$finalAudioFile`" MP3")

    $trackNum = 1
    foreach ($row in $playlistObj.Tracks) {
        $tTitle = $row.Title.Replace('"', "'")
        $tArtist = $row.Artist.Replace('"', "'")
        $timeLine = $row.Time

        if ($timeLine.Length -eq 5) { $timeLine = "00:$timeLine" } 
        $trackStr = "{0:D2}" -f $trackNum

        [void]$sb.AppendLine("  TRACK $trackStr AUDIO")
        [void]$sb.AppendLine("    TITLE `"$tTitle`"")
        [void]$sb.AppendLine("    PERFORMER `"$tArtist`"")

        try {
            $ts = [TimeSpan]::Parse($timeLine)
            $idx01_Min = [math]::Floor($ts.TotalMinutes).ToString("00")
            $idx01_Sec = $ts.Seconds.ToString("00")
            if ($trackNum -gt 1) {
                $tsPrev = $ts.Add([TimeSpan]::FromSeconds(-1))
                $idx00_Min = [math]::Floor($tsPrev.TotalMinutes).ToString("00")
                $idx00_Sec = $tsPrev.Seconds.ToString("00")
                [void]$sb.AppendLine("    INDEX 00 $idx00_Min`:$idx00_Sec`:00")
            }
            [void]$sb.AppendLine("    INDEX 01 $idx01_Min`:$idx01_Sec`:00")
        } catch { }
        $trackNum++
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($outputFile, $sb.ToString(), $utf8NoBom)
    Write-Host "Saved: $finalBaseName.cue" -ForegroundColor Green
}

# --- MAIN MENU ---
$cfg = Get-Config
$defaultDJ = if ($cfg) { $cfg.DefaultPerformer } else { "" }
$lastMode = if ($cfg) { $cfg.LastMode } else { "1" }

Write-Host "--- DJ CUE AUTOMATION V12 (Wrap Support) ---" -ForegroundColor Cyan
Write-Host "1. SERATO WEBSITE: Single Playlist URL" -ForegroundColor Gray
Write-Host "2. LOCAL CLIPBOARD: History Export (Any Layout)" -ForegroundColor Magenta
Write-Host "3. SERATO WEBSITE: Batch Profile Download" -ForegroundColor Yellow
$mode = Read-Host "Choose Mode (Default: $lastMode)"
if ($mode -eq "") { $mode = $lastMode }

if ($mode -eq "3") {
    $profileUrl = Read-Host "Paste Serato Profile URL"
    if (-not $profileUrl) { $profileUrl = "https://serato.com/playlists/Caio_Bueno" }
    try {
        $response = Invoke-WebRequest -Uri $profileUrl -UseBasicParsing
        $html = $response.Content
        $userPart = $profileUrl.Split("/")[-1]
        $matches = [regex]::Matches($html, 'href="(/playlists/' + $userPart + '/[^"]+)"')
        $links = $matches | ForEach-Object { "https://serato.com" + $_.Groups[1].Value } | Select-Object -Unique
        foreach ($link in $links) {
            $data = Get-SeratoPlaylist $link
            if ($data) { Save-CueFile $data $null }
            Start-Sleep -Seconds 1
        }
    } catch { Write-Host "Failed." -ForegroundColor Red }
} elseif ($mode -eq "1") {
    $url = Read-Host "Paste Playlist URL"
    $data = Get-SeratoPlaylist $url
    if ($data) {
        $fname = Read-Host "Enter Filename (Default: $($data.Title))"
        if ($fname -eq "") { $fname = $data.Title }
        Save-CueFile $data $fname
    }
} elseif ($mode -eq "2") {
    $rawLines = Get-Clipboard
    if (-not $rawLines) { Write-Host "Clipboard is empty!" -ForegroundColor Red; exit }
    Write-Host "Loaded $($rawLines.Count) lines." -ForegroundColor Green

    # Run the new Wrap-Safe Parser
    $result = Parse-SeratoHistoryText $rawLines
    $trackData = $result.Tracks
    $date = $result.Date
    
    if ($trackData.Count -eq 0) {
        # Fallback to Simple List if parsing failed
        Write-Host "Complex parse failed. Trying simple list..." -ForegroundColor DarkGray
        $cleanLines = $rawLines | Where-Object { $_.Trim() -and $_ -notmatch "^\d{1,2}:\d{2}\s*[aApP][mM]$" }
        for ($i=0; $i -lt $cleanLines.Count; $i+=2) {
            if (($i+1) -lt $cleanLines.Count) { 
                $rawName = Clean-Text $cleanLines[$i+1]
                if ($rawName -match " - ") { $p=$rawName-split" - ",2; $tA=$p[0];$tT=$p[1] } else { $tA="Unknown";$tT=$rawName }
                $trackData += [PSCustomObject]@{ Time=$cleanLines[$i].Trim(); Title=$tT; Artist=$tA } 
            }
        }
    }

    if ($trackData.Count -eq 0) { Write-Host "No tracks found." -ForegroundColor Red; exit }

    $performerPrompt = "Enter DJ Name"
    if ($defaultDJ) { $performerPrompt += " (Default: $defaultDJ)" }
    $performer = Read-Host $performerPrompt
    if ($performer -eq "") { $performer = $defaultDJ }
    
    $title = Read-Host "Enter Mix Title"
    if (-not $date) { $date = Read-Host "Enter Date" }
    $fname = Read-Host "Enter Filename"

    Save-Config $performer $mode
    $data = [PSCustomObject]@{ Title = $title; Performer = $performer; Date = $date; Tracks = $trackData }
    Save-CueFile $data $fname
}

Read-Host "`nPress Enter to close..."