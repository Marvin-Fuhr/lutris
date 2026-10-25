# Lutris Library Preview als Flatpak testen

Der Fork behält Lutris' GTK-Desktopanwendung, Runner, Installer, Spieleaktionen,
Suche, Kategorien, Listenansicht und Plattformanbindungen. Die Standardbibliothek
kombiniert lokale Spiele mit den bereits synchronisierten Bibliotheken verbundener
Konten. Spiele müssen dafür weder installiert noch in die lokale Lutris-Datenbank
importiert werden. Die Oberfläche verwendet ein dunkles Farbschema, Cover im
2:3-Format, Quellen-/Installationsbeschriftungen und einen sichtbaren Installationsfilter.
Die bisherigen Anzeigeformate und Zoomstufen bleiben über das Ansichtsmenü verfügbar.

## Fertiges Paket installieren

Das gebaute Paket liegt unter `dist/LutrisLibrary.flatpak` (Linux x86_64).
Es benötigt zum Installieren nur Flatpak, keinen Compiler und kein SDK.
Die Datei kann mit GNOME Software oder KDE Discover geöffnet werden, wenn dort
Flatpak-Unterstützung installiert ist. Alternativ im Verzeichnis der Datei:

```sh
flatpak install --user ./LutrisLibrary.flatpak
flatpak run io.github.MarvinFuhr.LutrisLibrary
```

Fehlende Laufzeitbibliotheken werden über die im Paket hinterlegte Flathub-Adresse
bezogen. Dafür ist beim ersten Installieren eine Internetverbindung nötig.

## Selbst bauen

Auf einem Linux-Desktop werden `flatpak`, `flatpak-builder`, Python 3 und eine
Internetverbindung zu Flathub benötigt, beispielsweise unter Debian/Ubuntu:

```sh
sudo apt install flatpak flatpak-builder python3
```

Im Wurzelverzeichnis dieses Repositorys:

```sh
./packaging/flatpak/build.sh
flatpak install --user ./dist/LutrisLibrary.flatpak
flatpak run io.github.MarvinFuhr.LutrisLibrary
```

Das Skript installiert die offizielle Lutris-Version benutzerbezogen von Flathub
als Build-Basis, übernimmt deren Runtime, SDK, Erweiterungen und Berechtigungen
und legt den Quellcode dieses Checkouts darüber. `flatpak-builder` installiert das
benötigte SDK automatisch. Der erste Build kann mehrere GB Downloads und freien
Speicher benötigen; spätere Builds verwenden die vorhandene Basis. Es wird kein
separates Wine-/WebKit-Paket selbst zusammengestellt. Flathubs Signaturprüfung
bleibt aktiv. Der Build verwendet die auf diesem Rechner installierte stabile
Lutris-Basis; deren Aktualisierung kann die Laufzeitabhängigkeiten ändern.

Das erzeugte Paket liegt in `dist/LutrisLibrary.flatpak`. Für weitere Änderungen
erneut das Build-Skript ausführen und das Paket installieren. Build-Zustand,
Manifest und lokales Flatpak-Repository liegen unter `build/flatpak`.

Alternativ kann nach dem Push im eigenen GitHub-Fork unter Actions der Workflow
„Build Library Preview Flatpak“ manuell gestartet werden. Er lädt das Bundle als
Artifact `LutrisLibrary-flatpak` hoch. Beim Push eines Tags `library-preview-v*`
baut derselbe Workflow das Paket und veröffentlicht es mit Prüfsumme automatisch
als GitHub-Vorabversion. Dafür verwendet er das kurzlebige `github.token` des
Workflows; ein persönlicher Token ist nicht erforderlich.

Die Testversion hat die eigene App-ID `io.github.MarvinFuhr.LutrisLibrary`, einen
eigenen Menüeintrag und eigene Konfigurations-/Kontodaten unter
`~/.var/app/io.github.MarvinFuhr.LutrisLibrary`. Sie ersetzt die offizielle
Installation nicht. In der Testversion erneut bei den gewünschten Plattformen
anmelden. Die Kontodaten der bestehenden Installation werden nicht kopiert.
Die Berechtigungen entsprechen denen der offiziellen Basis, einschließlich Zugriff
auf Spiele im Home-Verzeichnis und auf Datenträgern. Installationen und Änderungen
an denselben Spieledateien sind deshalb zwischen beiden Versionen sichtbar.

## Funktionsprüfung auf dem Desktop

Ab Preview v0.2.0: Cover wachsen
beim Überfahren mit der Maus in etwa 180 ms auf 108 %, bleiben dort und schrumpfen
beim Verlassen wieder. Die Rastergeometrie bleibt dabei stabil. Mausrad-Schritte
werden über etwa 160 ms interpoliert; Touchpad-Gesten und horizontales Scrollen
verwenden weiterhin GTKs native Verarbeitung. Scrollbar und Tastatur können einen
laufenden Mausrad-Übergang sofort unterbrechen. Wenn Animationen systemweit
abgeschaltet sind, erfolgt der Hover-Wechsel sofort und das Scrollen bleibt nativ.

Das neue Logo wurde aus der transparenten Original-PNG übernommen. Die Quelle
liegt unter `packaging/branding/logo-source.png`. Erneutes Erzeugen aller Varianten:
`python3 utils/update_branding.py packaging/branding/logo-source.png`.
Das Werkzeug ersetzt die bestehenden
App-/Dateityp-Icons sowie Logo-, Platzhalter- und Splash-Dateien. PNGs behalten ihre
jeweiligen Größen und RGBA-Kodierung; SVGs behalten ihre ursprünglichen Abmessungen
und enthalten das Originalbild als eingebettetes PNG. Rasterbilder werden dabei
nicht nachgezeichnet oder als echte Vektorgrafik ausgegeben.

