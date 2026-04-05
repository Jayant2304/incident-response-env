#!/usr/bin/env bash
set -euo pipefail

HF_USERNAME="${HF_USERNAME:?Set HF_USERNAME environment variable}"
SPACE_NAME="${SPACE_NAME:-incident-response-env}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLONE_DIR="/tmp/hf-deploy-${SPACE_NAME}"

echo "==> Deploying to HuggingFace Spaces: ${HF_USERNAME}/${SPACE_NAME}"

# Clean previous clone
rm -rf "${CLONE_DIR}"

# Clone the HF Space repo
echo "==> Cloning Space repository..."
git clone "https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}" "${CLONE_DIR}"

# Copy project files
echo "==> Copying project files..."
cp "${SCRIPT_DIR}/Dockerfile"    "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/models.py"     "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/__init__.py"   "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/inference.py"  "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/openenv.yaml"  "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/pyproject.toml" "${CLONE_DIR}/"
cp "${SCRIPT_DIR}/HF_README.md"  "${CLONE_DIR}/README.md"
cp -r "${SCRIPT_DIR}/server"     "${CLONE_DIR}/"

# Commit and push
cd "${CLONE_DIR}"
git add -A
git commit -m "Deploy Production Incident Response OpenEnv environment" || echo "Nothing to commit"
git push

echo "==> Deployment pushed. Watch build at:"
echo "    https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"
echo ""
echo "==> Once running, verify at:"
echo "    https://${HF_USERNAME}-${SPACE_NAME}.hf.space/health"
