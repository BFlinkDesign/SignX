# Save as: BluebeamAutoOptimizer.ps1
while ($true) {
    # Check if Bluebeam is running
    $revu = Get-Process "Revu" -ErrorAction SilentlyContinue
    
    if ($revu) {
        # BLUEBEAM IS RUNNING - Optimize it
        Write-Host "Bluebeam detected - Optimizing..." -ForegroundColor Green
        
        # Set high priority
        $revu.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::High
        
        # Clear temp files older than 1 day
        Get-ChildItem "$env:TEMP" -Recurse | Where {$_.LastWriteTime -lt (Get-Date).AddDays(-1)} | Remove-Item -Force -ErrorAction SilentlyContinue
        
        # Monitor memory
        if ($revu.WorkingSet -gt 2GB) {
            [System.GC]::Collect()
            Write-Host "Cleared memory" -ForegroundColor Yellow
        }
        
        # Wait 5 minutes before next check
        Start-Sleep -Seconds 300
    }
    else {
        # BLUEBEAM NOT RUNNING - Script sleeps
        Write-Host "Bluebeam not running - sleeping..." -ForegroundColor Gray
        
        # Check every 30 seconds if Bluebeam started
        Start-Sleep -Seconds 30
    }
}