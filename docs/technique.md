# Notes techniques — Resolve, MCP et pièges connus

Tout ce qui a été appris en le cassant au moins une fois. À relire avant de toucher à Resolve.

## Environnement
- **DaVinci Resolve Studio 21.1** (scripting externe activé : Préférences > Système > Général > « External scripting using : Local »).
- **MCP** : [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp), installé dans `D:\Logiciels\davinci-resolve-mcp`, déclaré dans Claude Desktop. Les outils apparaissent sous `davinci-resolve__*` (timeline, timeline_item, media_pool, fusion_comp, render, project_manager…).
- Resolve doit être **ouvert** avec le bon projet. Si un outil répond « Not connected » : `resolve_control launch`.
- La machine Linux de Cowork voit le dossier Records dans `~/mnt/Records` ; Resolve (Windows) le voit dans `C:\Users\Tristan\Videos\Records`. `commun.vers_windows()` fait la traduction.

## Contraintes de Cowork (machine Linux sur le PC)
- Chaque commande est coupée au bout de **3 minutes**, et tout processus lancé en arrière-plan meurt avec elle (bac à sable `--die-with-parent`). → Scripts par tranches, relancés tant qu'ils affichent « À RELANCER ».
- **Pas de suppression** de fichiers dans les dossiers connectés (sauf autorisation explicite). Conséquence : `git` ne marche pas depuis Cowork (il doit supprimer ses fichiers `index.lock`) → commits et push faits par Tristan sous Windows. Ne lancer AUCUNE commande git depuis Cowork, même `git status` : elle laisse un `.git/index.lock` impossible à supprimer qui bloque ensuite git sous Windows.
- Envoi de fichiers du cloud vers le PC (`device_commit_files`) : utiliser un **nom de staging unique** à chaque envoi, sinon une ancienne version peut être réécrite. Vérifier avec `md5sum`.
- 2 cœurs seulement : la transcription se fait plutôt dans l'espace de travail cloud (audio exporté en `.opus` de ~3 Mo).

## Son
- **Ne jamais importer de FCPXML / XML** : le son arrive fusionné (jeu en mono gauche/droite, voix perdue). Toujours extraire `jeu.wav` et `micro.wav` (script 01) et les poser nous-mêmes sur A1 / A2.
- **Volume d'un clip** : `timeline_item set_audio Volume` ne marche pas (renvoie false). Utiliser `timeline normalize_audio_level(item_ids, {"normalizationMode": "ITU-R BS.1770-4", "targetLoudness": -16})`. Les ID sont ceux des **éléments de timeline**, pas des médias.
- **Cible minimum -30 LUFS** : au-dessous, la normalisation échoue sans message. Pour la musique (-36), fabriquer une copie pré-baissée avec ffmpeg (`volume=-XdB`) et la poser sans normalisation.
- Un effet court (impact, whoosh) **paraît plus fort** que sa mesure : viser 6 à 8 dB sous la voix.
- **Toujours vérifier** par un rendu MP4 + `scripts/controle_audio.py`. On ne peut pas lire le volume d'un clip par l'API.
- Fondus audio : `timeline_item set_fades {"FadeIn": 5, "FadeOut": 5}` fonctionne (lecture avec `get_fades`).

