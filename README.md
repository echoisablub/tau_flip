# τ-Messung des SLM

Wie schnell schwingt der SLM nach einem Grauwert-Sprung auf den neuen Wert ein, und wie hängt das von Temperatur und LUT-Offset ab?

**Kurz gesagt:** Bei 50 °C sind große Sprünge bei Offset 0 rund 1,3- bis 3-mal schneller als bei 25 °C. Sprünge nach oben werden mit steigendem Offset langsamer, Sprünge nach unten deutlich weniger. Kleine Sprünge bis rund 24 Grau sind noch nicht belastbar. 75 °C folgt.

## Inhalt

- [Ergebnisse](#ergebnisse)
- [Was wurde gemessen?](#was-wurde-gemessen)
- [So liest du ein Feld im Fit-Plot](#so-liest-du-ein-feld-im-fit-plot)
- [Warum die Kurven so verschieden aussehen](#warum-die-kurven-so-verschieden-aussehen)
- [Grenzen der Messung](#grenzen-der-messung)
- [Dateien](#dateien)

## Ergebnisse

τ in ms, Fit über den Mittelwert aus 3 Wiederholungen. Die Tabellen enthalten nur große Sprünge, weil sie am besten reproduzierbar sind. Kursive Werte sind als unsicher markiert, weil τ für das Fitfenster von rund 8 ms zu lang ist.

### 25 °C

| Sprung | Richtung | Offset 0 | Offset 50 | Offset 100 | Offset 150 |
|---|---|---:|---:|---:|---:|
| `16 → 240` | hoch | 0,52 | 0,74 | 1,29 | 3,30 |
| `48 → 208` | hoch | 1,01 | 1,21 | 1,79 | 3,58 |
| `0 → 127` | hoch | 2,77 | 3,52 | 2,95 | 4,35 |
| `4 → 126` | hoch | 2,74 | 3,55 | 2,82 | 4,06 |
| `240 → 16` | runter | 3,39 | 3,22 | 3,33 | 4,36 |
| `208 → 48` | runter | 2,84 | 3,07 | 2,85 | *6,03* |
| `127 → 0` | runter | 2,72 | 2,73 | 3,14 | *6,22* |

### 50 °C (Sollwert)

| Sprung | Richtung | Offset 0 | Offset 50 | Offset 100 | Offset 150 |
|---|---|---:|---:|---:|---:|
| `16 → 240` | hoch | 0,40 | 0,33 | 0,48 | 1,05 |
| `48 → 208` | hoch | 0,42 | 0,50 | 0,63 | 1,31 |
| `0 → 127` | hoch | 0,96 | 1,15 | 1,48 | 2,62 |
| `4 → 126` | hoch | 1,00 | 1,13 | 1,59 | 2,84 |
| `240 → 16` | runter | 1,36 | 1,48 | 1,89 | 1,91 |
| `208 → 48` | runter | 1,61 | 1,60 | 1,91 | 1,68 |
| `127 → 0` | runter | 1,63 | 1,62 | 1,47 | 1,65 |

### Was man daraus ablesen kann

- **Temperatur:** Bei Offset 0 sind die Sprünge dieser Tabellen bei 50 °C rund 1,3- bis 3-mal schneller als bei 25 °C, zum Beispiel `240 → 16` mit 3,39 → 1,36 ms.
- **Offset, Sprünge nach oben:** Sie werden mit dem Offset langsamer. Bei 25 °C wird `16 → 240` von Offset 0 bis 150 um den Faktor 6 langsamer, bei 50 °C rund um den Faktor 2,6.
- **Offset, Sprünge nach unten:** Sie hängen weniger vom Offset ab. Bei 25 °C bleiben sie bis Offset 100 fast gleich, bei 50 °C ändern sie sich nur wenig.
- **Richtung:** Bei kleinem Offset sind die größten Sprünge nach oben deutlich schneller als nach unten, bei 25 °C und Offset 0 zum Beispiel `16 → 240` mit 0,52 ms gegen `240 → 16` mit 3,39 ms.

### Reproduzierbarkeit

Spannweite von τ zwischen 3 Wiederholungen, Median je Sprunggröße, jeweils über die Offsets 0, 50, 100 und 150:

| Sprunggröße (Grau) | 25 °C | 50 °C |
|---:|---|---|
| bis 8 | 58 / 74 / 58 / 76 % | 52 / 84 / 151 / 90 % |
| 16 | 34 / 28 / 16 / 53 % | 29 / 31 / 39 / 101 % |
| 24 | 29 / 27 / 50 / 45 % | 25 / 16 / 40 / 68 % |
| 25–64 | 27 / 11 / 5 / 16 % | 15 / 39 / 37 / 20 % |
| 65–127 | 3 / 4 / 3 / 18 % | 9 / 12 / 15 / 4 % |
| über 127 | 3 / 1 / 3 / 3 % | 2 / 11 / 10 / 7 % |

### Phasenhub und Stabilität

Gemessen mit einem Gray-Scan: gleichmäßige Grauwerte, eingeschwungenes Signal geteilt durch die Ref-Diode.

| Prüfung | 25 °C | 50 °C |
|---|---|---|
| Phasenhub Offset 0 | rund 2,18π | rund 2,37π |
| Phasenhub Offset 150 | rund 2,03π | rund 2,07π |
| Offset 0 zweimal geladen, Abweichung | 0,7 % | 1,4 % |
| Offset 150 gegen 0, aufgetragen gegen die Spannung | 1,8 % | 2,5 % |
| Offset 150 gegen 0, aufgetragen gegen den Grauwert | 67 % | 63 % |
| Kennlinie am Anfang und Ende der Messung | nicht gemessen | 1,7 % Änderung in 23 Minuten |

Dass die Kurven beider Offsets gegen die Spannung fast aufeinanderliegen, gegen den Grauwert aber nicht, zeigt: Die geladenen LUTs sind tatsächlich aktiv.

## Was wurde gemessen?

| Punkt | Wert |
|---|---|
| **Temperaturen** | 25 °C, 50 °C (Sollwert, die echte Temperatur wurde nicht ausgelesen), 75 °C folgt |
| **LUT-Offsets** | 0, 50, 100, 150, jeweils mit dem LUT zur Temperatur |
| **Wiederholungen** | 3 pro Offset, gemittelt |
| **Ablauf** | 39 Grauwert-Blöcke mit je 13 Frames (rund 9 ms), aufgeteilt auf 3 Shots mit 127, 136 und 136 ms, also 9 Shots pro Offset |
| **Ausgewertete Sprünge** | 38 |
| **Große Sprünge** | 16 ↔ 240, 48 ↔ 208 |
| **Mittlere Sprünge** | ±32, 64, 127 Grau um Grau 64 |
| **Kleine Sprünge** | ±4, 8, 16, 24 Grau um Grau 16 und 128 |
| **Zwischenschritte** | Sprünge von einem Paar zum nächsten |
| **Signale** | CH1 Frame-Trigger, CH2 PD hinter dem PBS, CH3 Ref-Diode |
| **Ergebnis pro Sprung** | τ, Verzögerung, Sprunghöhe in mV, Qualität |

**Auswertung:** Von beiden Dioden wird der Dunkelwert abgezogen, dann wird das Signal durch die Ref geteilt. Der Fit enthält Terme für den Ripple bei 718 und 1436 Hz. In den Plots ist der Ripple aus Messung und Fit herausgerechnet.

## So liest du ein Feld im Fit-Plot

Beispiel: [`25° C/tau_25C_O000_fits.png`](25%C2%B0%20C/tau_25C_O000_fits.png)

| Element | Bedeutung |
|---|---|
| **Titel**, z. B. `0 → 127` | Der SLM springt von Grau 0 auf Grau 127 |
| **Zusatz**, z. B. `wrap`, `step4@16`, `extra` | Art des Sprungs: `step4@16` sind 4 Grau um Grau 16, `extra` ist der Übergang zum nächsten Paar |
| **x-Achse** | Zeit seit dem Trigger: Bei 0 ms kommt der neue Frame |
| **y-Achse** | PD-Signal, mit der Ref auf konstantes Licht korrigiert. **Jedes Feld hat seine eigene Skala**, kleine Sprünge sehen also größer aus, als sie sind |
| **Graue Linie** | Messung, gemittelt über 3 Wiederholungen |
| **Blaue Linie** | Fit |
| **τ** | Zeitkonstante der Phase: Nach τ sind noch rund 37 % des Wegs übrig, nach 3τ noch rund 5 % |
| **Roter Titel** | Fit nicht nutzbar, der Grund steht in Klammern |

## Warum die Kurven so verschieden aussehen

Die PD misst nicht die Phase direkt, sondern die Intensität hinter dem PBS, und die läuft mit der Phase wie ein Cosinus² auf und ab. Die Phase selbst läuft dabei gleichmäßig zum neuen Wert, aber die Intensität kann unterwegs über ein Maximum oder Minimum laufen. Bei 25 °C und Offset 0 liegt das Maximum etwa bei Grau 70 und das Minimum etwa bei Grau 183.

| Form | Beispiel | Was passiert |
|---|---|---|
| **Einfacher Anstieg oder Abfall** | `4 → 28`, `140 → 116` | Die Phase bleibt auf einer Flanke, die Kurve sieht aus wie eine e-Funktion |
| **Buckel** | `0 → 127`, `127 → 0` | Die Phase läuft über das Maximum: erst hoch, dann wieder runter |
| **Delle** | `240 → 16`, `48 → 208` | Die Phase läuft durch das Minimum |
| **Delle und Anstieg, sehr schnell** | `16 → 240` | Fast der ganze Bereich wird durchlaufen, danach pendelt das Signal rasch ein |

Der Buckel bei `127 → 0` ist also kein Überschwingen des SLM, sondern die Phase, die auf ihrem Weg das Maximum passiert. Genau das berücksichtigt der Fit.

## Grenzen der Messung

- **Kleine Sprünge sind noch nicht belastbar:** Ein Offset-Trend lässt sich aus ihnen nicht ablesen, auch wenn der Titel im Plot schwarz ist. Maßgeblich ist die Tabelle zur Reproduzierbarkeit.
- **Temperatur:** Das Display zeigt nur den Sollwert. Die echte Temperatur des SLM wurde nicht ausgelesen. Dass der SLM sich verändert hat, zeigt die verschobene Kennlinie.
- **Phasenhub:** Der Fit nimmt genau 2π an. Gemessen wurde bis zu rund 2,37π bei Offset 0 und 50 °C, dort passt die Fitkurve bei den größten Sprüngen sichtbar weniger gut. Die Offsets 50 und 100 sind ungeprüft.
- **Ripple:** Das Signal schwingt bei der halben Frame-Rate (718 Hz) und bei der Frame-Rate (1436 Hz), im Mittel über 3 Wiederholungen bei 25 °C und Offset 0 mit rund 0,6 und 0,5 mV (bei rund 170 mV Maximum). Der Fit entfernt das, die Streuung von τ ändert sich dadurch aber kaum. Der Ripple ist also nicht die Hauptursache dafür.
- **Lichtabfall:** Die Lichtleistung fällt im Shot, weil die Phaser-Kopplung heiß wird: Nach 160 ms sind noch rund 58 % übrig. Die Ref-Diode korrigiert das, aber später im Shot gibt es trotzdem weniger Signal.
- **Fitfenster:** Mit 13 Frames pro Block sind nur rund 8 ms auswertbar. Für τ über rund 4 ms ist das zu kurz, solche Fits sind rot markiert.
- **Grenze im Plot:** „Sprung zu klein“ gilt unter 15 mV. Das ist eine eigene Festlegung, passend zum Signal dieser Messung.
- **Licht:** Alle τ-Messungen hier liefen mit rund 170 mV Maximum auf der PD. Ein früherer Sweep mit weniger Licht und einem langen Shot ist nicht enthalten.

## Dateien

| Pfad | Inhalt |
|---|---|
| [`25° C/`](25%C2%B0%20C/) | Ergebnisse 25 °C: pro Offset `.csv`, `.png` und `_fits.png` |
| [`50° C/`](50%C2%B0%20C/) | Ergebnisse 50 °C, gleiche Struktur |
| [`lut_checks/`](lut_checks/) | Gray-Scans: Phasenhub und Kennlinien (`lut_check` für 25 °C, `lut_check_50C` für 50 °C, `lut_check_50C_drift` für Anfang gegen Ende) |
| `tau_flip_labscript.py`, `tau_schedule.py` | Shot und Grauwert-Abfolge |
| `tau_analyse.py` | Auswertung und Fit |
| `tau_scope_csv.py` | Scope scharf stellen und Trace als CSV speichern |
| `gray_scan_labscript.py`, `gray_scan_schedule.py`, `gray_scan_analyse.py` | Gray-Scan: Shot, Abfolge, Auswertung |
| [`blacs_plugin/tau_scope/`](blacs_plugin/tau_scope/) | BLACS-Plugin, das pro Shot das Scope auslöst und speichert |
| [`measurement/`](measurement/) | Abläufe für die Messreihen. Die Pfade darin sind auf den Laborrechner zugeschnitten |
