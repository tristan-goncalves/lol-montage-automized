"""Étape 6 — Construction : traduit plan_v2.json + intro + habillage en listes d'éléments Resolve
(images source / images d'enregistrement) pour une timeline PLATE : intro puis partie, sans timeline
imbriquée, relisible et retouchable directement dans Edit.

Pistes : V1 jeu, V2 habillage (titre, runes pré-rendues avec ombre, S'abonner, zooms HUD) ;
         A1 son du jeu, A2 micro, A3 musique, A4 effets.
Intro : propositions/intro_<v>.json. Le dernier extrait peut être prolongé (« prolonger_s ») : ta voix
        s'arrête à la fin de ta phrase, puis le son du jeu fond, puis l'image fond au noir.
        Le titre « Dans cette vidéo… » est fabriqué ici (ffmpeg) à la durée exacte de l'intro.
Fondus micro adaptés à chaque coupe : jamais sur un mot (raccourcis s'il n'y a pas assez de silence).
Habillage de la partie : positions en secondes SOURCE (propositions/habillage_<v>.json).
Sortie : propositions/construction_<v>.json (frames relatives au début de la timeline).
Usage : python scripts/08_construction_v2.py "<vidéo>" [--version v3]
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from commun import Travail, argument_video, DEPOT

t = Travail(argument_video())
V = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "v2"
fps = int(round(t.infos()["fps"]))
plan = t.lire("propositions/plan_v2.json")
intro = t.lire(f"propositions/intro_{V}.json")
hab = t.lire(f"propositions/habillage_{V}.json")
F = lambda s: int(round(s * fps))


def phrase(s):
    m = s.get("mots") or []
    return (m[0][0], min(m[-1][1], m[-1][0] + 2.5)) if m else (s["debut"], s["fin"])


phrases = sorted(phrase(s) for s in t.lire("analyse/transcription.json"))


def fondus_voix(a_s, b_s, maxi):
    """Fondus (images) d'un morceau de micro [a_s, b_s] (secondes source) : ils ne touchent jamais un mot."""
    fin = [f for d, f in phrases if d < b_s and f > a_s]
    deb = [d for d, f in phrases if d < b_s and f > a_s]
    marge_fin = b_s - max(fin) if fin else 9
    marge_deb = min(deb) - a_s if deb else 9
    conv = lambda m: max(0, min(maxi, int(m * fps) - 1))
    return conv(marge_deb), conv(marge_fin)


video, jeu, micro, v2, a3, a4, vitesses, marqueurs, transfos = [], [], [], [], [], [], [], [], []

# --- Intro
rec = 0
fv = intro.get("fondu_voix", 6)
for c in intro["clips"]:
    a, b = F(c["src"][0]), F(c["src"][1])
    rallonge = F(c.get("prolonger_s", 0))
    video.append({"src": [a, b + rallonge], "rec": rec, "role": "intro"})
    jeu.append({"src": [a, b + rallonge], "rec": rec, "fondu": intro.get("fondu_jeu", 12),
                "fondu_sortie": rallonge or intro.get("fondu_jeu", 12)})
    if c.get("voix", True):
        fi, fo = fondus_voix(c["src"][0], c["src"][1], fv)
        micro.append({"src": [a, b], "rec": rec, "fondu_entree": fi, "fondu_sortie": fo})
    for s in c.get("sfx", []):  # effet sonore calé sur un kill (seconde source), attaque du son retirée
        a4.append({"fichier": s["fichier"], "rec": rec + F(s["t"] - c["src"][0] - s.get("attaque", 0)),
                   "duree": F(s.get("duree", 1.8))})
    rec += b + rallonge - a
fin_intro = rec
dernier = intro["clips"][-1]
# fondu au noir : sur la fin de la rallonge (il commence après le fondu du son)
video[-1]["fondu_noir"] = F(intro.get("fondu_noir_s", 2.0))
G = fin_intro + F(intro.get("noir_s", 0.6))  # début de la partie

