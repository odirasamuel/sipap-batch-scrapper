#!/bin/bash
# Build Lambda deployment packages for batch scraper jobs
#
# This script creates deployment packages for:
# 1. Odds Updater Lambda
# 2. Fixture Updater Lambda
#
# Deployment packages include:
# - sipap-batch-scraper source code
# - All dependencies from requirements.txt (minus dev dependencies)
# - Packaged as .zip files for Lambda deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Lambda deployment packages for batch scraper jobs${NC}"
echo ""

# Change to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Create output directory
LAMBDA_PACKAGES_DIR="${REPO_ROOT}/../../sipap-terraform/lambda_packages"
mkdir -p "$LAMBDA_PACKAGES_DIR"

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
echo -e "${YELLOW}Using temporary build directory: $BUILD_DIR${NC}"

# Function to build a Lambda package
build_lambda_package() {
    local job_name=$1
    local handler_module=$2
    local output_zip=$3

    echo ""
    echo -e "${GREEN}Building $job_name Lambda package...${NC}"

    # Create package directory
    PACKAGE_DIR="$BUILD_DIR/$job_name"
    mkdir -p "$PACKAGE_DIR"

    # Install dependencies (excluding dev dependencies and sipap-common)
    echo "Installing dependencies..."
    pip install \
        -r requirements-lambda.txt \
        -t "$PACKAGE_DIR" \
        --no-cache-dir \
        --platform manylinux2014_aarch64 \
        --only-binary=:all: \
        --python-version 3.12 \
        --implementation cp \
        --upgrade

    # Remove unnecessary files to reduce package size
    echo "Cleaning up unnecessary files..."
    find "$PACKAGE_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$PACKAGE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PACKAGE_DIR" -type f -name "*.pyc" -delete
    find "$PACKAGE_DIR" -type f -name "*.pyo" -delete
    find "$PACKAGE_DIR" -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

    # Copy sipap-common source code
    echo "Copying sipap-common..."
    SIPAP_COMMON_DIR="$REPO_ROOT/../sipap-common/src/sipap_common"
    if [ -d "$SIPAP_COMMON_DIR" ]; then
        cp -r "$SIPAP_COMMON_DIR" "$PACKAGE_DIR/"
    else
        echo -e "${RED}ERROR: sipap-common not found at $SIPAP_COMMON_DIR${NC}"
        echo "Please ensure sipap-common is cloned at: $REPO_ROOT/../sipap-common"
        exit 1
    fi

    # Copy batch-scraper source code
    echo "Copying sipap-batch-scraper source code..."
    cp -r src/sipap_batch_scraper "$PACKAGE_DIR/"

    # Create zip file
    echo "Creating zip archive..."
    cd "$PACKAGE_DIR"
    zip -r "$output_zip" . -q
    cd "$REPO_ROOT"

    # Get zip file size
    ZIP_SIZE=$(du -h "$output_zip" | cut -f1)
    echo -e "${GREEN}✓ Package created: $output_zip (${ZIP_SIZE})${NC}"
}

# Build Odds Updater package
build_lambda_package \
    "odds_updater" \
    "sipap_batch_scraper.jobs.odds_updater" \
    "$LAMBDA_PACKAGES_DIR/odds_updater.zip"

# Build Fixture Updater package
build_lambda_package \
    "fixture_updater" \
    "sipap_batch_scraper.jobs.fixture_updater" \
    "$LAMBDA_PACKAGES_DIR/fixture_updater.zip"

# Cleanup
echo ""
echo "Cleaning up temporary build directory..."
rm -rf "$BUILD_DIR"

echo ""
echo -e "${GREEN}✓ Lambda packages built successfully!${NC}"
echo ""
echo "Packages created in: $LAMBDA_PACKAGES_DIR"
ls -lh "$LAMBDA_PACKAGES_DIR"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review package sizes (Lambda limit: 50MB zipped, 250MB unzipped)"
echo "2. Deploy using terraform:"
echo "   cd ../../sipap-terraform"
echo "   terraform plan"
echo "   terraform apply"
echo ""
