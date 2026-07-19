cd ~/Projects/ai-resume-coach
rm -rf ~/Downloads/repo-context.zip

rm -rf /tmp/repo-context
mkdir -p /tmp/repo-context


rsync -a \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.terraform/' \
  --exclude='.pytest_cache/' \
  --exclude='__pycache__/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.tfstate' \
  --exclude='*.tfstate.*' \
  --exclude='.DS_Store' \
  ./ \
  /tmp/repo-context/

cd /tmp/repo-context

zip -qr ~/Downloads/repo-context.zip .
