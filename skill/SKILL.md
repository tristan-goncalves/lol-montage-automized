---
name: montage-lol
description: Monte une partie de League of Legends commentée de Tristan dans DaVinci Resolve, de l'analyse du rush à l'export (coupes, marqueurs, runes, intros, musique, effets sonores), en suivant son guide de style. Se déclenche quand Tristan donne une vidéo à monter, parle de montage LoL, de rush, d'intro, de runes ou fait un retour sur un montage.
---

# Montage LoL — process de référence

Tu montes les parties commentées de Tristan. Tiens-le au courant à chaque étape par un message court : ne travaille jamais longtemps en silence. **Il est le directeur du montage** : tu analyses, tu proposes, il valide, tu appliques. Rien n'est coupé sans son accord. Réponds en français, simplement, et sois honnête sur ce qui n'a pas marché.

## 0. Avant toute chose
1. Le dépôt vit sur son PC : `C:\Users\Tristan\Videos\Records\lol-montage-automized` (dans Cowork : `~/mnt/Records/lol-montage-automized`). Si le dossier Records n'est pas connecté, demande-le (device_request_folder_access).
2. Lis, dans cet ordre : `docs/guide_montage.md` (ses règles de style — elles priment sur tes goûts), `docs/technique.md` (pièges Resolve / MCP), le dernier fichier de `docs/journal/`.
3. Vérifie les outils : `device_bash` (scripts), outils `davinci-resolve__*` (Resolve doit être ouvert ; sinon `resolve_control launch` ou demande à Tristan de l'ouvrir).
4. Dépendances Python sur la machine Cowork (une fois) : `pip install -r requirements.txt`. Les scripts se lancent depuis le dépôt : `cd ~/mnt/Records/lol-montage-automized && python3 scripts/<script>.py "<vidéo>"`.
5. Crée une liste de tâches avec les étapes ci-dessous.

## 1. Préparer
- `python3 scripts/01_preparer.py "<vidéo>"` : vérifie 2 pistes audio, 1080p60, extrait `audio/jeu.wav` et `audio/micro.wav` dans `_montage/<vidéo>/`.
- S'il n'y a qu'une piste audio : arrête-toi et explique (OBS : piste 1 = jeu, piste 2 = micro).

## 2. Analyser
**Contrainte Cowork** : chaque appel `device_bash` est coupé au bout de 3 min et **rien ne survit en arrière-plan** (pas de nohup / setsid). Les scripts longs travaillent donc par tranches : relance-les tant qu'ils affichent « À RELANCER » (ils reprennent où ils s'étaient arrêtés). Tiens Tristan au courant entre deux passes.
1. `python3 scripts/03_analyser_jeu.py "<vidéo>" --budget 150` → volume, écrans noirs, HUD (KDA, kills d'équipe), morts avec leur durée. ~3 passes pour 27 min de vidéo.
   - Contrôle : les kills / morts trouvés doivent correspondre au KDA final. Signale tout écart au lieu de le cacher.
   - Si la lecture du HUD se trompe (nouvelle interface, autre résolution) : ajouter des exemples étiquetés dans `scripts/hud_ocr.py` (EXEMPLES) dans `templates/hud_exemples/`, réapprendre (`python3 scripts/hud_ocr.py apprendre`), puis relire sans repasser sur la vidéo (`03_analyser_jeu.py "<vidéo>" --relire-hud`).
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

- **Découper le rush pour la revue** : couper V1/A1/A2 au début et à la fin de chaque marqueur C/D (voir `docs/technique.md`, « Rush annoté découpé »). Tristan relit une proposition en cliquant sa ligne dans Index > Marqueurs, puis X (Marquer le clip) et Alt+/ (Lire de l'entrée à la sortie) : la lecture s'arrête pile à la fin.


### Revue par Tristan (outils en place)
- Scripts Resolve (Workspace > Scripts > Edit, sources dans `resolve/`) : « Revue 0 Marquer » (entrée/sortie sur le marqueur), « Revue 1 Couper » (rouge), « Revue 2 Accelerer » (cyan), « Revue 3 Garder » (vert). Les scripts de couleur passent au marqueur suivant et posent l'entrée/sortie. Installer/mettre à jour avec `script_plugin install` (catégorie Edit).
- `resolve/revue_resolve.ahk` (AutoHotkey v2) : Maj+Espace = F9 (Revue 0 Marquer) puis F10 (Play In to Out).
- Moments forts M en rouge = coupés. Intros (> 2 min) : décision dans le chat.
- Passe « coups de colère » sur la transcription (règle du guide) → `coupes_libres` dans `decisions.json`, jamais au milieu d'une phrase.

## 5. Monter la v1
1. **Décisions par couleur de marqueur** (méthode par défaut) : Tristan change la couleur des marqueurs de « 00 Rush annoté » dans Resolve — coupes : Rouge = couper, Vert = garder, Cyan = accélérer ×2, Jaune = pas décidé (gardé) ; idées / intros : Vert = je prends, Rouge = non ; déplacer / rallonger un marqueur = ajuster la coupe. Quand il dit « c'est bon » :
   - `timeline_markers get_all` sur « 00 Rush annoté », puis écris `propositions/marqueurs_resolve.json` au format `{"<frame>": {"color", "duration", "name"}}` (3 champs suffisent) ;
   - `python3 scripts/decisions_depuis_resolve.py "<vidéo>"` → `decisions.json` + résumé (à lui montrer : combien coupé / gardé / accéléré, idées retenues, ajustements) ;
   - s'il répond plutôt par numéros dans le chat, écris `decisions.json` toi-même (`couper`, `accelerer`, `garder`, `ajustements`).
   Puis `python3 scripts/05_plan_montage.py "<vidéo>"` → `plan_v1.json`.
   Puis `python3 scripts/06_retours_base.py "<vidéo>"` (backs sur la minimap) et `python3 scripts/07_plan_v2.py "<vidéo>"` → `plan_v2.json` (morts toujours visibles, backs coupés ou accélérés voix normale). Montre à Tristan le journal imprimé.
2. Écris `propositions/intro_vN.json` (extraits de l'intro, effets sur les kills — **pas de jingle Victory** —, titre `jusqua: fin_voix`, `prolonger_s` ≈ 2,5 sur le dernier extrait pour que le fondu commence après la dernière phrase) et `habillage_vN.json` (positions en secondes source ; runes = clip pré-rendu `runes_ombre.mov` + `rune_sfx.wav` ; S'abonner en bas au centre ×1,4). Lance `python3 scripts/zooms_hud.py "<vidéo>" --kda <s>` (zooms kill feed 1,5 s en lane, zoom KDA), vérifie l'alpha des .mov, puis `python3 scripts/08_construction_v2.py "<vidéo>" --version vN` (fondus adaptatifs, coupes du micro calées sur l'énergie de la voix ; lis son journal : les coupes « à vérifier » deviennent des marqueurs violets « À écouter »). Construis **une seule timeline plate** « 0N Montage vN » (pistes V1 Jeu / V2 Habillage, A1 Son du jeu / A2 Micro / A3 Musique / A4 Effets) : `append_to_timeline` par piste, `set_speed` sur vidéo **et** son du jeu des morceaux accélérés, `set_fades` sur **chaque** élément audio (valeurs de `construction_vN.json` pour le micro ; jeu 8, 15 autour des accélérations), fondu au noir en fin d'intro. Marqueurs via `apply_spec` (cyan accélérations, jaune kills/morts rendus visibles, rouge coupes, violet à écouter). Vérifie par captures (titre, runes, S'abonner, chaque zoom, kills) et par un rendu court de l'intro dont tu mesures le son à la fin de la dernière phrase.
3. Niveaux : copies `micro_mix.wav` (-16 LUFS) et `jeu_mix.wav` (-24) faites avec ffmpeg puis `replace_clip` (voir technique.md, « Montage v1 ») — pas de normalisation Resolve sur des morceaux.
4. Vérifie la durée finale contre l'estimation et montre 2-3 images clés (`timeline_frame capture`).

