# CANVAS Repository Update Script
Write-Host "Updating CANVAS repository..." -ForegroundColor Cyan

git add .
git commit -m "UI: Relocated drive phase indicator to hybrid panel, updated branding logo, and refined header layout"
git push https://github.com/KISHORENARAYANANSR/CANVAS_CAN-LIN_Automotive_Network_Virtual_Architectur_Simulator

Write-Host "Done!" -ForegroundColor Green
