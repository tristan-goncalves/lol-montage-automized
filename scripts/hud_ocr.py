"""Lecture des chiffres du HUD de LoL par comparaison à des modèles de caractères.

Pourquoi pas tesseract : sur la police du HUD, tesseract confond régulièrement le 5 avec 3 ou 9
(KDA « 5/2/1 » lu « 3/2/1 »), ce qui faisait disparaître des kills. Les caractères du HUD ont
toujours la même forme : une simple comparaison avec des modèles appris est bien plus fiable.

Modèles : templates/hud_caracteres.json, appris avec `python scripts/hud_ocr.py apprendre`
à partir d'images étiquetées (voir EXEMPLES ci-dessous).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from commun import DEPOT, reglages

MODELES = DEPOT / "templates" / "hud_caracteres.json"
TAILLE = (12, 18)  # largeur, hauteur normalisées d'un caractère


def binariser(im: np.ndarray, seuil: int = 120) -> np.ndarray:
    return (im.max(axis=2) > seuil).astype(np.uint8)


def caracteres(b: np.ndarray) -> list[np.ndarray]:
    """Découpe une zone binarisée en caractères (composantes connexes), de gauche à droite."""
    import cv2

    n, _, stats, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    boites = []
    for i in range(1, n):
        x, y, w, h, aire = stats[i]
        if h < 9 or aire < 12 or y > b.shape[0] * 0.5:  # bruit, deux-points, texte flottant sous le HUD
            continue
        boites.append((x, y, w, h))
    # fusionne les morceaux d'un même caractère qui se chevauchent horizontalement
    boites.sort()
    fus = []
    for x, y, w, h in boites:
        if fus and x < fus[-1][0] + fus[-1][2] - 1:
            X, Y, W, H = fus[-1]
            x2, y2 = max(X + W, x + w), max(Y + H, y + h)
            fus[-1] = (min(X, x), min(Y, y), x2 - min(X, x), y2 - min(Y, y))
        else:
            fus.append((x, y, w, h))
    sortie = []
    for x, y, w, h in fus:
        g = b[y:y + h, x:x + w].astype(np.float32)
        sortie.append(normaliser(g))
    return sortie


def normaliser(g: np.ndarray) -> np.ndarray:
    import cv2

    L, H = TAILLE
    h, w = g.shape
    echelle = H / h
    nw = max(1, min(L, int(round(w * echelle))))
    r = cv2.resize(g, (nw, H), interpolation=cv2.INTER_AREA)
    toile = np.zeros((H, L), np.float32)
    x0 = (L - nw) // 2
    toile[:, x0:x0 + nw] = r
    return toile


def charger_modeles() -> dict[str, list[np.ndarray]]:
    d = json.load(open(MODELES, encoding="utf-8"))
    return {k: [np.array(m, np.float32) for m in v] for k, v in d.items()}


def lire(zone_bgr: np.ndarray, modeles: dict, autorises: str) -> str:
    texte = ""
    for c in caracteres(binariser(zone_bgr)):
        meilleur, score = "?", 1e9
        for k, ms in modeles.items():
            if k not in autorises:
                continue
            for m in ms:
                s = float(((c - m) ** 2).sum())
                if s < score:
                    meilleur, score = k, s
        texte += meilleur
    return texte


def lire_hud(bandeau_bgr: np.ndarray, modeles: dict, champs: dict) -> dict:
    autor = {"kda": "0123456789/", "horloge": "0123456789"}
    return {nom: lire(bandeau_bgr[:, a:b], modeles, autor.get(nom, "0123456789")) for nom, (a, b) in champs.items()}


# Images d'apprentissage : bandeau HUD 380x32 -> valeurs réelles (partie du 17/08)
EXEMPLES = {
    "h_1180.png": {"kills_bleu": "18", "kills_rouge": "17", "kda": "4/2/1", "horloge": "2017"},
    "h_400.png": {"kills_bleu": "9", "kills_rouge": "4", "kda": "2/0/0", "horloge": "0717"},
    "h_1500.png": {"kills_bleu": "27", "kills_rouge": "25", "kda": "5/4/3", "horloge": "2537"},
    "h_960.png": {"kills_bleu": "18", "kills_rouge": "10", "kda": "4/1/1", "horloge": "1637"},
    "h_1205.png": {"kills_bleu": "20", "kills_rouge": "20", "kda": "5/2/1", "horloge": "2042"},
    "h_1220.png": {"kills_bleu": "21", "kills_rouge": "20", "kda": "5/2/2", "horloge": "2057"},
    "h_1300.png": {"kills_bleu": "26", "kills_rouge": "20", "kda": "5/2/3", "horloge": "2217"},
    "h_700.png": {"kills_bleu": "17", "kills_rouge": "9", "kda": "4/0/1", "horloge": "1217"},
}

if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] == "apprendre":
    import cv2

    dossier = Path(sys.argv[2])
    champs = reglages()["hud"]["champs"]
    modeles: dict[str, list] = {}
    for fichier, valeurs in EXEMPLES.items():
        im = cv2.imread(str(dossier / fichier))
        for nom, (a, b) in champs.items():
            cs = caracteres(binariser(im[:, a:b]))
            attendu = valeurs[nom]
            if len(cs) != len(attendu):
                print(f"⚠ {fichier} {nom} : {len(cs)} caractères trouvés pour « {attendu} », ignoré")
                continue
            for car, g in zip(attendu, cs):
                modeles.setdefault(car, []).append(g.round(3).tolist())
    json.dump(modeles, open(MODELES, "w", encoding="utf-8"))
    print("Modèles appris :", {k: len(v) for k, v in sorted(modeles.items())})
    # Vérification : relecture des exemples
    mods = charger_modeles()
    erreurs = 0
    for fichier, valeurs in EXEMPLES.items():
        lu = lire_hud(cv2.imread(str(dossier / fichier)), mods, champs)
        for k, v in valeurs.items():
            if lu[k] != v:
                erreurs += 1
                print(f"✗ {fichier} {k} : lu {lu[k]} au lieu de {v}")
    print(f"Relecture des exemples : {erreurs} erreur(s)")
