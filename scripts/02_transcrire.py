"""Étape 2 — Transcrire ta voix (micro.wav) avec l'horodatage de chaque mot, puis en déduire
les moments où tu parles et les silences.

Deux façons de l'utiliser :
  1. Sur ton PC, PAR TRANCHES (reprend où il s'est arrêté, relancer tant qu'il affiche « À RELANCER ») :
       python scripts/02_transcrire.py "<vidéo.mp4>" [--budget 150]
  2. Ailleurs (machine plus puissante, ex. l'espace de travail cloud de Claude) :
       python scripts/02_transcrire.py "<vidéo.mp4>" --exporter-audio      -> audio/micro.opus (léger)
       python scripts/02_transcrire.py --audio micro.opus --sortie transcription.json
     puis recopier transcription.json dans analyse/ et relancer le mode 1 (il ne fait alors que la suite).

Sorties : analyse/transcription.json, analyse/transcription.txt, analyse/parole.json
"""
import sys
import tempfile
import time

DEBUT = time.time()


def arg(nom, defaut=None):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else defaut


def modele(cfg):
    from faster_whisper import WhisperModel  # import tardif : lourd
    return WhisperModel(cfg["modele"], device="cpu", compute_type="int8")


def transcrire(m, audio, cfg, decalage=0.0):
    segs, _ = m.transcribe(str(audio), language=cfg["langue"], vad_filter=True, word_timestamps=True,
                           initial_prompt=cfg["prompt"])
    return [{"debut": s.start + decalage, "fin": s.end + decalage, "texte": s.text.strip(),
             "mots": [[w.start + decalage, w.end + decalage, w.word] for w in (s.words or [])]} for s in segs]


# ---------- Mode autonome (aucun dossier de travail) ----------
if "--audio" in sys.argv:
    import json
    import os
    import yaml

    here = os.path.dirname(os.path.abspath(__file__))
    cfg = yaml.safe_load(open(os.path.join(here, "..", "config", "reglages.yaml"), encoding="utf-8"))["transcription"]
    res = transcrire(modele(cfg), arg("--audio"), cfg)
    json.dump(res, open(arg("--sortie", "transcription.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(res)} segments -> {arg('--sortie', 'transcription.json')}")
    sys.exit(0)

from commun import Travail, argument_video, ffmpeg, tc  # noqa: E402

t = Travail(argument_video())
cfg = t.cfg["transcription"]
duree = t.infos()["duree_s"]
BUDGET = float(arg("--budget", 150))

if "--exporter-audio" in sys.argv:
    ffmpeg("-i", str(t / "audio/micro.wav"), "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "24k",
           str(t / "audio/micro.opus"))
    print(f"Audio léger : {t / 'audio/micro.opus'}")
    sys.exit(0)

# ---------- Transcription locale par tranches ----------
final = t / "analyse/transcription.json"
if not final.exists():
    import json

    partiel_f = t / "analyse/_transcription_partielle.json"
    etat = t.lire("analyse/_transcription_partielle.json") if partiel_f.exists() else {"fait_jusqua": 0.0, "segments": []}
    # Découper sur des silences du micro pour ne pas couper un mot en deux
    vol = t.lire("analyse/volume.json") if (t / "analyse/volume.json").exists() else None

    def fin_de_tranche(debut, longueur):
        cible = min(duree, debut + longueur)
        if not vol or cible >= duree:
            return cible
        pas, micro = vol["pas_s"], vol["micro"]
        i0, i1 = int((cible - 20) / pas), int(cible / pas)
        calmes = [i for i in range(max(i0, int(debut / pas) + 1), min(i1, len(micro))) if micro[i] < -50]
        return calmes[-1] * pas if calmes else cible

    m = modele(cfg)
    longueur, vitesse = 45.0, None
    while etat["fait_jusqua"] < duree - 0.5:
        reste = BUDGET - (time.time() - DEBUT)
        if vitesse is not None:
            longueur = min(300.0, max(20.0, reste * 0.8 / vitesse))
            if reste < 20 * vitesse:
                break
        a = etat["fait_jusqua"]
        b = fin_de_tranche(a, longueur)
        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            ffmpeg("-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(t / "audio/micro.wav"), "-ac", "1", "-ar", "16000",
                   f"{tmp}/x.wav", capture=True)
            etat["segments"] += transcrire(m, f"{tmp}/x.wav", cfg, a)
        vitesse = (time.time() - t0) / (b - a)
        etat["fait_jusqua"] = b
        t.ecrire("analyse/_transcription_partielle.json", etat)
    if etat["fait_jusqua"] < duree - 0.5:
        print(f"À RELANCER : transcrit jusqu'à {tc(etat['fait_jusqua'])} sur {tc(duree)} "
              f"(vitesse {vitesse:.2f} s de calcul par seconde d'audio)")
        sys.exit(0)
    t.ecrire("analyse/transcription.json", etat["segments"])

# ---------- Parole et silences ----------
segments = t.lire("analyse/transcription.json")
with open(t / "analyse/transcription.txt", "w", encoding="utf-8") as f:
    f.writelines(f"[{tc(s['debut'])}] {s['texte']}\n" for s in segments)
parole = []
for s in segments:
    for a, b, _ in s["mots"]:
        b = min(b, a + cfg["duree_max_mot_s"])
        if parole and a - parole[-1][1] < cfg["fusion_ecart_s"]:
            parole[-1][1] = max(parole[-1][1], b)
        else:
            parole.append([a, b])
silences, prec = [], 0.0
for a, b in parole:
    if a > prec:
        silences.append([prec, a])
    prec = b
if prec < duree:
    silences.append([prec, duree])
t.ecrire("analyse/parole.json", {"parole": parole, "silences": silences})
total = sum(b - a for a, b in parole)
print(f"Parole : {tc(total)} sur {tc(duree)} ({100 * total / duree:.0f} %), {len(silences)} silences")