titre = intro.get("titre")
if titre:
    debut = F(titre.get("debut_s", 0.2))
    fin = fin_intro - F(dernier.get("prolonger_s", 0)) if titre.get("jusqua") == "fin_voix" else fin_intro
    duree = fin - debut
    sortie = t / titre["fichier"]
    police = DEPOT / "templates" / "polices" / "Poppins-Bold.ttf"
    d = duree / fps
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "t.txt").write_text(titre.get("texte", "Dans cette vidéo…"), encoding="utf-8")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"color=c=black@0:s=1920x1080:r={fps}:d={d:.3f},format=rgba", "-vf",
                        f"drawbox=x=64:y=66:w=8:h=66:color=0xffd84d@1:t=fill:replace=1,"
                        f"drawtext=fontfile={police}:textfile={tmp}/t.txt:x=92:y=62:fontsize=56:fontcolor=white:"
                        f"shadowcolor=black@0.75:shadowx=3:shadowy=3,"
                        f"fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st={d - 0.8:.3f}:d=0.8:alpha=1",
                        "-frames:v", str(duree), "-c:v", "qtrle", "-pix_fmt", "argb", str(sortie)], check=True)
    v2.append({"fichier": titre["fichier"], "rec": debut, "duree": duree, "nom": "titre"})
if intro.get("whoosh"):
    w = intro["whoosh"]
    a4.append({"fichier": w["fichier"], "rec": G - F(w.get("pic_s", 0.5)), "duree": F(w["duree_s"])})

# --- Partie
cumul = 0
pos = []  # (src_a, src_b, rec_a, vitesse) pour replacer l'habillage
for i, m in enumerate(plan["morceaux"]):
    x, y = m["src"]
    v = m["vitesse"]
    d = int(round((y - x) * fps / v))
    a = F(x)
    r = G + cumul
    el = {"src": [a, a + d], "rec": r}
    fj = hab.get("fondu_jeu", 8) if v == 1 else hab.get("fondu_accel", 15)
    video.append(dict(el, role="partie", **({"fondu_entree": F(intro.get("fondu_depuis_noir_s", 1.2))} if i == 0 else {})))
    jeu.append(dict(el, fondu=fj, **({"fondu_entree": F(intro.get("fondu_depuis_noir_s", 1.2))} if i == 0 else {})))
    if v != 1:
        vitesses.append({"piste": "video", "rec": r, "pourcent": round(v * 100)})
        vitesses.append({"piste": "jeu", "rec": r, "pourcent": round(v * 100)})
        marqueurs.append({"rec": r, "couleur": "Cyan", "nom": f"Accéléré ×{v:g}",
                          "note": "Retour à la base / temps mort accéléré, voix à vitesse normale", "duree": d})
    for vx in m["voix"]:
        sa, sb = vx["src"]
        fi, fo = fondus_voix(sa, sb, hab.get("fondu_voix", 4))
        micro.append({"src": [F(sa), F(sb)], "rec": r + F(vx["decalage"]), "fondu_entree": fi, "fondu_sortie": fo})
    pos.append((x, y, r, v))
    cumul += d
fin = G + cumul
if micro:
    micro[-1]["fondu_sortie"] = max(micro[-1]["fondu_sortie"], 0)
video[-1]["fondu_noir"] = F(1.5)


def placer(s):
    """Seconde source -> frame du montage (None si la seconde a été coupée)."""
    for x, y, r, v in pos:
        if x <= s < y:
            return r + int(round((s - x) * fps / v))
    return None


journal = []
elements = list(hab["elements"])
if (t / "habillage/killfeed.json").exists():
    elements += t.lire("habillage/killfeed.json")
for h in elements:
    r = placer(h["src_s"])
    if r is None:
        if h.get("optionnel"):
            journal.append(f"{h['nom']} : seconde {h['src_s']} coupée, abandonné")
            continue
        suivants = [p for p in pos if p[0] >= h["src_s"]]
        r = suivants[0][2] if suivants else None
        journal.append(f"{h['nom']} : seconde {h['src_s']} coupée, déplacé au morceau suivant")
    if r is None:
        continue
    el = {"fichier": h["fichier"], "rec": r + F(h.get("decalage_s", 0)), "duree": F(h["duree_s"]), "nom": h["nom"]}
    if h.get("transform"):
        el["transform"] = h["transform"]
    (v2 if h["piste"] == "V2" else a4).append(el)

# Musique : du début de la partie à la fin, avec un trou pendant les jingles qui la remplacent
trous = sorted((e["rec"], e["rec"] + e["duree"]) for e in a4 if e.get("nom") in hab.get("coupent_musique", []))
debut = G
for ta, tb in trous + [(fin, fin)]:
    if ta > debut:
        a3.append({"fichier": hab["musique"], "src": [debut - G, ta - G], "rec": debut, "fondu": F(2.0)})
    debut = max(debut, tb - F(hab.get("reprise_musique_avant_fin_s", 1.3)))

