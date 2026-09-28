"""Étape 5 — Transformer tes décisions en plan de timeline pour Resolve.

Entrée : propositions/decisions.json, écrit par Claude à partir de tes réponses :
  {"couper": ["C1", "C2", "D4"], "accelerer": ["D2"], "garder": ["D1"],
   "ajustements": {"D3": [debut_s, fin_s]}}
  - Toute coupe évidente (C) non mentionnée ailleurs est coupée par défaut.
  - Tout cas à discuter (D) non mentionné est gardé par défaut (dans le doute, on garde).

Sortie : propositions/plan_v1.json avec, pour chaque morceau gardé, les images source et
d'enregistrement, prêtes pour media_pool.append_to_timeline (vidéo V1, jeu A1, micro A2).

Accélération ×2 : la vidéo est placée sur la moitié de sa durée source puis passée à 200 %
(timeline_item.set_speed garde la durée de l'élément et consomme 2x plus d'images). Le son du jeu
n'est pas placé sur ces morceaux (à ×2 il devient aigu) : la musique prend le relais.

Usage : python scripts/05_plan_montage.py "<vidéo.mp4>"
"""
from commun import Travail, argument_video, images, tc

t = Travail(argument_video())
fps = t.infos()["fps"]
duree = t.infos()["duree_s"]
items = {x["id"]: x for x in t.lire("propositions/propositions.json")}
dec = t.lire("propositions/decisions.json")
garder = set(dec.get("garder", []))
couper = set(dec.get("couper", [])) | {i for i, x in items.items() if x["cat"] == "C" and i not in garder}
accel = set(dec.get("accelerer", []))
ajust = dec.get("ajustements", {})

zones = []  # (debut, fin, type) avec type "coupe" ou "accel"
for i in couper | accel:
    x = items[i]
    a, b = ajust.get(i, (x["debut"], x["fin"]))
    zones.append((a, b, "accel" if i in accel else "coupe"))
zones.sort()

morceaux, pos = [], 0.0
for a, b, typ in zones:
    if a > pos:
        morceaux.append((pos, a, 1))
    if typ == "accel":
        morceaux.append((max(a, pos), b, 2))
    pos = max(pos, b)
if pos < duree:
    morceaux.append((pos, duree, 1))
morceaux = [m for m in morceaux if m[1] - m[0] >= 1 / fps]

plan, rec = [], 0
for a, b, vitesse in morceaux:
    f0, f1 = images(a, fps), images(b, fps)
    longueur = (f1 - f0) // vitesse
    plan.append({"source_debut": f0, "source_fin": f0 + longueur, "record": rec, "vitesse": vitesse,
                 "debut_s": round(a, 2), "fin_s": round(b, 2)})
    rec += longueur

t.ecrire("propositions/plan_v1.json", {
    "fps": fps, "duree_finale_s": round(rec / fps, 2), "morceaux": plan,
    "note": "end_frame exclusif ; record relatif au début de la timeline ; vitesse 2 -> set_speed Percentage 200 après placement"})
print(f"{len(plan)} morceaux, dont {sum(1 for p in plan if p['vitesse'] == 2)} accélérés — durée finale {tc(rec / fps)}")
