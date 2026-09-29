"""Transforme les couleurs des marqueurs du rush annoté (modifiées par Tristan dans Resolve)
en décisions de montage (propositions/decisions.json), prêtes pour 05_plan_montage.py.

Code couleur (à changer dans Resolve : double-clic sur le marqueur > Color) :
  Coupes (C, D)   Rouge = couper · Vert = garder · Cyan = accélérer ×2 · Jaune = pas décidé (gardé)
  Idées / intros  Vert = je prends · Rouge = non · Bleu = pas décidé
  Moments forts   Vert = garder · Rouge = couper (rien d'intéressant à l'écran)
Déplacer ou rallonger un marqueur de coupe = ajuster la coupe : le début et la durée du marqueur
sont relus et deviennent la nouvelle plage.

Entrée : propositions/marqueurs_resolve.json = relevé des marqueurs de la timeline « 00 Rush annoté »
(Claude l'écrit via timeline_markers get_all : {"<frame>": {"color", "duration", "name", ...}}).
Usage : python scripts/decisions_depuis_resolve.py "<vidéo.mp4>"
"""
from commun import Travail, argument_video, tc

t = Travail(argument_video())
fps = t.infos()["fps"]
items = {x["id"]: x for x in t.lire("propositions/propositions.json")}
releve = t.lire("propositions/marqueurs_resolve.json")

dec = {"couper": [], "accelerer": [], "garder": [], "indecis": [], "ajustements": {},
       "idees_retenues": [], "idees_refusees": []}
vus = set()
for frame, m in releve.items():
    ident = m["name"].split()[0] if m.get("name") else ""
    if ident not in items:
        continue
    vus.add(ident)
    x, couleur = items[ident], m["color"]
    if x["cat"] in "CD":
        cible = {"Red": "couper", "Green": "garder", "Cyan": "accelerer"}.get(couleur, "indecis")
        dec[cible].append(ident)
        debut, fin = int(frame) / fps, (int(frame) + int(m["duration"])) / fps
        if abs(debut - x["debut"]) > 0.1 or abs(fin - x["fin"]) > 0.1:  # marqueur déplacé / redimensionné
            dec["ajustements"][ident] = [round(debut, 3), round(fin, 3)]
    elif x["cat"] == "M":
        if couleur == "Red":
            dec["couper"].append(ident)
    elif x["cat"] == "I":
        if couleur == "Green":
            dec["idees_retenues"].append(ident)
        elif couleur == "Red":
            dec["idees_refusees"].append(ident)

manquants = sorted(i for i, x in items.items() if x["cat"] in "CD" and i not in vus)
t.ecrire("propositions/decisions.json", dec)
print(f"Couper : {len(dec['couper'])} · garder : {len(dec['garder'])} · accélérer : {len(dec['accelerer'])} · "
      f"pas décidé (gardé) : {len(dec['indecis'])} · ajustés : {len(dec['ajustements'])}")
print("Idées retenues :", ", ".join(dec["idees_retenues"]) or "aucune", "| refusées :", ", ".join(dec["idees_refusees"]) or "aucune")
for i, (a, b) in dec["ajustements"].items():
    print(f"  {i} ajusté : {tc(items[i]['debut'])}-{tc(items[i]['fin'])} -> {tc(a)}-{tc(b)}")
if manquants:
    print("⚠ Marqueurs introuvables (supprimés ?) — traités comme gardés :", ", ".join(manquants))
