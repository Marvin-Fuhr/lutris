"""Keep the preview isolated while retaining the upstream Flatpak dependencies."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("flatpak_prepare", "packaging/flatpak/prepare.py")
assert spec is not None and spec.loader is not None
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

METADATA = """[Application]
name=net.lutris.Lutris
runtime=org.gnome.Platform/x86_64/49
sdk=org.gnome.Sdk/x86_64/49
[Context]
shared=network;ipc;
sockets=x11;wayland;pulseaudio;
devices=dri;
filesystems=home;!host;
features=multiarch;
[Environment]
WEBKIT_DISABLE_DMABUF_RENDERER=1
[Session Bus Policy]
org.freedesktop.Flatpak=talk
[Extension org.freedesktop.Platform.Compat.i386]
directory=lib/i386-linux-gnu
version=25.08
"""


class FlatpakManifestTest(unittest.TestCase):
    def test_runtime_and_extensions_follow_installed_lutris(self):
        manifest = prepare.make_manifest(METADATA, Path("/checkout"))
        self.assertEqual(manifest["runtime-version"], "49")
        self.assertEqual(manifest["base"], "net.lutris.Lutris")
        self.assertIn("org.freedesktop.Platform.Compat.i386", manifest["inherit-extensions"])
        self.assertIn("--talk-name=org.freedesktop.Flatpak", manifest["finish-args"])
        self.assertIn("--nofilesystem=host", manifest["finish-args"])

    def test_identity_is_distinct_and_build_outputs_are_not_sources(self):
        manifest = prepare.make_manifest(METADATA, Path("/checkout"))
        self.assertNotEqual(manifest["id"], manifest["base"])
        self.assertIn(f"--env=LUTRIS_APPLICATION_ID={manifest['id']}", manifest["finish-args"])
        sources = manifest["modules"][0]["sources"]
        self.assertEqual({entry["dest"] for entry in sources}, {"bin", "lutris", "share", "packaging/flatpak"})
        self.assertNotIn("/checkout", {entry["path"] for entry in sources})

    def test_branding_replaces_base_icons_and_exports_png_sizes_for_preview_id(self):
        commands = prepare.make_manifest(METADATA, Path("/checkout"))["modules"][0]["build-commands"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "app/share/icons"
            destination.mkdir(parents=True)
            for size in ("16x16", "128x128", "scalable"):
                suffix = ".svg" if size == "scalable" else ".png"
                relative = Path("hicolor") / size / "apps" / ("net.lutris.Lutris" + suffix)
                source = root / "share/icons" / relative
                source.parent.mkdir(parents=True)
                source.write_bytes(b"new branding " + size.encode())
                old = destination / relative
                old.parent.mkdir(parents=True)
                old.write_bytes(b"old base icon")
            for command in commands:
                if command.startswith(
                    ("cp -a share/icons/", "for icon in share/icons/", "install -Dm644 share/icons/")
                ):
                    subprocess.run(command.replace("/app/", str(root / "app") + "/"), cwd=root, shell=True, check=True)
            for size in ("16x16", "128x128", "scalable"):
                suffix = ".svg" if size == "scalable" else ".png"
                directory = destination / "hicolor" / size / "apps"
                self.assertEqual((directory / (prepare.APP_ID + suffix)).read_bytes(), b"new branding " + size.encode())
                self.assertEqual(
                    (directory / ("net.lutris.Lutris" + suffix)).read_bytes(), b"new branding " + size.encode()
                )
        self.assertIn("gtk-update-icon-cache -f -t /app/share/icons/hicolor", commands)
