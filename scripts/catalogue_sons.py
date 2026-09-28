"""Catalogue la bibliothèque sonore (effets + musiques) avec des mesures objectives.

Pour chaque fichier : type (d'après le nom et la forme du son), durée, volume intégré et
momentané max, pic, dynamique, attaque (son sec ou progressif), brillance (aigu/grave),
tempo approximatif, et le GAIN CONSEILLÉ pour tomber au bon niveau sous la voix.

Je n'« écoute » pas : ces mesures servent à choisir un son adapté techniquement. L'ambiance
(drôle, épique…) vient du nom du fichier, d'où l'intérêt de noms descriptifs.

Sortie : <Records>/_montage/catalogue_sons.csv (+ .json). Relancer après tout ajout de fichiers.
Usage : python scripts/catalogue_sons.py
"""
import csv
import json
import re
import subprocess

import numpy as np

from commun import racine_locale, reglages

cfg = reglages()
RACINE = racine_locale(cfg)
MUSIQUES = RACINE / cfg["chemins"]["musiques"]
SORTIE = RACINE / cfg["chemins"]["travail"]
SORTIE.mkdir(exist_ok=True)
SR = 22050
TYPES = [("whoosh", "whoosh"), ("swoosh", "whoosh"), ("swish", "whoosh"), ("riser", "montée"), ("buildup", "montée"),
         ("reverse", "montée inversée"), ("impact", "impact"), ("hit", "impact"), ("boom", "impact"), ("bang", "impact"),
         ("thump", "impact"), ("explode", "explosion"), ("blast", "explosion"), ("camera", "appareil photo"),
         ("shutter", "appareil photo"), ("flash", "appareil photo"), ("ui", "interface"), ("click", "interface"),
         ("button", "interface"), ("pop", "interface"), ("chime", "interface"), ("notification", "interface"),
         ("success", "interface")]


def volume(p):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    resume = err[err.rfind("Summary:"):]

    def champ(k):
        m = re.search(k + r":\s+(-?[\d.]+|-inf)", resume)
        return -70.0 if not m or m.group(1) == "-inf" else float(m.group(1))

    moments = [float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", err)]
    return champ("I"), champ("LRA"), champ("Peak"), (max(moments) if moments else None)


def mesures(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < 2048:
        return {"duree_s": round(len(x) / SR, 2)}
    env = np.abs(x)
    attaque = float(np.argmax(env >= 0.9 * (env.max() or 1e-9)) / SR)
    n, freqs, centres = 2048, np.fft.rfftfreq(2048, 1 / SR), []
    for i in range(0, len(x) - n, n * max(1, len(x) // (n * 400))):
        s = np.abs(np.fft.rfft(x[i:i + n] * np.hanning(n)))
        if s.sum() > 1e-6:
            centres.append((freqs * s).sum() / s.sum())
    tempo = None
    if len(x) / SR > 20:  # autocorrélation de l'enveloppe d'attaques, 60-180 BPM
        hop = 512
        seg = x[: SR * 60]
        e = np.sqrt(np.convolve(seg ** 2, np.ones(hop) / hop, "valid")[::hop])
        o = np.maximum(0, np.diff(e))
        o -= o.mean()
        ac = np.correlate(o, o, "full")[len(o) - 1:]
        f = SR / hop
        lo, hi = int(f * 60 / 180), int(f * 60 / 60)
        if hi < len(ac):
            tempo = round(60 * f / (lo + int(np.argmax(ac[lo:hi]))))
    return {"duree_s": round(len(x) / SR, 2), "attaque_s": round(attaque, 3),
            "brillance_hz": round(float(np.median(centres))) if centres else None, "tempo_bpm": tempo}


def type_de(rel, d):
    nom = rel.lower()
    if "sound" not in nom and "effect" not in nom:  # musiques
        return "jingle" if d.get("duree_s", 0) < 40 else "musique"
    for cle, typ in TYPES:
        if cle in nom.rsplit("/", 1)[-1] or f"/{cle}" in nom:
            return typ
    return "impact" if (d.get("attaque_s") or 1) < 0.05 and d.get("duree_s", 9) < 3 else "effet"


lignes = []
fichiers = sorted(p for p in MUSIQUES.rglob("*") if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".flac"))
for p in fichiers:
    rel = p.relative_to(MUSIQUES).as_posix()
    try:
        integre, dyn, pic, mmax = volume(p)
        d = mesures(p)
    except Exception as e:  # un fichier illisible ne bloque pas le catalogue
        lignes.append({"fichier": rel, "type": "erreur", "note": str(e)})
        continue
    typ = type_de(rel, d)
    s = cfg["son"]
    if typ == "musique":
        gain = s["musique_lufs"] - integre
    elif typ == "jingle":
        gain = s["jeu_lufs"] - integre
    else:
        gain = (s["sfx_moment_max_cible"] - mmax) if mmax is not None and mmax > -70 else None
    lignes.append({"fichier": rel, "type": typ, **d, "lufs_integre": integre, "lufs_moment_max": mmax, "pic_dbfs": pic,
                   "dynamique_lu": dyn, "gain_conseille_db": round(gain, 1) if gain is not None else None})
    print(f"{typ:16} {rel}")

cles = ["fichier", "type", "duree_s", "lufs_integre", "lufs_moment_max", "pic_dbfs", "dynamique_lu", "attaque_s",
        "brillance_hz", "tempo_bpm", "gain_conseille_db", "note"]
with open(SORTIE / "catalogue_sons.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, cles, extrasaction="ignore", delimiter=";")
    w.writeheader()
    w.writerows(lignes)
with open(SORTIE / "catalogue_sons.json", "w", encoding="utf-8") as f:
    json.dump(lignes, f, ensure_ascii=False, indent=1)
print(f"{len(lignes)} fichiers catalogués -> {SORTIE / 'catalogue_sons.csv'}")
