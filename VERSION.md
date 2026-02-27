
# INSTALL
pip install -r requirements.txt
python run.py

# RECOVERY
git log --oneline -n 5

Copy-Item .env $env:TEMP\.env.backup
git reset --hard 80f714fc
git clean -fd
Copy-Item $env:TEMP\.env.backup .env -Force
git push origin master --force
python run.py

# UPDATE
git add .
git commit -m "v0.0.2 - added FastAPI and AJAX"
git push
python run.py

# DEV LOG
v0.0.2 - added FastAPI and AJAX
v0.0.3 - added Screenshots
v0.0.4 - added Settings.yaml
