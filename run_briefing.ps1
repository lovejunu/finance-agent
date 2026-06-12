# finance-agent 모닝 브리핑 실행 스크립트
# Windows 작업 스케줄러에서 호출됩니다

$ScriptDir = "C:\Users\NKIA1\finance-agent"
$LogFile   = "$ScriptDir\briefing.log"

Set-Location $ScriptDir

$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content $LogFile "[$timestamp] 브리핑 시작"

python "$ScriptDir\briefing.py" >> $LogFile 2>&1

$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content $LogFile "[$timestamp] 완료`n"
