"""Étape 1 — Vérifier la vidéo et extraire le son en deux fichiers : jeu.wav et micro.wav.

Pourquoi deux WAV : l'import FCPXML/XML dans Resolve mélange les pistes (jeu en mono gauche/droite,
voix perdue). On place donc nous-mêmes jeu.wav sur A1 et micro.wav sur A2.

Usage : python scripts/01_preparer.py "<vidéo.mp4>"
"""
from commun import Travail, argument_video, ffmpeg, sonder, tc

t = Travail(argument_video())
cfg = t.cfg
info = sonder(t.video)
t.ecrire("video.json", info)
print(f"Vidéo : {t.nom} — {tc(info['duree_s'])}, {info['fps']} i/s, {info['largeur']}x{info['hauteur']}, "
      f"{info['pistes_audio']} piste(s) audio")

problemes = []
if info["pistes_audio"] < 2:
    problemes.append("une seule piste audio : impossible de séparer jeu et micro (vérifie OBS : piste 1 = jeu, piste 2 = micro)")
if abs(info["fps"] - cfg["video"]["fps"]) > 0.5:
    problemes.append(f"fps {info['fps']} différent du réglage {cfg['video']['fps']}")
if (info["largeur"], info["hauteur"]) != (cfg["video"]["largeur"], cfg["video"]["hauteur"]):
    problemes.append("résolution différente de 1080p : les positions du HUD seront fausses")
for p in problemes:
    print("⚠", p)

for nom, piste in (("jeu", cfg["video"]["piste_jeu"]), ("micro", cfg["video"]["piste_micro"])):
    sortie = t / f"audio/{nom}.wav"
    attendu = int(info["duree_s"] * 48000 * 4)  # 48 kHz, stéréo, 16 bits
    if sortie.exists() and sortie.stat().st_size > attendu * 0.99:
        print(f"{nom}.wav déjà présent et complet, on le garde")
        continue
    if piste >= info["pistes_audio"]:
        continue
    # On écrit dans un fichier temporaire puis on renomme : un fichier interrompu (commande coupée)
    # n'est jamais pris pour un fichier complet.
    tmp = sortie.with_name(f"{nom}_en_cours.wav")
    ffmpeg("-i", str(t.video), "-map", f"0:a:{piste}", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(tmp))
    tmp.replace(sortie)
    print(f"{nom}.wav extrait")

print(f"Dossier de travail : {t.dossier}")
