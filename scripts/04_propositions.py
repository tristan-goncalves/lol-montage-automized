"""Étape 4 — Construire les propositions de montage à partir des analyses :
  C = coupes évidentes (confiance élevée), D = cas à discuter, M = moments forts, I = idées / intros.

Les idées (I) et les intros sont rédigées par Claude dans propositions/idees.json (liste de
{"debut", "fin", "texte"}) : ce script les intègre au rapport et aux marqueurs.

Sorties : propositions/propositions.json, propositions/rapport.md, propositions/marqueurs.json
Usage : python scripts/04_propositions.py "<vidéo.mp4>"
"""
import numpy as np

from commun import Travail, argument_video, images, tc

t = Travail(argument_video())
cfg, c = t.cfg, t.cfg["coupes"]
info = t.infos()
duree, fps = info["duree_s"], info["fps"]
P = t.lire("analyse/parole.json")
parole, silences = P["parole"], P["silences"]
morts = t.lire("analyse/morts.json")["morts"]
noirs = t.lire("analyse/noirs.json")
evts = t.lire("analyse/evenements.json") if (t / "analyse/evenements.json").exists() else []
vol = t.lire("analyse/volume.json")
jeu, micro, pas = np.array(vol["jeu"]), np.array(vol["micro"]), vol["pas_s"]
transcription = t.lire("analyse/transcription.json")
mots = [w for s in transcription for w in s["mots"]]

instants = [x for e in evts for x in (e["debut"], e["fin"])] + [m[0] for m in morts]


def pres_evenement(a, b):
    g = c["garde_evenement_s"]
    return any(a - g <= x <= b + g for x in instants)


def dans_mort(a, b):
    return next((m for m in morts if a < m[1] and b > m[0]), None)


def stats_jeu(a, b):
    x = jeu[int(a / pas):max(int(b / pas), int(a / pas) + 1)]
    return float(x.mean()), float(x.max())


def extrait(a, b, marge=2.0):
    return " ".join(w[2].strip() for w in mots if a - marge <= w[0] <= b + marge)[:160]


C, D = [], []
for s0, s1 in silences:
    a = 0.0 if s0 <= 0 else s0 + c["marge_apres_parole_s"]
    b = duree if s1 >= duree - 0.1 else s1 - c["marge_avant_parole_s"]
    m = dans_mort(s0, s1)
    if m:
        a2 = max(a, m[0] + c["reaction_apres_mort_s"])
        b2 = min(b, m[1] - 0.3) if m[1] < duree - 0.5 else b
        if b2 - a2 >= c["duree_min_s"]:
            C.append([a2, b2, f"Mort à {tc(m[0])} sans commentaire (écran gris, micro silencieux)"])
        continue
    if s1 - s0 < c["silence_min_s"] or b - a < c["duree_min_s"] or pres_evenement(s0, s1):
        continue
    moy, mx = stats_jeu(s0, s1)
    if moy < c["jeu_calme_moyenne_db"] and mx < c["jeu_calme_max_db"]:
        C.append([a, b, "Silence en phase calme (farm / déplacement), aucun kill ni combat autour"])
    elif moy < c["jeu_hesitant_moyenne_db"]:
        D.append([a, b, "couper", "moyenne", f"Silence de {s1 - s0:.0f} s avec un peu d'action en jeu"])
    elif s1 - s0 >= c["accelerer_min_s"]:
        D.append([a, b, "accélérer ×2", "moyenne", f"Silence de {s1 - s0:.0f} s mais de l'action à l'écran"])

for a, b in noirs:
    if b - a >= 0.3:
        C.append([a, b, "Écran noir"])
    else:
        D.append([a, b, "couper", "élevée", "Écran noir d'une fraction de seconde (glitch d'enregistrement ?)"])

# Fusion des coupes évidentes qui se chevauchent
C.sort()
fusion = []
for a, b, r in C:
    if fusion and a <= fusion[-1][1] + 0.3:
        fusion[-1][1] = max(fusion[-1][1], b)
    else:
        fusion.append([a, b, r])
C = fusion

# Moments forts : kills / morts du HUD, puis pics d'excitation dans ta voix
M = []
for e in evts:
    if e["type"] == "kill":
        M.append([e["debut"] - 8, e["fin"] + 4, f"Kill n°{e['valeur']}"])
for m in morts:
    M.append([m[0] - 12, m[0] + 3, "Mort (le moment qui y mène)"])
