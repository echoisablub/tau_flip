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
> Der Plot unten und die τ-Werte in diesem Dokument stammen aus der Wiederholung bei Offset 0 (Ordner `0023`): dieselben 38 Sprünge, aber auf 3 Shots mit 127, 136 und 136 ms verteilt, 3 Wiederholungen (9 Shots) und doppeltes Licht.

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
- **Richtung macht einen großen Unterschied:** `16 → 240` braucht 0,53 ms, `240 → 16` aber 3,40 ms. `48 → 208` braucht 1,02 ms, zurück sind es 2,84 ms. Nach oben (höhere Spannung) geht es also deutlich schneller.
- **Typischer Wert:** Viele Sprünge liegen bei rund 2–3 ms. Wegen der großen Streuung sind die kleinen davon aber noch mit Vorsicht zu lesen.