# Calage des coupes du micro sur l'énergie réelle de la voix (les fins de mots de Whisper sont approximatives :
# une coupe « après le dernier mot » tombait parfois au milieu de la dernière syllabe). Une fin de morceau qui tombe
# dans la parole est repoussée jusqu'au premier creux (fenêtre de 40 ms sous SEUIL), un début est avancé de même,
# sans jamais empiéter sur le morceau de micro voisin.
import numpy as np
import wave
SEUIL = hab.get("seuil_creux_db", -36)


def energie(w, t0, t1):
    w.setpos(min(w.getnframes() - 1, max(0, int(t0 * 48000))))
    d = np.frombuffer(w.readframes(max(1, int((t1 - t0) * 48000))), np.int16).reshape(-1, w.getnchannels()).mean(1)
    return 20 * np.log10(np.sqrt((d ** 2).mean()) / 32768 + 1e-9)


def creux(w, t, sens, maxi):
    """Premier creux de voix (fenêtre de 20 ms sous SEUIL) après/avant t, dans maxi secondes : la fin réelle du
    mot en cours. None s'il n'y en a pas (parole continue : à vérifier à l'oreille)."""
    pas = 0.02
    for k in range(1, int(maxi / pas) + 1):
        x = t + sens * k * pas
        if energie(w, x - 0.01, x + 0.01) < SEUIL:
            return x
    return None


calages = []
with wave.open(str(t / "audio/micro.wav")) as w:
    micro.sort(key=lambda m: m["rec"])
    for k, m in enumerate(micro):
        a, b = m["src"]
        prec = micro[k - 1] if k else None
        suiv = micro[k + 1] if k + 1 < len(micro) else None
        # la parole continue dans un autre morceau (même source juste après / avant) : coupe voulue, on n'y touche pas
        colle_suiv = any(o["src"][0] - F(0.5) <= b <= o["src"][1] and o["src"][0] > a for o in micro if o is not m)
        colle_prec = any(o["src"][0] <= a <= o["src"][1] + F(0.5) and o["src"][1] < b for o in micro if o is not m)
        if not colle_suiv and energie(w, b / fps - 0.03, b / fps) > SEUIL:
            place = (suiv["rec"] if suiv else fin) - (m["rec"] + b - a)
            x = creux(w, b / fps, +1, min(0.45, place / fps))
            if x is not None:
                m["src"][1] = F(x)
                m["fondu_sortie"] = 2
                calages.append(f"micro {k} fin {b / fps:.2f} -> {x:.2f}")
            else:
                journal.append(f"micro {k} : fin {b / fps:.2f} dans la parole, pas de creux (à vérifier)")
        if not colle_prec and energie(w, a / fps, a / fps + 0.03) > SEUIL:
            place = m["rec"] - ((prec["rec"] + prec["src"][1] - prec["src"][0]) if prec else 0)
            x = creux(w, a / fps, -1, min(0.3, place / fps))
            if x is not None:
                m["rec"] -= a - F(x)
                m["src"][0] = F(x)
                m["fondu_entree"] = 2
                calages.append(f"micro {k} début {a / fps:.2f} -> {x:.2f}")
            else:
                journal.append(f"micro {k} : début {a / fps:.2f} dans la parole, pas de creux (à vérifier)")
print(f"{len(calages)} coupes de micro recalées sur un creux de voix")
journal += calages

# Chevauchements sur V2 / A4 : signalés (Resolve refuse deux éléments au même endroit d'une piste)
for nom, piste in (("V2", v2), ("A4", a4)):
    piste.sort(key=lambda e: e["rec"])
    for e1, e2 in zip(piste, piste[1:]):
        if e1["rec"] + e1["duree"] > e2["rec"]:
            journal.append(f"CHEVAUCHEMENT {nom} : {e1.get('nom', e1['fichier'])} / {e2.get('nom', e2['fichier'])}")

t.ecrire(f"propositions/construction_{V}.json", {
    "fps": fps, "fin_intro": fin_intro, "debut_partie": G, "fin": fin,
    "video": video, "jeu": jeu, "micro": micro, "v2": v2, "a3": a3, "a4": a4,
    "vitesses": vitesses, "marqueurs": marqueurs, "journal": journal})
print(f"Intro {fin_intro / fps:.1f} s, partie à {G / fps:.1f} s, fin {int(fin / fps // 60)} min {fin / fps % 60:04.1f} s")
print(f"{len(video)} vidéo, {len(jeu)} jeu, {len(micro)} micro, {len(v2)} V2, {len(a3)} musique, {len(a4)} effets")
print("Fondus micro raccourcis (mot trop proche de la coupe) :",
      sum(1 for m in micro if min(m["fondu_entree"], m["fondu_sortie"]) < 4))
print("\n".join(journal))
