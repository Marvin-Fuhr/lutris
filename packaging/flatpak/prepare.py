#!/usr/bin/env python3
"""Build a development manifest on top of the installed, verified Lutris Flatpak.

The base keeps upstream's native libraries, runners and runtime extensions. Only
our Python/UI tree is overlaid. Runtime/SDK versions follow the installed base.
"""

import configparser
import json
import subprocess
from pathlib import Path

APP_ID = "io.github.MarvinFuhr.LutrisLibrary"
BASE_ID = "net.lutris.Lutris"


def make_manifest(metadata, source_path):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    config.read_string(metadata)
    runtime, _arch, branch = config["Application"]["runtime"].split("/")
    sdk = config["Application"].get("sdk", runtime.replace(".Platform", ".Sdk")).split("/")[0]
    finish_args = []
    for key, flag in {
        "shared": "share",
        "sockets": "socket",
        "devices": "device",
        "filesystems": "filesystem",
        "features": "allow",
        "persistent": "persist",
    }.items():
        for value in config.get("Context", key, fallback="").split(";"):
            if value:
                # Metadata uses !foo to revoke a permission.
                prefix = {
                    "share": "unshare",
                    "socket": "nosocket",
                    "device": "nodevice",
                    "filesystem": "nofilesystem",
                    "allow": "disallow",
                }.get(flag)
                finish_args.append(f"--{prefix if value.startswith('!') else flag}={value.lstrip('!')}")
    for section, prefix in (("Session Bus Policy", ""), ("System Bus Policy", "system-")):
        if config.has_section(section):
            for name, policy in config[section].items():
                flag = {"talk": "talk-name", "own": "own-name", "none": "no-talk-name"}.get(policy)
                if flag:
                    finish_args.append(f"--{prefix}{flag}={name}")
    if config.has_section("Environment"):
        finish_args.extend(f"--env={key}={value}" for key, value in config["Environment"].items())
    finish_args.append(f"--env=LUTRIS_APPLICATION_ID={APP_ID}")
    return {
        "id": APP_ID,
        "runtime": runtime,
        "runtime-version": branch,
        "sdk": sdk,
        "base": BASE_ID,
        "base-version": "stable",
        "command": "lutris-library",
        "inherit-extensions": [
            section.removeprefix("Extension ")
            for section in config.sections()
            if section.startswith("Extension ") and not section.endswith(".Debug")
        ],
        "finish-args": finish_args,
        "modules": [
            {
                "name": "lutris-library",
                "buildsystem": "simple",
                "build-commands": [
                    "mkdir -p /app/lib/lutris-library /app/bin",
                    "cp -a bin lutris share /app/lib/lutris-library/",
                    "cp -a share/lutris/. /app/share/lutris/",
                    "install -Dm755 packaging/flatpak/lutris-library /app/bin/lutris-library",
                    f"install -Dm644 packaging/flatpak/{APP_ID}.desktop /app/share/applications/{APP_ID}.desktop",
                    (
                        "install -Dm644 share/icons/hicolor/scalable/apps/net.lutris.Lutris.svg "
                        f"/app/share/icons/hicolor/scalable/apps/{APP_ID}.svg"
                    ),
                    (
                        "rm -f /app/share/applications/net.lutris.Lutris.desktop "
                        "/app/share/applications/net.lutris.Lutris1.desktop"
                    ),
                    "rm -f /app/share/metainfo/net.lutris.Lutris.metainfo.xml",
                ],
                "sources": [
                    {"type": "dir", "path": str(source_path / folder), "dest": folder}
                    for folder in ("bin", "lutris", "share", "packaging/flatpak")
                ],
            }
        ],
    }


def main():
    root = Path(__file__).resolve().parents[2]
    metadata = subprocess.check_output(["flatpak", "info", "--user", "--show-metadata", BASE_ID, "stable"], text=True)
    target = root / "build/flatpak/manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(make_manifest(metadata, root), indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
