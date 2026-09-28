"""Étape 3 — Analyser la partie : volume du jeu et du micro, morts (écran gris), écrans noirs,
lecture du HUD (KDA, kills d'équipe) pour dater les kills, morts et assists.

Travaille PAR TRANCHES et reprend où il s'est arrêté : relance le script tant qu'il affiche
« À RELANCER » (utile quand une commande est limitée dans le temps, comme dans Cowork).

Sorties : analyse/volume.json, analyse/morts.json, analyse/noirs.json, analyse/hud.json, analyse/evenements.json
Usage : python scripts/03_analyser_jeu.py "<vidéo.mp4>" [--budget 150] [--sans-hud]
"""
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from commun import Travail, argument_video, ffmpeg, tc

DEBUT = time.time()
BUDGET = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 150
SANS_HUD = "--sans-hud" in sys.argv
t = Travail(argument_video())
cfg = t.cfg
duree = t.infos()["duree_s"]
PAS = cfg["mesures"]["pas_rms_s"]
FPS_A = cfg["mesures"]["fps_analyse_image"]
PAS_HUD = cfg["mesures"]["pas_hud_s"]
TRANCHE = 60  # secondes de vidéo par passage ffmpeg


def reste():
    return BUDGET - (time.time() - DEBUT)


# ---------- 1. Volume par tranche de 0,5 s (rapide) ----------
def volume_db(wav: Path) -> list[float]:
    sr = 8000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = int(sr * PAS)
    x = x[: len(x) // n * n].reshape(-1, n)
    return [round(float(v), 1) for v in 20 * np.log10(np.sqrt((x ** 2).mean(axis=1)) + 1e-9)]


if not (t / "analyse/volume.json").exists():
    t.ecrire("analyse/volume.json", {"pas_s": PAS, "jeu": volume_db(t / "audio/jeu.wav"),
                                     "micro": volume_db(t / "audio/micro.wav")})
    print("Volume mesuré")

# ---------- 2. Passage image par tranches : saturation, écrans noirs, HUD ----------
etat_f = t / "analyse/_image_partiel.json"
etat = t.lire("analyse/_image_partiel.json") if etat_f.exists() else {"fait_jusqua": 0.0, "sat": [], "noirs": [], "hud": []}
z = cfg["hud"]["zone"]
if not SANS_HUD:
    import cv2

    from hud_ocr import charger_modeles, lire_hud
    MODELES_HUD = charger_modeles()
    (t / "analyse/hud_images").mkdir(exist_ok=True)


duree_tranche_mesuree = None
while etat["fait_jusqua"] < duree - 0.5:
    if duree_tranche_mesuree and reste() < duree_tranche_mesuree * 1.3:
        break
    t0 = time.time()
    s = etat["fait_jusqua"]
    d = min(TRANCHE, duree - s)
    with tempfile.TemporaryDirectory() as tmp:
        graphe = (f"[0:v]fps={FPS_A},scale=320:-1,split[a][n];"
                  f"[a]signalstats,metadata=print:key=lavfi.signalstats.SATAVG[a2];"
                  f"[n]blackdetect=d=0.5:pix_th=0.08[n2]")
        sorties = ["-map", "[a2]", "-f", "null", "-", "-map", "[n2]", "-f", "null", "-"]
        if not SANS_HUD:
            graphe += f";[0:v]fps=1/{PAS_HUD},crop={z['l']}:{z['h']}:{z['x']}:{z['y']}[h]"
            sorties += ["-map", "[h]", f"{tmp}/h_%05d.png"]
        r = ffmpeg("-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", str(t.video), "-an", "-filter_complex", graphe, *sorties,
                   capture=True)
        sat = [float(v) for v in re.findall(r"SATAVG=([\d.]+)", r.stderr)]
        etat["sat"] += [[round(s + i / FPS_A, 2), v] for i, v in enumerate(sat)]
        etat["noirs"] += [[s + float(a), s + float(b)] for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]
        if not SANS_HUD:
            for i, p in enumerate(sorted(Path(tmp).glob("h_*.png"))):
                tt = round(s + i * PAS_HUD, 1)
                im = cv2.imread(str(p))
                cv2.imwrite(str(t / f"analyse/hud_images/{int(tt):05d}.png"), im)  # gardé pour relire si besoin
                etat["hud"].append({"t": tt, **lire_hud(im, MODELES_HUD, cfg["hud"]["champs"])})
    etat["fait_jusqua"] = s + d
    t.ecrire("analyse/_image_partiel.json", etat)
    duree_tranche_mesuree = time.time() - t0

if etat["fait_jusqua"] < duree - 0.5:
    print(f"À RELANCER : image analysée jusqu'à {tc(etat['fait_jusqua'])} sur {tc(duree)}")
    sys.exit(0)

# ---------- 3. Morts ----------
# L'écran devient gris quand tu es mort. La saturation seule est trompeuse (certaines zones de la carte
# sont ternes), donc on part des morts lues dans le KDA et on mesure leur durée avec la saturation.
# Sans HUD (ou pour une mort non lue), repli sur une saturation très basse et longue.
sat = [x for x in etat["sat"] if x[1] > 0.3]  # 0 = écran noir, pas une mort
tps = np.array([x[0] for x in sat])
val = np.array([x[1] for x in sat])
med = float(np.median(val))
fen = max(1, int(3 * FPS_A))
lisse = np.convolve(val, np.ones(fen) / fen, mode="same")


def fin_de_mort(debut):
    i = int(np.searchsorted(tps, debut + 5))
    stable = int(2 * FPS_A)
    while i < len(tps) - stable:
        if (lisse[i:i + stable] > 0.85 * med).all() or tps[i] > debut + 75:
            return float(tps[i])
        i += 1
    return duree


morts = []
cm = cfg["morts"]
bas = lisse < 0.6 * med
debut = None
for i, b in enumerate(list(bas) + [False]):
    if b and debut is None:
        debut = i
    elif not b and debut is not None:
        a0, f0 = float(tps[debut]), float(tps[min(i, len(tps) - 1)])
        if f0 - a0 >= cm["duree_min_s"] + 3:
            morts.append([a0, f0, "saturation"])
        debut = None
etat["_morts_saturation"] = morts
t.ecrire("analyse/morts.json", {"saturation_mediane": med, "morts": [m[:2] for m in morts], "source": "saturation"})

# Écrans noirs (fusion de ceux coupés par une limite de tranche)
noirs = []
for a, b in sorted(etat["noirs"]):
    if noirs and a - noirs[-1][1] < 0.6:
        noirs[-1][1] = max(noirs[-1][1], b)
    else:
        noirs.append([a, b])
t.ecrire("analyse/noirs.json", noirs)
print(f"Écrans noirs : {len(noirs)}")

if SANS_HUD:
    sys.exit(0)

# ---------- 4. Événements lus dans le HUD ----------
lectures = etat["hud"]
t.ecrire("analyse/hud.json", lectures)


def stable(serie):
    """Valeur retenue si lue 2 fois de suite, jamais en baisse, pas plus de +4 d'un coup."""
    sortie, cour = [], None
    for i, (tt, v) in enumerate(serie):
        suiv = serie[i + 1][1] if i + 1 < len(serie) else None
        if v is not None and v == suiv and (cour is None or cour <= v <= cour + 4) and v != cour:
            sortie.append((tt, v))
            cour = v
    return sortie


def kda(s, i):
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{1,2})", s)
    return int(m.group(i + 1)) if m else None


