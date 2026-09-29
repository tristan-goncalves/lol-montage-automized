"""Zooms sur le HUD (1,5 s) : kill feed pendant la phase de lane, et zoom KDA.

Kill feed : pendant les 10 premières minutes de jeu, chaque kill d'équipe (lu sur le HUD) où Tristan n'est
pas impliqué (pas de kill / mort / assist à lui à ±10 s) donne un zoom sur la colonne des kills à droite
(entre le score et la minimap). Au plus un zoom toutes les 30 s.
Sorties : habillage/killfeed_<t>.mov (transparents) et habillage/killfeed.json (éléments d'habillage,
positions en secondes source, repris par 08_construction).
Usage : python scripts/zooms_hud.py "<vidéo>" [--kda 1719]
"""
import subprocess
import sys

from commun import Travail, argument_video

t = Travail(argument_video())
cfg = t.cfg.get("zooms", {})
DUREE = cfg.get("duree_s", 1.5)
PHASE_LANE = cfg.get("phase_lane_s", 600) - cfg.get("decalage_horloge_s", 12)  # horloge de jeu -> temps vidéo
ECART = cfg.get("ecart_min_s", 30)
# zoom ×1,5 collé au bord droit, par-dessus le kill feed d'origine (retour 29/09 : ×2 trop gros, trop loin du bord)
KF = cfg.get("killfeed", {"x": 1700, "y": 225, "l": 220, "h": 120, "zoom": 1.5, "px": 1574, "py": 212})
KDA = cfg.get("kda", {"x": 1652, "y": 0, "l": 100, "h": 34, "zoom": 3, "px": 1604, "py": 40})
evts = t.lire("analyse/evenements.json")


def zoom(t0, crop, sortie):
    x, y, l, h, z, px, py = (crop[k] for k in ("x", "y", "l", "h", "zoom", "px", "py"))
    L, H = int(round(l * z)), int(round(h * z))
    graphe = (f"[0:v]crop={l}:{h}:{x}:{y},scale={L}:{H}:flags=lanczos,format=rgba,"
              f"drawbox=x=0:y=0:w={L}:h={H}:color=black@0.55:t=2,drawbox=x=2:y=2:w={L - 4}:h={H - 4}:color=white@0.28:t=1,"  # cadre discret
              f"fade=t=in:st=0:d=0.15:alpha=1,fade=t=out:st={DUREE - 0.2:.2f}:d=0.2:alpha=1,"
              f"pad=1920:1080:{px}:{py}:color=black@0,format=argb[v]")  # pad garde l'alpha (overlay le perdait)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t0:.2f}", "-t", f"{DUREE}", "-i", str(t.video),
                    "-filter_complex", graphe, "-map", "[v]", "-t", f"{DUREE}", "-c:v", "qtrle", "-pix_fmt", "argb",
                    str(sortie)], check=True)


perso = [e["debut"] for e in evts if e["type"] in ("kill", "mort", "assist")]
choisis = []
for e in sorted(evts, key=lambda e: e["debut"]):
    if e["type"] not in ("kill_equipe", "kill_ennemi") or e["debut"] > PHASE_LANE:
        continue
    if any(abs(e["debut"] - p) <= 10 for p in perso):
        continue
    if choisis and e["debut"] - choisis[-1] < ECART:
        continue
    choisis.append(e["debut"])

elements = []
for s in choisis:
    # le HUD est lu toutes les 5 s : à la lecture, le kill a eu lieu dans les 5 s d'avant et reste affiché ~8 s
    t0 = next(e["fin"] for e in evts if e["debut"] == s) + 0.5
    f = t / f"habillage/killfeed_{int(s)}.mov"
    zoom(t0, KF, f)
    elements.append({"nom": f"killfeed_{int(s)}", "piste": "V2", "fichier": f"habillage/killfeed_{int(s)}.mov",
                     "src_s": t0, "duree_s": DUREE, "optionnel": True})
t.ecrire("habillage/killfeed.json", elements)
print(f"{len(elements)} zooms kill feed :", [e["src_s"] for e in elements])

if "--kda" in sys.argv:
    s = float(sys.argv[sys.argv.index("--kda") + 1])
    zoom(s, KDA, t / "habillage/zoom_kda_v3.mov")
    print("zoom KDA :", s)