fen = int(2 / pas)
lisse = np.convolve(micro, np.ones(fen) / fen, mode="same")
seuil = float(np.median(lisse[lisse > -60])) + 12 if (lisse > -60).any() else -20
pics = []
for i in np.argsort(-lisse):
    tt = i * pas
    if lisse[i] < seuil or len(pics) >= 8:
        break
    if all(abs(tt - p) > 20 for p in pics) and not any(a - 5 <= tt <= b + 5 for a, b, _ in M):
        pics.append(tt)
for tt in pics:
    M.append([tt - 5, tt + 4, f"Tu t'enflammes : « {extrait(tt - 2, tt + 2, 0)} »"])
M = sorted([[max(0, a), min(duree, b), r] for a, b, r in M])

idees = t.lire("propositions/idees.json") if (t / "propositions/idees.json").exists() else []

items = []
for i, (a, b, r) in enumerate(C, 1):
    items.append({"id": f"C{i}", "cat": "C", "debut": a, "fin": b, "action": "couper", "confiance": "élevée", "raison": r})
for i, (a, b, act, conf, r) in enumerate(sorted(D), 1):
    items.append({"id": f"D{i}", "cat": "D", "debut": a, "fin": b, "action": act, "confiance": conf, "raison": r,
                  "extrait": extrait(a, b)})
for i, (a, b, r) in enumerate(M, 1):
    items.append({"id": f"M{i}", "cat": "M", "debut": a, "fin": b, "action": "garder", "raison": r})
for i, x in enumerate(idees, 1):
    items.append({"id": f"I{i}", "cat": "I", "debut": x["debut"], "fin": x.get("fin", x["debut"]), "action": "idée",
                  "raison": x["texte"]})
t.ecrire("propositions/propositions.json", items)

# ---------- Rapport lisible ----------
total_c = sum(b - a for a, b, _ in C)
total_d = sum(x[1] - x[0] for x in D if x[2] == "couper")
titres = {"C": "Coupes évidentes", "D": "À discuter", "M": "Moments forts", "I": "Idées et intros"}
L = [f"# Propositions de montage — {t.nom}", "",
     f"- Durée brute : **{tc(duree)}**",
     f"- Après les coupes évidentes : **{tc(duree - total_c)}** ({len(C)} coupes, {tc(total_c)} retirées)",
     f"- Si tu valides aussi toutes les coupes « à discuter » : **{tc(duree - total_c - total_d)}**",
     f"- Morts détectées : {', '.join(tc(m[0]) for m in morts) or 'aucune'}",
     "", "Réponds par numéro : « C OK sauf C4 », « D2 accélérer », « D5 garder »…", ""]
for cat in "CDMI":
    lignes = [x for x in items if x["cat"] == cat]
    if not lignes:
        continue
    L += [f"## {titres[cat]}", "", "| N° | Début | Fin | Durée | Action | Confiance | Pourquoi |", "|---|---|---|---|---|---|---|"]
    for x in lignes:
        pourquoi = x["raison"] + (f" — « {x['extrait']} »" if x.get("extrait") else "")
        L.append(f"| {x['id']} | {tc(x['debut'])} | {tc(x['fin'])} | {x['fin'] - x['debut']:.0f} s | {x['action']} | "
                 f"{x.get('confiance', '')} | {pourquoi.replace('|', '/')} |")
    L.append("")
with open(t / "propositions/rapport.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))

# ---------- Marqueurs pour Resolve (project_manager.apply_spec) ----------
couleurs = cfg["resolve"]["couleurs_marqueurs"]
coul = {"C": couleurs["coupe_evidente"], "D": couleurs["a_discuter"], "M": couleurs["moment_fort"], "I": couleurs["idee"]}
marqueurs, pris = [], set()
for x in items:
    f0 = images(x["debut"], fps)
    while f0 in pris:
        f0 += 1
    pris.add(f0)
    note = x["raison"] + (f" | Proposition : {x['action']} | Confiance : {x['confiance']}" if x["cat"] in "CD" else "")
    marqueurs.append({"frame": f0, "color": coul[x["cat"]], "name": f"{x['id']} {titres[x['cat']]}", "note": note,
                      "duration": max(1, images(x["fin"] - x["debut"], fps))})
t.ecrire("propositions/marqueurs.json", marqueurs)
print(f"{len(C)} C / {len(D)} D / {len(M)} M / {len(idees)} I — durée après C : {tc(duree - total_c)}")
print(f"Rapport : {t / 'propositions/rapport.md'}")
