"""Keep the preview isolated while retaining the upstream Flatpak dependencies."""

import importlib.util
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
