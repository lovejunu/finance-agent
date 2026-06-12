# 작업 스케줄러 등록 스크립트
# 관리자 권한으로 실행하세요: PowerShell을 "관리자 권한으로 실행"

$TaskName   = "FinanceAgentMorningBriefing"
$ScriptPath = "C:\Users\NKIA1\finance-agent\run_briefing.ps1"

$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""

# 매일 오전 08:00 KST 실행
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host "[OK] '$TaskName' 작업이 등록되었습니다. 매일 08:00 실행됩니다."
