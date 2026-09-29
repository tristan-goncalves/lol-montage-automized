"""Étape 5 bis — Plan v2 : part du plan v1 (tes décisions) et applique les règles de la revue du 29/09.

1. Une mort n'est jamais masquée : on garde l'image et le son du jeu de ~8 s avant la mort jusqu'à 2,5 s
   après (écran gris). Si ce passage était coupé pour un coup de colère (coupe libre ou moment fort M
   refusé), seule ta voix y est retirée.
2. Retours à la base (analyse/retours_base.json) : un long silence (≥ 5 s) est coupé ; le reste est
   accéléré (jusqu'à ×2) si ça fait gagner au moins 3 s. Ta voix reste à vitesse normale : tes phrases
   sont posées les unes après les autres dans le passage accéléré.
3. Les accélérations déjà décidées (D) suivent la même règle (voix à vitesse normale).

Entrées : propositions/plan_v1.json, decisions.json, propositions.json, analyse/transcription.json,
analyse/morts.json, analyse/retours_base.json. Exceptions possibles dans decisions.json :
  "retours_base": {"241.0": "garder" | "couper" | "accelerer"}   (clé = début du retour)
Sortie : propositions/plan_v2.json — pour chaque morceau : source vidéo [a, b] (s), vitesse, et les
morceaux de voix {src: [a, b], decalage: s depuis le début du morceau dans la timeline}.
Usage : python scripts/07_plan_v2.py "<vidéo.mp4>"
"""
from commun import Travail, argument_video

t = Travail(argument_video())
fps = t.infos()["fps"]
R = t.cfg.get("plan_v2", {})
AVANT_MORT = R.get("avant_mort_s", 8.0)
APRES_MORT = R.get("apres_mort_s", 2.5)
SILENCE_COUPE = R.get("silence_coupe_retour_s", 5.0)
MARGE = R.get("marge_parole_s", 0.4)
GAIN_MIN = R.get("gain_min_accel_s", 3.0)
VIT_MAX = R.get("vitesse_max", 3.0)
ECART_VOIX = R.get("ecart_voix_accel_s", 0.45)
MARGE_FIN_PHRASE = R.get("marge_fin_phrase_s", 0.35)   # silence gardé après une phrase avant une coupe
MARGE_DEBUT_PHRASE = R.get("marge_debut_phrase_s", 0.15)
COMBLER = R.get("combler_avant_mort_s", 6.0)
COUPE_MIN = R.get("coupe_min_s", 1.5)

v1 = t.lire("propositions/plan_v1.json")
dec = t.lire("propositions/decisions.json")
props = {x["id"]: x for x in t.lire("propositions/propositions.json")}
morts = t.lire("analyse/morts.json")["morts"]
retours = t.lire("analyse/retours_base.json") if (t / "analyse/retours_base.json").exists() else []
choix_retours = dec.get("retours_base", {})


def phrase(s):
    """Bornes réelles d'une phrase : premier / dernier mot (whisper étire parfois les segments)."""
    m = s.get("mots") or []
    if m:
        return (m[0][0], min(m[-1][1], m[-1][0] + 2.5))
    return (s["debut"], s["fin"])


phrases = sorted(phrase(s) for s in t.lire("analyse/transcription.json"))


def moins(zones, trous):
    """zones - trous (listes d'intervalles)."""
    res = []
    for a, b in zones:
        morceaux = [(a, b)]
        for x, y in trous:
            nv = []
            for c, d in morceaux:
                if y <= c or x >= d:
                    nv.append((c, d))
                else:
                    if x > c:
                        nv.append((c, x))
                    if y < d:
                        nv.append((y, d))
            morceaux = nv
        res += morceaux
    return [(a, b) for a, b in res if b - a > 0.05]


def union(zones):
    res = []
    for a, b in sorted(zones):
        if res and a <= res[-1][1] + 1e-6:
            res[-1] = (res[-1][0], max(res[-1][1], b))
        else:
            res.append((a, b))
    return res


def voix_entiere(zones, marges=False):
    """Retire des zones de voix les phrases coupées sur un bord (jamais la moitié d'une phrase)."""
    res = []
    for a, b in zones:
        md, mf = (MARGE_DEBUT_PHRASE, MARGE_FIN_PHRASE) if marges else (0.0, 0.0)
        for d, f in phrases:
            if d - md < a < f + mf:
                a = f + mf
            if d - md < b < f + mf:
                b = d - md
        if b - a > 0.3:
            res.append((a, b))
    return res


