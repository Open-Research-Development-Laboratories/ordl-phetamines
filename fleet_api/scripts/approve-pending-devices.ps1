param(
  [int]$DurationSeconds = 600,
  [int]$PollSeconds = 2,
  [switch]$Once
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds([Math]::Max(1, $DurationSeconds))
Write-Host "Watching ordlctl pending devices..."

while ($true) {
  try {
    $raw = ordlctl devices list --json
    $obj = $raw | ConvertFrom-Json
    $pending = @($obj.pending)

    if ($pending.Count -gt 0) {
      Write-Host ("Found {0} pending request(s)." -f $pending.Count)
      foreach ($req in $pending) {
        if ($null -ne $req.requestId -and "$($req.requestId)" -ne "") {
          Write-Host ("Approving requestId={0}" -f $req.requestId)
          ordlctl devices approve $req.requestId | Out-Host
        }
      }
    }
    else {
      Write-Host "No pending device pairing requests."
    }
  }
  catch {
    Write-Warning ("Pairing watcher error: {0}" -f $_.Exception.Message)
  }

  if ($Once) { break }
  if ((Get-Date) -ge $deadline) { break }
  Start-Sleep -Seconds ([Math]::Max(1, $PollSeconds))
}

Write-Host "Pairing watcher complete."
