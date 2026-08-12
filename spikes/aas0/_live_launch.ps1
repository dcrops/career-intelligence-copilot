Set-Location 'C:\Users\dcropper\Projects\AI_Projects\career-intelligence-copilot'
$env:PYTHONPATH = 'src;spikes'
$env:NODE_OPTIONS = '--use-system-ca'
Write-Host ''
Write-Host '=== AAS-0 LIVE (restarted with Quick apply fix) ==='
Write-Host '1. In the Playwright Chromium window: Sign in to SEEK if needed.'
Write-Host '2. Return HERE and press Enter when the job page is ready.'
Write-Host '3. Answer unknown questions in THIS window when prompted.'
Write-Host '4. Spike will NOT click final Submit.'
Write-Host ''
python spikes/aas0/run_assist.py --authorize-live --manual-comparison-minutes 25
Write-Host ''
Write-Host 'Spike process exited. You can close this window.'
pause
