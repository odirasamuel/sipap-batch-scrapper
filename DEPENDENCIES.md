# Batch Scraper Dependencies

This document explains the dependency management strategy for the batch scraper.

## Requirements Files

### `requirements.txt` (Development)
Full dependencies for local development including:
- `sipap-common` - Installed from local repository
- All production dependencies
- Development dependencies (pytest, mypy, ruff, etc.)

**Usage:**
```bash
# For local development
pip install -e '.[dev]'
# Or
pip install -r requirements.txt
```

### `requirements-lambda.txt` (Production/Lambda)
Production-only dependencies for Lambda deployment, **excluding**:
- `sipap-common` (bundled directly from source)
- Development dependencies (pytest, mypy, etc.)

**Usage:**
- Used automatically by GitHub Actions workflow
- Used by `scripts/build_lambda_packages.sh`

## sipap-common Dependency

`sipap-common` is a local package (not published to PyPI) that contains shared utilities across SIPAP services.

### How It's Handled

**Local Development:**
- Installed from: `/Users/charlesotuya/AI-Odi/sentinel/sipap/repos/sipap-common`
- Via: `pip install -e ../sipap-common`
- Or: Listed in `requirements.txt` as `sipap-common>=0.1.0`

**Lambda Packages (GitHub Actions):**
1. Workflow checks out both repositories:
   - `sipap-batch-scraper` (main code)
   - `sipap-common` (dependency)
2. Installs production dependencies from `requirements-lambda.txt`
3. **Copies `sipap-common` source directly** into the Lambda package:
   ```bash
   cp -r sipap-common/src/sipap_common $PACKAGE_DIR/
   ```
4. Copies `sipap-batch-scraper` source
5. Creates deployment package (.zip)

**Lambda Packages (Manual Build):**
Same approach as GitHub Actions:
```bash
./scripts/build_lambda_packages.sh
```
Script expects `sipap-common` to be at `../sipap-common/`

### Why This Approach?

**Alternatives considered:**
1. ❌ **Publish to PyPI** - Requires PyPI account, package maintenance
2. ❌ **Private PyPI server** - Extra infrastructure, complexity
3. ❌ **Git dependencies** (`git+https://...`) - Requires authentication in CI/CD
4. ✅ **Bundle source directly** - Simple, no external dependencies, works in CI/CD

**Benefits:**
- No PyPI publishing needed
- No authentication complexity
- Works in GitHub Actions out of the box
- Same approach for local and CI/CD builds
- Full source code included (easy debugging)

## Dependency Updates

### Updating Production Dependencies

1. Edit `requirements-lambda.txt`
2. Commit and push (triggers GitHub Actions)
3. Packages automatically rebuilt with new dependencies

### Updating sipap-common

**No action needed!**

GitHub Actions always uses the latest `sipap-common` from the `main` branch.

If you need a specific version:
1. Use git tags in sipap-common repository
2. Update workflow to checkout specific tag:
   ```yaml
   - name: Checkout sipap-common repository
     uses: actions/checkout@v4
     with:
       repository: odirasamuel/sipap-common
       ref: v0.2.0  # Specific version
       path: sipap-common
   ```

### Updating Development Dependencies

Edit `requirements.txt` only (doesn't affect Lambda packages).

## Troubleshooting

### "sipap-common not found" Error (Local Build)

**Symptom:**
```
ERROR: sipap-common not found at /path/to/sipap-common/src/sipap_common
```

**Solution:**
Ensure sipap-common is cloned in the correct location:
```bash
cd /Users/charlesotuya/AI-Odi/sentinel/sipap/repos/
ls -la sipap-common/  # Should exist

# If missing:
git clone https://github.com/odirasamuel/sipap-common.git
```

### "Could not find a version that satisfies the requirement sipap-common" (GitHub Actions)

**Symptom:**
```
ERROR: No matching distribution found for sipap-common>=0.1.0
```

**Solution:**
This error should NOT occur if using `requirements-lambda.txt`.

Check that the workflow is using `requirements-lambda.txt`:
```yaml
pip install -r requirements-lambda.txt  # ✅ Correct
pip install -r requirements.txt         # ❌ Wrong (has sipap-common)
```

### Package Size Too Large

**Symptom:**
Lambda deployment package exceeds 50MB (zipped) or 250MB (unzipped).

**Solution:**
1. Check what's included:
   ```bash
   unzip -l lambda_packages/odds_updater.zip | head -50
   ```

2. Exclude large unnecessary dependencies in `requirements-lambda.txt`

3. Remove test files from sipap-common before copying:
   ```bash
   # In workflow or build script
   find sipap-common/src/sipap_common -type d -name "tests" -exec rm -rf {} +
   ```

## Architecture Diagram

```
sipap-batch-scraper/
├── requirements.txt          # Full deps (dev + prod + sipap-common)
├── requirements-lambda.txt   # Production only (no sipap-common, no dev)
└── src/sipap_batch_scraper/

sipap-common/                 # Separate repository
└── src/sipap_common/         # Bundled directly into Lambda packages

Lambda Package Structure:
lambda_package.zip
├── sipap_common/            # ← Copied from sipap-common/src/
├── sipap_batch_scraper/     # ← Copied from sipap-batch-scraper/src/
├── playwright/              # ← From requirements-lambda.txt
├── scrapy/                  # ← From requirements-lambda.txt
├── boto3/                   # ← From requirements-lambda.txt
└── ... (other dependencies)
```

---

**Last Updated:** 2026-06-28
**Maintained By:** CI/CD Team
