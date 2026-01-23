# Find all debug files related to questions
Write-Host "Searching for debug_questions files..." -ForegroundColor Cyan
Get-ChildItem C:\Users\Seba\Downloads\M30M\Data-analysis\ -Recurse -Filter "debug_questions_C*.txt" -ErrorAction SilentlyContinue | 
    Select-Object FullName, LastWriteTime, @{Name="Size(KB)";Expression={[math]::Round($_.Length/1KB,2)}} |
    Format-Table -AutoSize

Write-Host "`nSearching for any recent .docx or .xlsx files..." -ForegroundColor Cyan
Get-ChildItem C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\ -Recurse -Include "*.docx","*.xlsx" -ErrorAction SilentlyContinue |
    Where-Object {$_.LastWriteTime -gt (Get-Date).AddHours(-2) -and $_.Name -like "*questions*"} |
    Select-Object FullName, LastWriteTime |
    Format-Table -AutoSize