1. Bei GOG, Epic und/oder weiteren verwendeten Diensten anmelden. Nach erfolgreicher
   Anmeldung wird die Bibliothek geladen. Die Schaltfläche zum Aktualisieren neben
   „Installed only“ lädt alle verbundenen Bibliotheken erneut; auch beim Start wird
   synchronisiert. Die Quellen können weiterhin einzeln in der Seitenleiste geöffnet
   und aktualisiert werden.
2. In „Games“ erscheinen lokale und nicht installierte Kontospiele zusammen. Ein
   installiertes Spiel mit derselben Plattform-/App-ID erscheint nur einmal. Derselbe
   Titel auf unterschiedlichen Stores bleibt als separate Lizenz sichtbar.
3. Suche und z. B. `source:gog installed:false` prüfen. „Installed only“ blendet
   nicht installierte Spiele bewusst aus. Standardmäßig ist der Filter ausgeschaltet;
   eine zuvor gewählte Einstellung wird weiterhin respektiert. Auch ausgeblendete
   Spiele und ausdrücklich ausgeschlossene Dienste bleiben ausgeblendet.
4. Ein nicht installiertes Spiel auswählen: Spielleiste und Kontextmenü sollen den
   normalen Lutris-Installer anbieten. Doppelklick installiert über die richtige
   Plattform. Ein installiertes Spiel weiterhin starten, konfigurieren und stoppen.
5. Listenansicht, Cover-Zoom, Favoriten, gespeicherte Suchen und Runner-Konfiguration
   prüfen. Kategorien beziehen sich weiterhin auf lokal registrierte Spiele.
6. Nach einer erfolgreichen Synchronisierung offline starten: gespeicherte Kataloge
   bleiben sichtbar, solange das Konto angemeldet bleibt. Fehlgeschlagene Downloads
   dürfen einen vorhandenen Katalog nicht löschen. Fehlermeldungen weiter beachten.

## Grenzen und bisherige Validierung

Die Ansicht vereinigt die Daten, die Lutris' jeweilige Anbindung tatsächlich liefern
kann. Sie fügt keine bisher nicht unterstützten Store-APIs hinzu. Insbesondere benötigt
Steams vorhandene Anbindung eine lokale Steam-Anmeldung und öffentliche Profil- und
Spieldetails während der Synchronisierung. Ein öffentliches Store-Angebot wie Flathub
wird nicht als persönliche Spielebibliothek hinzugefügt. Fehlende Cover werden mit den
vorhandenen Bannern/Icons oder dem Lutris-Platzhalter dargestellt, ohne Spiele auszublenden.
Nicht jeder Dienst stellt hochkantige Cover bereit. Anmeldung, Katalogvollständigkeit
und tatsächliche Spieleinstallation müssen mit echten Konten auf dem Zielsystem geprüft
werden; dafür wurden keine Zugangsdaten angefordert oder eingebaut.

In der Cloud wurden die echte GTK-Ansicht mit lokalen und simulierten GOG-/Epic-
Katalogeinträgen, plattformübergreifende Identitäten, Filter und Aktionsauflösung geprüft.
Die ausführbare Testsuite umfasst 687 Tests: 686 bestanden, einer übersprungen.
Ruff, Formatprüfung, Mypy (372 Python-Dateien), Meson-Build und beide Meson-Tests
waren erfolgreich. In der echten GTK-Ansicht wurden zusätzlich der Installationsfilter,
das Zurückschalten auf alle Spiele und der Wechsel zur Listenansicht geprüft.
Der Flatpak-Manifestgenerator wurde mit Tests und dem Manifestparser von
`flatpak-builder` geprüft. Das Paket wurde anschließend vollständig gebaut und aus
`dist/LutrisLibrary.flatpak` benutzerbezogen installiert. Versionsabfrage,
Datenbank-/Bibliotheksinitialisierung und Aufbau des neuen GTK-Bibliotheksfensters
wurden innerhalb von Flatpak erfolgreich geprüft. Für den GUI-Test mussten in der
minimalen Cloud-Umgebung die echten Flatpak-Sitzungsdienste vorübergehend gestartet
und ihre lokalen Programmpfade bereitgestellt werden; die Bildlade-Sandbox blieb aktiv.

Das Bundle ist für Linux x86_64, verwendet `org.gnome.Platform//49` und wurde auf
Lutris-Basiscommit
`986be5709ac3e54e4331313a40891c2007760e999c050ccd84511b9d097a1b7b`
gebaut. Die SHA-256-Prüfsumme steht in `dist/LutrisLibrary.flatpak.sha256`.
Die Flathub-Freigabe der Cloud ist inzwischen wirksam; der vorherige HTTP-403-Blocker
besteht für den Paketbau nicht mehr.

Zusätzlich fehlt dieser Cloud-Laufzeit `/proc/<pid>/task/<tid>/children`.
Die vorhandenen Prozess-Wrapper-Tests hängen deshalb; sie wurden nicht als bestanden
gewertet. Die Dialogtests sind wie im bestehenden CI ausgeschlossen. Das ersetzt
keinen Spiele- und Kontotest auf einem normalen Linux-Desktop.

Entfernen der Vorschau (Konfigurationsdaten bleiben zunächst erhalten):

```sh
flatpak uninstall --user io.github.MarvinFuhr.LutrisLibrary
```