## 6. Intro
- L'intro est construite dans la même timeline que la partie (pas d'imbrication : Tristan relit et retouche dans Edit). Cuts dans les silences entre phrases, effets sonores sur les kills, Victory seulement sur « VICTOIRE », « Dans cette vidéo… » en haut à gauche, long fondu au noir puis fondu depuis le noir.
- Habillage sobre (guide) : runes à 5 s, « S'abonner » quand Tristan explique le matchup, musique d'ambiance -33 LUFS sous toute la partie, quelques jingles à -30.
- Musique et effets : choisis dans `_montage/catalogue_sons.csv` (type, durée, tempo) et **applique le gain conseillé**. Musique en copie pré-baissée (-33 LUFS), effets normalisés à -30.
- Titres : écris `habillage/titres.json` puis `python3 scripts/titres.py "<vidéo>"` → clips `.mov` transparents à poser sur V3. Style sobre (retour de Tristan).
- Ralenti : plage source double puis `set_speed 50` + `set_retime optical_flow`. Vérifie que le plan ralenti montre bien l'action (pas le tableau des scores).

## 7. Runes
- Importer `templates/Template Runes.drt` (ou la timeline « Template Runes » du projet). Dis à Tristan de remplacer les images (clic droit sur l'image dans 04 Runes > Replace Clip) **avant** le rendu.
- Gigotement : si les comps Fusion manquent après import du .drt, `timeline_item_fusion import_comp` avec `templates/runes_comps/rune1..9.comp` (une par piste ; amplitudes finales validées le 29/09). Vérifie avec `export_comp`.
- Rends « Template Runes » en QuickTime ProRes 4444 avec `ExportAlpha: true` (MarkIn/MarkOut = les 5 s) → `habillage/runes_brut.mov`, puis `python3 scripts/runes_habillage.py habillage/runes_brut.mov habillage/runes_ombre.mov` (ombre contour + fondus). Pose le clip sur V2 5 s après le début de la partie (Pan 20, Tilt −180) avec `rune_sfx.wav` (Fleet Footwork) sur A4 0,24 s avant. Jamais la timeline imbriquée dans le montage (elle fait ramer la lecture).

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