## Placer des clips
- `media_pool append_to_timeline` avec `clip_infos` : `{clip_id, start_frame, end_frame, record_frame, track_index, media_type}` — **end_frame exclusif**, record_frame relatif au début de la timeline, media_type 1 = vidéo, 2 = audio.
- `create_timeline_from_clips` exige un `record_frame` dans chaque clip_info.
- Une nouvelle timeline commence à l'image 216000 (01:00:00:00) : les lectures (`get_items`) sont en images **absolues**.
- **Images fixes** : forcées à 300 images (5 s) quelle que soit la durée demandée. Pour une autre durée → en faire un clip vidéo (ffmpeg).
- Le dossier courant du panneau des médias peut changer tout seul (l'archivage automatique y touche) : **refaire `set_current_folder` juste avant chaque import**.
- Les transitions comptent comme des éléments dans l'index d'une piste : après en avoir ajouté, les `item_index` se décalent. Ajouter les transitions **de la fin vers le début**.

## Transformations, vitesse, transitions
- `set_transform` marche (Pan, Tilt, ZoomX, ZoomY, RotationAngle).
- **Pan n'est pas en pixels** : pour décaler de `x` px horizontalement, `Pan = x / 0.5625`. Tilt est en pixels (positif = vers le haut).
- Une image fixe est d'abord mise à l'échelle pour remplir la hauteur (1080 px) : `Zoom = taille voulue en px / 1080`.
- **Vitesse** : `set_speed {"Percentage": 50, "RippleTimeline": false}` (la clé « Speed » est refusée). La durée de l'élément est conservée, c'est la quantité d'images source consommée qui change.
  - Ralenti à 50 % d'un passage de N images : poser la plage source `[début, début + 2N[` (durée 2N), puis passer à 50 % → l'élément dure 2N et montre les N premières images.
  - Accélération ×2 d'un passage de N images : poser `[début, début + N/2[`, puis passer à 200 % → l'élément dure N/2 et montre les N images (c'est ce que fait `05_plan_montage.py`).
- Qualité du ralenti : `set_retime {"process": "optical_flow", "motion_estimation": 6}`.
- **Transitions** : `add_transition {"type": "Cross Dissolve", "category": "simple", "position": "start", "alignment": "center", "duration": 8}` (clés en minuscules). Il faut de la matière avant/après la coupe (poignées).
- **Points d'animation (keyframes)** : `timeline_item add_keyframe` plante (« 'NoneType' object is not callable ») sur cette version. Contournement : Fusion (ci-dessous).

## Fusion
- Un comp Fusion ajouté par l'API **est bien rendu** si le graphe va de MediaIn à MediaOut : `timeline_item_fusion add_comp` → `fusion_comp add_tool Transform` → `connect` MediaIn1 → outil → MediaOut1.
- Les **expressions** passent par `fusion_comp bulk_set_expressions` (ex. `Center = Point(0.5 + 0.007*sin(time*0.2), 0.5 + …)`). C'est ce qui fait gigoter les runes.
- Ne jamais écrire une valeur de paramètre sous `Comp.Lock()` : elle se relit mais n'est pas rendue.
- Toujours prouver un effet Fusion par une image rendue (`timeline_frame capture`), jamais par une relecture.

## Titres
- `insert_fusion_title` insère à la **tête de lecture** sur la piste active, pas à l'endroit demandé, et `move_clips` ne sait pas déplacer un titre. → On fabrique les titres en `.mov` ProRes 4444 transparents (`scripts/titres.py`) et on les place comme des clips.

## Rendu
- `render prepare_render_job` avec `require_temp_target: false` pour écrire dans le dossier de la vidéo. Toujours passer `ExportVideo`, `ExportAudio`, `AudioCodec` : les réglages de la page Deliver déjà chargés sont hérités sinon.
- `render verify_output` pour vérifier que le fichier contient vidéo **et** son.
- `timeline_frame capture` (qualité `frame` ou `preview`) pour voir une image précise.

## Versionnage automatique
- Chaque opération destructive archive la timeline (`<nom>_archived_vNN`). Encadrer une série de modifications par `timeline_versioning begin_run` / `end_run` pour n'avoir qu'une archive.
- Les archives atterrissent parfois dans le dossier courant : les ranger ensuite dans « Archive » (`media_pool move_clips`).

## Export / import de timelines
- `timeline export_timeline_checked {"export_type": "EXPORT_DRT", "require_temp_path": false}` écrit un `.drt`. Import dans un autre projet : File > Import > Timeline. **Non vérifié** : que les comps Fusion (gigotement des runes) soient inclus dans le `.drt`.

## Analyse
- faster-whisper (modèle `small`, français, horodatage par mot) : bon compromis. Il étire parfois un mot sur plusieurs secondes → durée d'un mot bornée à 2,5 s.
- HUD (1080p) : zone x 1540, y 0, 380×32 px. **Pas de tesseract** : il confond le 5 avec 3 ou 9 sur cette police. Lecture par comparaison à des modèles de caractères (`scripts/hud_ocr.py`, modèles dans `templates/hud_caracteres.json`, 0 erreur sur 32 valeurs de test). Une valeur n'est retenue que si elle est lue deux fois de suite et ne décroît jamais.
- Morts : départ = mort lue dans le KDA, recalée sur le moment où la saturation relative passe sous 0,7 ; fin = saturation relative > 0,95 pendant 2 s (réapparition). Précision constatée : ±1 s sur les 5 morts du 17/08.
- Décalage observé sur la partie du 17/08 : horloge du jeu = temps vidéo + 37 s (dépend du moment où OBS a été lancé).