def nombre(s):
    return int(s) if s.isdigit() and int(s) <= 80 else None


evenements = []
series = {"kill": lambda h: kda(h["kda"], 0), "mort": lambda h: kda(h["kda"], 1), "assist": lambda h: kda(h["kda"], 2),
          "kill_equipe": lambda h: nombre(h["kills_bleu"]), "kill_ennemi": lambda h: nombre(h["kills_rouge"])}
for nom, f in series.items():
    prec = 0
    for tt, v in stable([(h["t"], f(h)) for h in lectures]):
        if v > prec:
            evenements.append({"debut": round(tt - PAS_HUD, 1), "fin": tt, "type": nom, "valeur": v})
        prec = v
evenements.sort(key=lambda e: e["debut"])
t.ecrire("analyse/evenements.json", evenements)

# Morts : départ = mort lue dans le KDA (recalée sur la baisse de saturation), fin = retour des couleurs
morts = []
for e in (x for x in evenements if x["type"] == "mort"):
    fenetre = np.where((tps >= e["debut"] - 6) & (tps <= e["fin"] + 1) & (lisse < 0.72 * med))[0]
    d0 = float(tps[fenetre[0]]) if len(fenetre) else e["debut"]
    morts.append([d0, fin_de_mort(d0), "kda"])
for a0, f0, src in etat["_morts_saturation"]:  # morts vues seulement à l'image (ex. fin de partie)
    if not any(a0 < m[1] and f0 > m[0] for m in morts):
        morts.append([a0, f0, src])
morts.sort()
t.ecrire("analyse/morts.json", {"saturation_mediane": med, "morts": [m[:2] for m in morts],
                                "sources": [m[2] for m in morts]})
print("Morts :", ", ".join(f"{tc(a)} ({b - a:.0f} s, {s_})" for a, b, s_ in morts))
print(f"Événements HUD : {len(evenements)} —",
      ", ".join(f"{e['type']} {tc(e['fin'])}" for e in evenements if e["type"] in ("kill", "mort")))
