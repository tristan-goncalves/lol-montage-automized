# lol-montage

Montage assisté par IA des parties de League of Legends commentées de Tristan : Claude analyse le rush,
propose les coupes et une intro, Tristan valide, puis Claude applique le montage dans **DaVinci Resolve**
via son MCP (runes, musique, effets sonores, titres, export).

Le dépôt contient **le process, les règles et le code** — jamais les médias.

## Comment ça marche

```
Rush OBS (.mp4, piste 1 = jeu, piste 2 = micro)
   │
   ├─ 01_preparer        vérifie la vidéo, extrait jeu.wav / micro.wav
   ├─ 02_transcrire      transcription horodatée de ta voix (faster-whisper)
   ├─ 03_analyser_jeu    volume, morts (écran gris), écrans noirs, KDA lu dans le HUD
   ├─ 04_propositions    coupes évidentes / à discuter / moments forts / idées + marqueurs
   │        ⏸  Tristan valide par numéro
   ├─ 05_plan_montage    décisions → plan de timeline (images exactes, accélérations)
   │
   └─ Resolve (Claude via MCP) : rush annoté, montage v1, intro, runes, mix, contrôle, export
```

Le déroulé complet, étape par étape, est dans [skill/SKILL.md](skill/SKILL.md).

## Organisation

| Dossier | Contenu |
|---|---|
| `skill/` | Le skill Claude : le process de référence |
| `docs/guide_montage.md` | Le style de Tristan (règles éditoriales), enrichi à chaque retour |
| `docs/technique.md` | Pièges Resolve / MCP et leurs solutions |
| `docs/journal/` | Une fiche par vidéo : propositions, décisions, retours |
| `config/reglages.yaml` | Tous les réglages chiffrés (marges de coupe, niveaux sonores, zone du HUD…) |
| `scripts/` | Un script par étape + outils (catalogue des sons, titres, contrôle audio) |
| `templates/` | Template de runes Resolve (.drt), polices des titres |

Les fichiers de travail de chaque vidéo sont créés **hors du dépôt**, dans `Records/_montage/<vidéo>/`
(`audio/`, `analyse/`, `propositions/`, `habillage/`, `exports/`).

## Installation

1. Python 3.10+, [ffmpeg](https://ffmpeg.org/) et [tesseract](https://github.com/tesseract-ocr/tesseract) dans le PATH.
2. `pip install -r requirements.txt`
3. DaVinci Resolve Studio avec le scripting externe activé et le MCP
   [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) déclaré dans Claude Desktop.
4. Vérifier les chemins dans `config/reglages.yaml`.

## Utilisation

Dans Cowork, avec le dossier Records connecté et Resolve ouvert :

> « Monte-moi la partie `2026-09-30 21-14-02.mp4` »

Claude suit le skill : analyse, rapport de propositions, puis montage après ta validation.
Tes retours (« les effets sont trop forts », « coupe moins près des kills »…) sont notés dans le guide
et le journal : le montage suivant en tient compte.

Les scripts se lancent aussi à la main : `python scripts/01_preparer.py "<vidéo.mp4>"`.

## Bibliothèque sonore

`python scripts/catalogue_sons.py` mesure tous les sons du dossier `Musiques` (type, durée, volume,
attaque, brillance, tempo) et calcule le gain à appliquer pour que chaque son tombe au bon niveau
sous la voix. À relancer après chaque ajout de fichiers.
