# CANVAS Repository Safe Sync Script
Write-Host "Starting Safe Synchronization with GitHub..." -ForegroundColor Cyan

# 1. Save local state
Write-Host "Saving local files..." -ForegroundColor Yellow
git add .
git commit -m "Save local project state before syncing README"

# 2. Update remote URL
Write-Host "Configuring GitHub remote..." -ForegroundColor Yellow
git remote remove origin
git remote add origin https://github.com/KISHORENARAYANANSR/CANVAS_Automotive-Network-Simulation-Cybersecurity-Testing-Platform.git

# 3. Pull README safely
Write-Host "Pulling README from GitHub..." -ForegroundColor Yellow
git pull origin main --allow-unrelated-histories --no-rebase --no-edit
if ($LASTEXITCODE -ne 0) {
    Write-Host "Main branch not found, trying master branch..." -ForegroundColor Yellow
    git pull origin master --allow-unrelated-histories --no-rebase --no-edit
}

# 4. Push everything back
Write-Host "Pushing synchronized project back to GitHub..." -ForegroundColor Yellow
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    git push -u origin master
}

Write-Host "Synchronization Complete!" -ForegroundColor Green
