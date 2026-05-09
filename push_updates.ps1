# CANVAS Repository Update Script
Write-Host "Updating CANVAS repository..." -ForegroundColor Cyan

git add .
git commit -m "Automated update of local CANVAS files"
git push origin main

Write-Host "Done!" -ForegroundColor Green
