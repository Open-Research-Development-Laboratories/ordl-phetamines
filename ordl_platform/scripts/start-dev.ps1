param(
  [switch]$Api,
  [switch]$Ui,
  [switch]$Stack
)

if (-not ($Api -or $Ui -or $Stack)) {
  $Api = $true
  $Ui = $true
}

if ($Api) {
  Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command','cd ordl_platform/backend; python -m uvicorn app.main:app --reload --port 8891'
}

if ($Ui) {
  Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command','cd ordl_platform/frontend; npm run dev'
}

if ($Stack) {
  Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command','cd ordl_platform/infra; podman-compose -f podman-compose.yml up --build'
}
