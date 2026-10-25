#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in flatpak flatpak-builder python3; do
  command -v "$tool" >/dev/null || { echo "Missing required tool: $tool" >&2; exit 1; }
done
# User-scoped installs; no root access is required after installing the tools.
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub net.lutris.Lutris//stable
python3 packaging/flatpak/prepare.py
flatpak-builder --user --assumeyes --install-deps-from=flathub --force-clean --disable-rofiles-fuse \
  --state-dir=build/flatpak/state --repo=build/flatpak/repo \
  build/flatpak/app build/flatpak/manifest.json
mkdir -p dist
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
  build/flatpak/repo dist/LutrisLibrary.flatpak io.github.MarvinFuhr.LutrisLibrary master
printf 'Built: %s/dist/LutrisLibrary.flatpak\n' "$PWD"