# --- Morceaux v1 : vidéo gardée, et accélérations déjà décidées
garde = []   # (a, b, vitesse) en secondes source ; en v1 un morceau accéléré consomme (fin - début) × vitesse
for m in v1["morceaux"]:
    a = m["source_debut"] / fps
    garde.append((a, a + (m["source_fin"] - m["source_debut"]) * m["vitesse"] / fps, m["vitesse"]))

# Voix interdite : coups de colère (coupes libres, moments forts M coupés)
colere = [(a, b) for a, b, *_ in dec.get("coupes_libres", [])]
colere += [(props[i]["debut"], props[i]["fin"]) for i in dec.get("couper", []) if props.get(i, {}).get("cat") == "M"]
colere = union(colere)

# --- 1. Morts visibles
video = union([(a, b) for a, b, _ in garde])
accel = [(a, b, v) for a, b, v in garde if v != 1]
ajouts = []
evts = t.lire("analyse/evenements.json") if (t / "analyse/evenements.json").exists() else []
kills = [(e["debut"] - 1.0, e["fin"]) for e in evts if e["type"] == "kill"]   # tes kills (fenêtre HUD de 5 s)
fenetres = [(a - AVANT_MORT, a + APRES_MORT) for a, _ in morts] + [(a - 5.0, b + 2.0) for a, b in kills]
for fenetre in fenetres:
    # on comble aussi un petit trou juste avant (pas de saut d'image à 2 s de la mort)
    avant = [b for x, b in video if b <= fenetre[0] and fenetre[0] - b < COMBLER]
    if avant:
        fenetre = (max(avant), fenetre[1])
    manque = moins([fenetre], video)
    if manque:
        ajouts += manque
video = union(video + ajouts)
voix_muette = [z for z in ajouts]  # par défaut, la voix des passages rajoutés n'est gardée que hors colère
voix_ok_ajouts = moins(ajouts, colere)
voix_muette = moins(voix_muette, voix_ok_ajouts)

# --- 2. Retours à la base
coupes_retour, accel_retour, journal = [], [], []
for r in retours:
    d, f = r["debut"], r["fin"]
    choix = choix_retours.get(f"{d}", "auto")
    zone = [(max(a, d), min(b, f)) for a, b in video if min(b, f) > max(a, d)]
    zone = [z for z in zone if not any(z[0] < y and z[1] > x for x, y, _ in accel)]
    if choix == "garder" or not zone:
        continue
    zone = voix_entiere(zone, marges=True)  # jamais une phrase coupée (ni mangée par un fondu) au bord du retour
    for a, b in zone:
        parole = [(x, y) for x, y in phrases if x >= a - 0.05 and y <= b + 0.05]
        if choix == "couper" or not parole:
            if b - a < COUPE_MIN:
                continue
            coupes_retour.append((a, b))
            journal.append(f"{r['type']} {a:.1f}-{b:.1f} : coupé ({b - a:.1f} s, pas de commentaire)")
            continue
        # a) long silence coupé
        bords = [a] + [v for p in parole for v in p] + [b]
        silences = [(bords[i], bords[i + 1]) for i in range(0, len(bords), 2)]
        for x, y in silences:
            if y - x >= SILENCE_COUPE:
                cx, cy = (x + MARGE if x > a else x), (y - MARGE if y < b else y)
                coupes_retour.append((cx, cy))
                journal.append(f"{r['type']} {cx:.1f}-{cy:.1f} : silence coupé ({cy - cx:.1f} s)")
        reste = moins([(a, b)], [c for c in coupes_retour if a <= c[0] < b])
        # b) le reste accéléré, la voix à vitesse normale
        for x, y in reste:
            p = [(u, w) for u, w in parole if u >= x - 0.05 and w <= y + 0.05]
            if not p:
                continue
            besoin = sum(w - u for u, w in p) + ECART_VOIX * len(p) + 0.4
            v = min(VIT_MAX, (y - x) / besoin)
            v = int(v * 20) / 20  # pas de 5 %
            if v >= 1.2 and (y - x) * (1 - 1 / v) >= GAIN_MIN:
                accel_retour.append((x, y, v))
                journal.append(f"{r['type']} {x:.1f}-{y:.1f} : accéléré ×{v:g}, voix normale "
                               f"(gain {(y - x) * (1 - 1 / v):.1f} s)")

