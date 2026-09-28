"""Contrôle du mix sur un rendu : volume momentané toutes les 0,5 s et alertes.

Sert à vérifier objectivement qu'aucun effet sonore ou passage de musique ne passe au-dessus de ta voix.
Référence voix = médiane des passages les plus forts (la voix domine le mix).
Alerte si une tranche dépasse la référence de plus de 3 dB, ou si la musique seule (passages sans voix)
est à moins de 12 dB sous la voix.

Usage : python scripts/controle_audio.py "<rendu.mp4>"
"""
import re
import subprocess
import sys

import numpy as np

if len(sys.argv) < 2:
    sys.exit("Usage : python scripts/controle_audio.py <rendu.mp4>")
err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", sys.argv[1], "-vn", "-af", "ebur128=peak=true",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
lignes = re.findall(r"t:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+)", err)
if not lignes:
    sys.exit("Aucune mesure : le fichier a-t-il une piste audio ?")
t = np.array([float(a) for a, _ in lignes])
m = np.array([float(b) for _, b in lignes])
tranches = {}
for tt, v in zip(t, m):
    k = round(int(tt * 2) / 2, 1)
    tranches[k] = max(tranches.get(k, -99), v)
cles = sorted(tranches)
vals = np.array([tranches[k] for k in cles])
actif = vals[vals > -45]
ref = float(np.median(actif[actif >= np.percentile(actif, 50)])) if len(actif) else -20
integre = re.search(r"I:\s+(-?[\d.]+) LUFS", err[err.rfind("Summary:"):])

print(f"Volume intégré : {integre.group(1) if integre else '?'} LUFS — référence voix ≈ {ref:.0f} LUFS (momentané)")
print("Profil (seconde:volume) :", " ".join(f"{k:.1f}:{tranches[k]:.0f}" for k in cles))
trop = [k for k in cles if tranches[k] > ref + 3]
if trop:
    print(f"⚠ {len(trop)} tranche(s) au-dessus de la voix de plus de 3 dB : " + ", ".join(f"{k:.1f}s" for k in trop[:30]))
else:
    print("✓ Aucun passage ne dépasse la voix de plus de 3 dB")
calmes = vals[(vals < ref - 6) & (vals > -60)]
if len(calmes) and np.median(calmes) > ref - 12:
    print(f"⚠ Les passages sans voix sont à {ref - np.median(calmes):.0f} dB sous la voix (cible ≥ 12 dB) : musique trop forte ?")
