# τ-Messung des SLM bei 25 °C

Wie schnell schwingt der SLM nach einem Grauwert-Sprung auf den neuen Wert ein, und wie hängt das vom LUT-Offset ab?

## Inhalt

- [Was wurde gemessen?](#was-wurde-gemessen)
- [So liest du ein Feld im Fit-Plot](#so-liest-du-ein-feld-im-fit-plot)
- [Warum die Kurven so verschieden aussehen](#warum-die-kurven-so-verschieden-aussehen)
- [Was du daraus ablesen kannst](#was-du-daraus-ablesen-kannst)

## Was wurde gemessen?

| Punkt | Wert |
|---|---|
| **Temperatur** | 25 °C |
| **LUT-Offsets** | 0, 50, 100, 150 |
| **Shots pro Offset** | 3, gemittelt |
| **Ablauf pro Shot** | 39 Grauwert-Blöcke mit je 13 Frames (rund 9 ms), zusammen 507 Frames, 353 ms |
| **Ausgewertete Sprünge** | 38 |
| **Große Sprünge** | 16 ↔ 240, 48 ↔ 208 |
| **Kleine Sprünge** | ±4, 8, 16, 24 Grau um Grau 16 und 128 |
| **Mittlere Sprünge** | ±32, 64, 127 Grau um Grau 64 |
| **Zwischenschritte** | Sprünge von einem Paar zum nächsten |
| **Signale** | CH1 Frame-Trigger, CH2 PD hinter dem PBS, CH3 Ref-Diode |
| **Ergebnis pro Sprung** | τ, Verzögerung, Sprunghöhe in mV, Qualität |

> **Zwei Messvarianten:** Die Tabelle beschreibt den ersten Sweep mit einem langen Shot (Ordner `0018` bis `0021`).
> Der Plot unten und die τ-Werte in diesem Dokument stammen aus der Wiederholung (Ordner `0023` bis `0026` für Offset 0, 50, 100, 150): dieselben 38 Sprünge, aber auf 3 Shots mit 127, 136 und 136 ms verteilt, 3 Wiederholungen (9 Shots pro Offset) und doppeltes Licht. Der Fit enthält hier zusätzlich den Dunkelabzug und einen 718-Hz-Term.

## So liest du ein Feld im Fit-Plot

Plot für Offset 0: [`0023/tau_25C_O000_fits.png`](0023/tau_25C_O000_fits.png)

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

Die PD misst nicht die Phase direkt, sondern die Intensität hinter dem PBS, und die läuft mit der Phase wie ein Cosinus² auf und ab. Die Phase selbst läuft dabei gleichmäßig zum neuen Wert, aber die Intensität kann unterwegs über ein Maximum oder Minimum laufen. Bei Offset 0 liegt das Maximum etwa bei Grau 70 und das Minimum etwa bei Grau 183.

| Form | Beispiel | Was passiert |
|---|---|---|
| **Einfacher Anstieg oder Abfall** | `4 → 28`, `140 → 116` | Die Phase bleibt auf einer Flanke, die Kurve sieht aus wie eine e-Funktion |
| **Buckel** | `0 → 127`, `127 → 0` | Die Phase läuft über das Maximum: erst hoch, dann wieder runter |
| **Delle** | `240 → 16`, `48 → 208` | Die Phase läuft durch das Minimum |
| **Delle und Anstieg, sehr schnell** | `16 → 240` | Fast der ganze Bereich wird durchlaufen, danach pendelt das Signal rasch ein |

Der Buckel bei `127 → 0` ist also kein Überschwingen des SLM, sondern die Phase, die auf ihrem Weg das Maximum passiert. Genau das berücksichtigt der Fit.

## Was du daraus ablesen kannst

- **Große Sprünge sind am zuverlässigsten:** Messung und Fit liegen fast perfekt übereinander, und die Wiederholungen stimmen auf wenige Prozent überein.
- **Richtung macht einen großen Unterschied:** `16 → 240` braucht 0,53 ms, `240 → 16` aber 3,39 ms. `48 → 208` braucht 1,01 ms, zurück sind es 2,84 ms. Nach oben (höhere Spannung) geht es also deutlich schneller.
- **Typischer Wert:** Viele Sprünge liegen bei rund 2–3 ms. Wegen der großen Streuung sind die kleinen davon aber noch mit Vorsicht zu lesen.

## Ergebnisse bei 25 °C

τ in ms, Fit über den Mittelwert aus 3 Wiederholungen. Die Tabelle enthält nur große Sprünge, die bei den meisten Offsets gut reproduzierbar sind.

| Sprung | Richtung | Offset 0 | Offset 50 | Offset 100 | Offset 150 |
|---|---|---:|---:|---:|---:|
| `16 → 240` | hoch | 0,53 | 0,74 | 1,29 | 3,30 |
| `48 → 208` | hoch | 1,01 | 1,21 | 1,80 | 3,58 |
| `0 → 127` | hoch | 2,79 | 3,55 | 2,94 | 4,35 |
| `4 → 126` | hoch | 2,79 | 3,59 | 2,82 | 4,05 |
| `240 → 16` | runter | 3,39 | 3,22 | 3,33 | 4,36 |
| `208 → 48` | runter | 2,84 | 3,07 | 2,85 | *6,03* |
| `127 → 0` | runter | 2,70 | 2,72 | 3,14 | *6,20* |

Kursive Werte sind als unsicher markiert, weil τ für das Fitfenster von rund 8 ms zu lang ist.

- **Große Sprünge nach oben** werden mit steigendem Offset deutlich langsamer: `16 → 240` um den Faktor 6, `48 → 208` um den Faktor 3,5.
- **Große Sprünge nach unten** bleiben bis Offset 100 fast gleich und werden erst bei Offset 150 langsamer.
- **Reproduzierbarkeit:** Die Sprünge über 127 Grau streuen zwischen den Wiederholungen um rund 1–3 %, die von 65 bis 127 Grau bei Offset 0 bis 100 um rund 3–4 %, bei Offset 150 um rund 18 %.

## Grenzen der Messung

- **Kleine Sprünge sind noch nicht belastbar:** Bei Sprüngen bis 8 Grau streut τ zwischen den Wiederholungen meist um mehr als 50 %, bei 16 bis 64 Grau typisch um 10–50 %. Ein Offset-Trend lässt sich daraus nicht ablesen, auch wenn der Titel im Plot schwarz ist.
- **Ripple bei 718 Hz:** Das Signal schwingt bei der halben Frame-Rate, bei Offset 0 mit typisch rund 1,6 mV Amplitude im Einzelshot und rund 0,65 mV im Mittel über 3 Wiederholungen (bei rund 170 mV Maximum). Der Fit berücksichtigt das. Das Restrauschen halbiert sich dadurch, die Streuung von τ wird aber nur bei Sprüngen bis 8 Grau kleiner.
- **Lichtabfall:** Die Lichtleistung fällt im Shot, weil die Phaser-Kopplung heiß wird: Nach 160 ms sind noch rund 58 % übrig. Die Ref-Diode korrigiert das, aber später im Shot gibt es trotzdem weniger Signal.
- **Fitfenster:** Mit 13 Frames pro Block sind nur rund 8 ms auswertbar. Für τ über rund 4 ms ist das zu kurz, solche Fits sind rot markiert.
- **Phasenhub:** Der Fit nimmt genau 2π an. Gemessen wurden rund 2,18π bei Offset 0 und rund 2,03π bei Offset 150, die Offsets 50 und 100 sind ungeprüft (Plot: [`../../../../gray_scan_csv/2026/11/05/lut_check.png`](../../../../gray_scan_csv/2026/11/05/lut_check.png)).

## Dateien

| Offset | Ordner | Ergebnisse | Fit-Plot |
|---:|---|---|---|
| 0 | `0023` | [`tau_25C_O000.csv`](0023/tau_25C_O000.csv) | [`tau_25C_O000_fits.png`](0023/tau_25C_O000_fits.png) |
| 50 | `0024` | [`tau_25C_O050.csv`](0024/tau_25C_O050.csv) | [`tau_25C_O050_fits.png`](0024/tau_25C_O050_fits.png) |
| 100 | `0025` | [`tau_25C_O100.csv`](0025/tau_25C_O100.csv) | [`tau_25C_O100_fits.png`](0025/tau_25C_O100_fits.png) |
| 150 | `0026` | [`tau_25C_O150.csv`](0026/tau_25C_O150.csv) | [`tau_25C_O150_fits.png`](0026/tau_25C_O150_fits.png) |

In diesen Dateien gilt eine Grenze von 15 mV für „Sprung zu klein“, passend zum höheren Signal. Der erste Sweep mit einem langen Shot liegt in `0018` bis `0021` und ist dort ohne Dunkelabzug ausgewertet.