video = moins(video, coupes_retour)
accel = accel + accel_retour


def dans_colere(d, f):
    return any(d < y and f > x for x, y in colere)


# Marge de silence autour des phrases aux bords des coupes (sinon le fondu audio mange le dernier mot)
etendu = []
for a, b in video:
    for i, (d, f) in enumerate(phrases):
        if dans_colere(d, f):
            continue
        suiv = phrases[i + 1][0] if i + 1 < len(phrases) else f + 5
        prec = phrases[i - 1][1] if i > 0 else d - 5
        if b - 0.6 < f <= b + 0.05 or d < b < f:       # phrase qui finit au ras de la coupe (ou la chevauche)
            b = max(b, min(f + MARGE_FIN_PHRASE, suiv - 0.05))
        if a - 0.05 <= d < a + 0.3 or d < a < f:          # phrase qui commence au ras de la coupe
            a = min(a, max(d - MARGE_DEBUT_PHRASE, prec + 0.05))
    etendu.append((a, b))
video = union(etendu)

# --- 3. Morceaux finaux, découpés aux bords des accélérations
bornes = sorted({v for a, b, _ in accel for v in (a, b)})
morceaux = []
for a, b in video:
    pts = [a] + [x for x in bornes if a < x < b] + [b]
    for x, y in zip(pts, pts[1:]):
        if y - x < 0.1:
            continue
        v = next((vv for aa, bb, vv in accel if aa <= x + 1e-6 and y <= bb + 1e-6), 1)
        morceaux.append({"src": [round(x, 3), round(y, 3)], "vitesse": v})

record = 0.0
for m in morceaux:
    x, y = m["src"]
    v = m["vitesse"]
    duree = (y - x) / v
    if v == 1:
        zones = voix_entiere(moins([(x, y)], voix_muette + colere))
        m["voix"] = [{"src": [round(a, 3), round(b, 3)], "decalage": round(a - x, 3)} for a, b in zones]
    else:
        # phrases posées à leur place « proportionnelle », sans se chevaucher, et tassées à la fin si besoin
        p = [(u, w) for u, w in phrases if u >= x - 0.05 and w <= y + 0.05 and not any(u < cy and w > cx for cx, cy in colere)]
        poses, t0 = [], 0.15
        for u, w in p:
            dec_ = max(t0, (u - x) / v)
            poses.append([u, w, dec_])
            t0 = dec_ + (w - u) + ECART_VOIX
        deb = duree - 0.15
        for q in reversed(poses):  # si ça déborde, on recule depuis la fin
            if q[2] + (q[1] - q[0]) > deb:
                q[2] = deb - (q[1] - q[0])
            deb = q[2] - ECART_VOIX
        # chaque phrase garde un peu de silence autour d'elle (le fondu tombe dans le silence, pas sur un mot)
        voix = []
        for k, (u, w, d_) in enumerate(poses):
            prec = poses[k - 1][1] if k else u - 1
            suiv = poses[k + 1][0] if k + 1 < len(poses) else w + 1
            pu = max(u - 0.1, prec + 0.05, x)
            pw = min(w + 0.3, suiv - 0.05, y)
            voix.append({"src": [round(pu, 3), round(pw, 3)], "decalage": round(max(0, d_ - (u - pu)), 3)})
        m["voix"] = voix
    m["record_s"] = round(record, 3)
    m["duree_s"] = round(duree, 3)
    record += duree

t.ecrire("propositions/plan_v2.json", {"fps": fps, "duree_s": round(record, 2), "morceaux": morceaux,
                                        "journal": journal, "morts_rajoutees": [[round(a, 2), round(b, 2)] for a, b in ajouts]})
print(f"Plan v2 : {len(morceaux)} morceaux, {record / 60:.0f} min {record % 60:04.1f} s "
      f"(v1 : {v1['duree_finale_s'] / 60:.0f} min {v1['duree_finale_s'] % 60:04.1f} s)")
print("Morts rendues visibles :", [[round(a, 1), round(b, 1)] for a, b in ajouts])
print("\n".join(journal))
