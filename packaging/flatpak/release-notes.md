Neue Vorschau mit animierter Rasterbibliothek und neuem Logo.

- Cover wachsen beim Überfahren mit der Maus weich auf 108 %, bleiben vergrößert und schrumpfen beim Verlassen zurück. Das Raster verschiebt sich dabei nicht.
- Mausrad-Scrolling erhält einen kurzen Übergang. Touchpad-Gesten, Scrollbar und Tastatur bleiben direkt bedienbar. Die Systemeinstellung für reduzierte Animationen wird respektiert.
- Neues Logo aus der gelieferten Original-PNG: App-, Tray- und Dateityp-Icons, Info-Dialog, Platzhalter und Splash-Grafiken. Alle vorhandenen Größen und Transparenz bleiben erhalten. Die SVG-Dateien betten die PNG verlustfrei ein; sie sind keine nachgezeichneten Vektorgrafiken.
- Bestehende Konten, Spiele, Runner, Installer und die gemeinsame Bibliothek bleiben erhalten.

## Installieren oder aktualisieren

`LutrisLibrary.flatpak` unter **Assets** herunterladen und mit GNOME Software/KDE Discover öffnen. Alternativ im Download-Verzeichnis:

```sh
flatpak install --user ./LutrisLibrary.flatpak
flatpak run io.github.MarvinFuhr.LutrisLibrary
```

Die App-ID bleibt `io.github.MarvinFuhr.LutrisLibrary`. Beim Aktualisieren dieser Vorschau bleiben ihre Einstellungen und Kontodaten erhalten. Die offizielle Lutris-Installation wird nicht ersetzt. Fehlende Laufzeitbibliotheken werden von Flathub geladen.

Validierung: 686 Tests bestanden, einer übersprungen; zusätzliche GTK-Tests für Hover, Richtungswechsel, Scrollgrenzen, Touchpad-/Scrollbar-Unterbrechung und reduzierte Animationen. Ruff und Mypy fehlerfrei. Die vorhandenen Dialogtests sind wie in CI ausgeschlossen; die Prozess-Wrapper-Tests können in der Cloud-Laufzeit mangels `/proc/.../children` nicht sinnvoll ausgeführt werden. Reale Spiele- und Kontotests erfolgen auf dem Zielsystem.

SHA-256: siehe `LutrisLibrary.flatpak.sha256` unter Assets.
