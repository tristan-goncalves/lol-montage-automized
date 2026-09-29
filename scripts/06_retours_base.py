"""Retours à la base (« backs ») : repérés sur la minimap, d'après le rectangle blanc de la caméra.

On ne décode que les images clés (une toutes les ~4 s chez OBS), ce qui prend moins d'une minute.
Quand le rectangle arrive d'un coup dans le coin de ta fontaine, c'est un rappel (téléportation) ;
le back va de ~9 s avant l'arrivée (canalisation du rappel) jusqu'au moment où la caméra est
revenue loin de la base (retour en lane).
Sorties : analyse/minimap.json (position caméra par image clé) et analyse/retours_base.json.
Usage : python scripts/06_retours_base.py "<vidéo.mp4>"
"""
import json
import subprocess
import sys

import numpy as np

from commun import Travail, argument_video

t = Travail(argument_video())
cfg = t.cfg.get("retours_base", {})
X, Y, T = cfg.get("minimap", [1620, 780, 300])          # zone de la minimap en 1080p (x, y, côté)
RAPPEL_S = cfg.get("canalisation_s", 9.0)                # le rappel dure 8 s, + marge
LOIN_FONTAINE = cfg.get("distance_retour_lane", 105)     # px (dans la minimap) : sorti de la base
PRES_FONTAINE = cfg.get("distance_fontaine", 55)         # px : à la fontaine
SAUT = cfg.get("saut_min", 70)                           # px : la caméra « saute » (téléportation)

# 1) Images clés de la minimap, en niveaux de gris, 1 octet par pixel
cmd = ["ffmpeg", "-nostats", "-v", "info", "-skip_frame", "nokey", "-i", str(t.video), "-an",
       "-vf", f"crop={T}:{T}:{X}:{Y},format=rgb24,showinfo", "-vsync", "0",
       "-f", "rawvideo", "-"]
p = subprocess.run(cmd, capture_output=True)
brut = np.frombuffer(p.stdout, np.uint8).reshape(-1, T, T, 3)
temps = [float(x.split(":")[1]) for x in p.stderr.decode(errors="ignore").split() if x.startswith("pts_time:")]
n = min(len(temps), len(brut))


def camera(im):
    """Centre du rectangle blanc de la caméra (None si introuvable)."""
    blanc = (im.min(axis=2) > 225)
    lignes = np.where(blanc.sum(axis=1) >= 35)[0]     # bords haut/bas : longues lignes horizontales
    cols = np.where(blanc.sum(axis=0) >= 25)[0]       # bords gauche/droit
    if len(lignes) == 0 and len(cols) == 0:
        return None
    if len(lignes):
        xs = np.where(blanc[lignes[0]])[0]
        cx = (xs.min() + xs.max()) / 2
    else:
        cx = cols.mean()
    if len(cols):
        ys = np.where(blanc[:, cols[0]])[0]
        cy = (ys.min() + ys.max()) / 2
    else:
        cy = lignes.mean()
    return float(cx), float(cy)


pos = [[round(temps[i], 2), camera(brut[i])] for i in range(n)]

# 2) Coin de la fontaine : la position la plus extrême où la caméra reste souvent (coin haut droit ou bas gauche)
pts = np.array([c for _, c in pos if c])
coins = {"haut_droit": (T - 30, 25), "bas_gauche": (30, T - 25)}
compte = {k: int(np.sum(np.hypot(pts[:, 0] - a, pts[:, 1] - b) < PRES_FONTAINE)) for k, (a, b) in coins.items()}
coin = max(compte, key=compte.get)
fx, fy = coins[coin]


def dist(c):
    return None if c is None else float(np.hypot(c[0] - fx, c[1] - fy))


# 3) Arrivées par téléportation (rappel, ou réapparition après une mort), puis sortie de base
morts = t.lire("analyse/morts.json")["morts"] if (t / "analyse/morts.json").exists() else []
retours = []
i = 1
while i < len(pos):
    d, dp = dist(pos[i][1]), dist(pos[i - 1][1])
    if d is not None and d < PRES_FONTAINE and dp is not None and dp - d > SAUT and pos[i][0] > 60:
        arrivee = pos[i][0]
        j = i
        while j < len(pos) and (dist(pos[j][1]) is None or dist(pos[j][1]) < LOIN_FONTAINE):
            j += 1
        sortie = pos[min(j, len(pos) - 1)][0]
        mort = any(a - 5 <= arrivee <= b + 10 for a, b in morts)
        retours.append({"type": "reapparition" if mort else "rappel", "debut": round(arrivee - RAPPEL_S, 2), "arrivee": arrivee,
                        "fin": round(sortie, 2), "duree": round(sortie - arrivee + RAPPEL_S, 1)})
        i = j
    i += 1

t.ecrire("analyse/minimap.json", {"coin_fontaine": coin, "positions": pos})
t.ecrire("analyse/retours_base.json", retours)
print(f"{n} images clés, fontaine {coin}, {len(retours)} retours à la base :")
for r in retours:
    print(f"  {r['type']:12s} {r['debut']:7.1f} -> {r['fin']:7.1f}  ({r['duree']} s)")
