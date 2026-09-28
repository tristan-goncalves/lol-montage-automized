---
name: montage-lol
description: Monte une partie de League of Legends commentée de Tristan dans DaVinci Resolve, de l'analyse du rush à l'export (coupes, marqueurs, runes, intros, musique, effets sonores), en suivant son guide de style. Se déclenche quand Tristan donne une vidéo à monter, parle de montage LoL, de rush, d'intro, de runes ou fait un retour sur un montage.
---

# Montage LoL — process de référence

Tu montes les parties commentées de Tristan. **Il est le directeur du montage** : tu analyses, tu proposes, il valide, tu appliques. Rien n'est coupé sans son accord. Réponds en français, simplement, et sois honnête sur ce qui n'a pas marché.

## 0. Avant toute chose
1. Le dépôt vit sur son PC : `C:\Users\Tristan\Videos\Records\lol-montage` (dans Cowork : `~/mnt/Records/lol-montage`). Si le dossier Records n'est pas connecté, demande-le (device_request_folder_access).
2. Lis, dans cet ordre : `docs/guide_montage.md` (ses règles de style — elles priment sur tes goûts), `docs/technique.md` (pièges Resolve / MCP), le dernier fichier de `docs/journal/`.
3. Vérifie les outils : `device_bash` (scripts), outils `davinci-resolve__*` (Resolve doit être ouvert ; sinon `resolve_control launch` ou demande à Tristan de l'ouvrir).
4. Dépendances Python sur la machine Cowork (une fois) : `pip install -r requirements.txt`. Les scripts se lancent depuis le dépôt : `cd ~/mnt/Records/lol-montage && python3 scripts/<script>.py "<vidéo>"`.
5. Crée une liste de tâches avec les étapes ci-dessous.

## 1. Préparer
- `python3 scripts/01_preparer.py "<vidéo>"` : vérifie 2 pistes audio, 1080p60, extrait `audio/jeu.wav` et `audio/micro.wav` dans `_montage/<vidéo>/`.
- S'il n'y a qu'une piste audio : arrête-toi et explique (OBS : piste 1 = jeu, piste 2 = micro).

## 2. Analyser
**Contrainte Cowork** : chaque appel `device_bash` est coupé au bout de 3 min et **rien ne survit en arrière-plan** (pas de nohup / setsid). Les scripts longs travaillent donc par tranches : relance-les tant qu'ils affichent « À RELANCER » (ils reprennent où ils s'étaient arrêtés). Tiens Tristan au courant entre deux passes.
1. `python3 scripts/03_analyser_jeu.py "<vidéo>" --budget 150` → volume, écrans noirs, HUD (KDA, kills d'équipe), morts avec leur durée. ~3 passes pour 27 min de vidéo.
   - Contrôle : les kills / morts trouvés doivent correspondre au KDA final. Signale tout écart au lieu de le cacher.
   - Si la lecture du HUD se trompe (nouvelle interface, autre résolution) : ajouter des exemples étiquetés dans `scripts/hud_ocr.py` (EXEMPLES) et réapprendre (`python3 scripts/hud_ocr.py apprendre <dossier d'images>`).
2. Transcription — **dans l'espace de travail cloud** (plus rapide, faster-whisper déjà installable) :
   - sur le PC : `python3 scripts/02_transcrire.py "<vidéo>" --exporter-audio` → `audio/micro.opus` (~3 Mo) ;
   - `device_stage_files` de `micro.opus`, `scripts/02_transcrire.py` et `config/reglages.yaml`, puis dans le cloud : `pip install faster-whisper` et `python3 scripts/02_transcrire.py --audio micro.opus --sortie transcription.json` (lancer en arrière-plan côté cloud et surveiller : ~10-20 min pour 30 min d'audio) ;
   - recopier `transcription.json` dans `analyse/` (device_commit_files, **nom de fichier de staging unique** : un nom déjà utilisé peut renvoyer l'ancienne version) ;
   - sur le PC : `python3 scripts/02_transcrire.py "<vidéo>"` → `transcription.txt` et `parole.json`.
   - Repli : transcription sur le PC par tranches (`--budget 150`, après `pip install --user faster-whisper`), lent sur 2 cœurs.

## 3. Proposer — puis attendre Tristan
1. Lis `analyse/transcription.txt` en entier : c'est là que tu comprends l'histoire de la partie (tournants, phrases drôles, frustration).
2. Écris `propositions/idees.json` : `[{"debut": s, "fin": s, "texte": "..."}]` avec
   - **3 intros de 15 à 25 s** (storytelling, spectaculaire, humour), chacune = liste de plans (timecodes + phrase dite + pourquoi) ;
   - les idées d'habillage : zoom KDA, jingle Pokémon sur un kill, musique d'ambiance sur les phases calmes (choisie dans `_montage/catalogue_sons.csv`), texte ou mème, fin sur « S'abonner ».
3. `python3 scripts/04_propositions.py "<vidéo>"` → `propositions/rapport.md` (tableaux C / D / M / I, durée estimée) et `propositions/marqueurs.json`.
4. Relis les coupes D : complète leur raison à partir de la transcription (le script ne comprend pas le sens). Supprime ce qui contredit le guide.
5. Les scripts ne coupent que des silences : ils retirent ~10 % (27 min → ~24 min). Pour approcher l'objectif (~20 min), c'est à toi de proposer, à partir de la transcription, des coupes **de contenu** en D (digressions, commentaires trop longs pendant une mort, fin de partie qui traîne), avec la phrase clé à garder.
6. Présente à Tristan un résumé court (durées, points à trancher, 3 intros) et demande ses décisions **par numéro** (« C OK sauf C4, D2 accélérer, intro A »). **Arrête-toi là tant qu'il n'a pas répondu.**

## 4. Resolve — projet et rush annoté
- Projet : un par vidéo (nom = vidéo) sauf consigne contraire. Dossiers : `01 Rushes`, `02 Timelines`, `03 Habillage`, `04 Runes`, `Archive` (`media_pool add_subfolder`).
- Importer dans `01 Rushes` : la vidéo, `jeu.wav`, `micro.wav` (chemins Windows — `set_current_folder` juste avant chaque import).
- Timeline « 00 Rush annoté » : vidéo sur V1, jeu.wav sur A1, micro.wav sur A2 (append_to_timeline, media_type 1 / 2), **jamais le son intégré de la vidéo**. Nommer les pistes (Gameplay / Jeu / Micro).
- Marqueurs : `project_manager apply_spec` avec `{"project": ..., "timelines": [{"name": "00 Rush annoté", "markers": <marqueurs.json>}]}`.
- Encadre chaque série de modifications par `timeline_versioning begin_run` / `end_run`.

## 5. Monter la v1
1. Traduis ses réponses en `propositions/decisions.json` (`couper`, `accelerer`, `garder`, `ajustements`) puis `python3 scripts/05_plan_montage.py "<vidéo>"` → `plan_v1.json`.
2. Nouvelle timeline « 01 Montage v1 » : pour chaque morceau, vidéo V1 + jeu A1 + micro A2 aux images du plan ; morceaux `vitesse: 2` → vidéo seule puis `set_speed {"Percentage": 200}`.
3. Fondus audio de 5 images sur chaque morceau (`set_fades`), niveaux : `normalize_audio_level` micro -16, jeu -24.
4. Vérifie la durée finale contre l'estimation et montre 2-3 images clés (`timeline_frame capture`).

## 6. Intro
- Construis l'intro choisie dans sa propre timeline (« Intro <style> »), puis place-la en tête de la v1.
- Musique et effets : choisis dans `_montage/catalogue_sons.csv` (type, durée, tempo) et **applique le gain conseillé**. Musique en copie pré-baissée (-36 LUFS), effets normalisés à -30.
- Titres : écris `habillage/titres.json` puis `python3 scripts/titres.py "<vidéo>"` → clips `.mov` transparents à poser sur V3. Style sobre (retour de Tristan).
- Ralenti : plage source double puis `set_speed 50` + `set_retime optical_flow`. Vérifie que le plan ralenti montre bien l'action (pas le tableau des scores).

## 7. Runes
- Importer `templates/Template Runes.drt` (ou la timeline « Template Runes » du projet) et le poser au début de la partie sur V2.
- Dis à Tristan de remplacer les images (clic droit sur l'image dans 04 Runes > Replace Clip). Si le gigotement a disparu après import du .drt, remets les comps Fusion (voir technique.md, section Fusion).

## 8. Contrôle et export
- Rendu de contrôle MP4 (`render prepare_render_job` avec ExportVideo/ExportAudio explicites, `require_temp_target: false`, puis `start` et `verify_output`).
- `python3 scripts/controle_audio.py "<rendu.mp4>"` : aucune alerte tolérée sur les effets au-dessus de la voix. Corrige, re-rends, re-mesure.
- Export final quand Tristan valide.

## 9. Retour et apprentissage (à chaque fois)
- Chaque retour de Tristan → une ligne dans le « Journal des règles » de `docs/guide_montage.md`, et la règle elle-même dans la bonne section si elle change.
- Écris / complète `docs/journal/<date>_<champion>.md` : la partie, les propositions, ses décisions, ses retours, les problèmes.
- Un nouveau piège technique → `docs/technique.md`. Un réglage chiffré → `config/reglages.yaml`.
- Termine par le message de commit proposé (Tristan fait le push). Si le **process** lui-même change (pas juste une règle), propose une mise à jour de ce skill.

## Rappels
- Ne lance jamais de commande git depuis Cowork (voir technique.md) : Tristan committe et pousse sous Windows.
- Ne publie jamais de médias dans le dépôt (vidéos, sons, artworks) : le `.gitignore` les exclut.
- Si une étape échoue, dis-le clairement, propose un contournement, ne maquille pas un résultat.
