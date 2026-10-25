Desktop-Vorschau des Lutris-Forks mit dunkler Bibliothek und hochkantigen Cover-Kacheln.

- Gemeinsame Bibliothek für lokale Spiele und synchronisierte Kataloge angemeldeter Konten, einschließlich nicht installierter Spiele.
- Quellen- und Installationsanzeige, Installationsfilter und Aktualisierung verbundener Bibliotheken.
- Eigene Flatpak-App-ID: `io.github.MarvinFuhr.LutrisLibrary`; bestehendes Lutris und dessen Kontodaten werden nicht ersetzt.

Installation (Linux x86_64): `LutrisLibrary.flatpak` unten unter Assets herunterladen und mit GNOME Software/KDE Discover öffnen oder im Download-Verzeichnis ausführen:

```sh
flatpak install --user ./LutrisLibrary.flatpak
flatpak run io.github.MarvinFuhr.LutrisLibrary
```

Fehlende Laufzeitbibliotheken werden von Flathub geladen. Die Plattformkonten müssen in der Vorschau erneut angemeldet werden.

Geprüft: Installation aus dem Bundle, Versionsabfrage, Datenbankinitialisierung und grafischer Start innerhalb von Flatpak; 675 Tests bestanden, einer übersprungen; Ruff, Formatprüfung, Mypy und Meson erfolgreich. Dialogtests sind wie in CI ausgeschlossen. Die Prozess-Wrapper-Tests sind wegen einer Einschränkung der Cloud-Laufzeit nicht als bestanden gewertet. Tatsächliche Spieleinstallationen und die Vollständigkeit persönlicher Kontobibliotheken sind auf dem Zielsystem zu prüfen. Die bestehenden API-Grenzen der Plattformen gelten weiterhin.

SHA-256: siehe `LutrisLibrary.flatpak.sha256` unter Assets.
