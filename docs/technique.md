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
- Score d'équipe : ton équipe est TOUJOURS en bleu, mais à gauche ou à droite selon le côté de la carte → rangement par couleur, pas par position (partie du 29/09 jouée de l'autre côté).
- KDA à 2 chiffres (« 9/14/12 ») : zone élargie à 118-210 px.
- Horloge du jeu vs temps vidéo : +37 s le 17/08, +12 s le 29/09 → dépend de chaque enregistrement.
- Fin de partie : si tu es mort au moment de la victoire, l'écran reste gris jusqu'au Nexus ; ne pas couper la chute du Nexus en coupant « la mort ».
- Morts : départ = mort lue dans le KDA, recalée sur le moment où la saturation relative passe sous 0,7 ; fin = saturation relative > 0,95 pendant 2 s (réapparition). Précision constatée : ±1 s sur les 5 morts du 17/08.
- Décalage observé sur la partie du 17/08 : horloge du jeu = temps vidéo + 37 s (dépend du moment où OBS a été lancé).

## Rush annoté découpé pour la revue (29/09)
- Le rush annoté est découpé (V1, A1, A2) à chaque début et fin de marqueur C/D : chaque proposition est un clip, relu avec X puis Alt+/.
- L'API n'a pas de lame : on retire les 3 clips entiers et on repose des morceaux contigus avec `media_pool append_to_timeline` (clip_infos positionnés, `media_type` 1 = vidéo seule, 2 = audio seul). `end_frame` est EXCLUSIF (end = début + durée).
- Les marqueurs de timeline ne bougent pas quand on supprime / repose les clips.
- Propositions qui se chevauchent (ex. C42 dans D29) : la plus longue est en plusieurs morceaux.
- Idée abandonnée : bandeaux transparents par proposition sur V2 (jugé trop lourd par Tristan).
- `timeline duplicate` bascule la timeline courante sur la copie : revenir avec `set_current` avant de continuer.

## Montage v1 (29/09)
- **Niveaux** : ne pas normaliser dans Resolve une piste découpée en morceaux (chaque morceau serait normalisé séparément et les passages calmes remontés). On mesure le fichier entier (`ffmpeg -af ebur128`), on fabrique `micro_mix.wav` / `jeu_mix.wav` avec `volume=+XdB,alimiter=limit=0.89:level=false` (micro -16, jeu -27 LUFS depuis la revue v3 — -24 était un peu fort), puis `media_pool_item replace_clip` : les éléments de timeline gardent leurs points d'entrée / sortie.
- Musique d'ambiance : un seul fichier fabriqué avec ffmpeg (pistes « Route » Pokémon enchaînées, gain conseillé du catalogue, fondus 3/4 s) à -36 LUFS, posé sur A3 en deux morceaux (trou pendant « Got Ganked »). Jingles pré-baissés à -30 LUFS sur A4.
- **Intro + montage** : intro dans sa propre timeline, puis une timeline « 02 Vidéo finale » qui imbrique [Intro][01 Montage v1] (append_to_timeline d'éléments de pool de type Timeline, `track_index` obligatoire). Évite de décaler tout le montage.
- **Runes** : `timeline import_timeline_checked` du `.drt` avec `require_temp_path: false`, puis la timeline « Template Runes » imbriquée sur V2 à 5 s. Tristan remplace les images dans 04 Runes.
- **S'abonner** : la vidéo source (League Of Legends/S'abonner animation) est une démo ; la séquence sur fond vert propre est à 10.0-19.8 s. Détourage ffmpeg (`chromakey=0x00FF00:0.28:0.06`), recadrage 1420×400 à (250,560), mise à l'échelle 50 %, posée en haut à gauche (30,130) → `habillage/abonner.mov` (qtrle transparent).
- **Zoom KDA** : incrustation ffmpeg du KDA du HUD (crop 100×34 à (1652,0), ×4, cadre jaune) sous le score en haut à droite, 3 s → `zoom_kda.mov`.
- `05_plan_montage.py` : coupes libres (`coupes_libres`), plages protégées (`garder_plages`), recalage des coupes hors des phrases, miettes < 0,5 s supprimées.
- Fondus audio 5 images : pas faits sur les 126 morceaux (un appel par morceau) ; les coupes tombent dans des silences. À surveiller au rendu.

## Montage v2 (29/09) — timeline plate et règles de la revue
- `06_retours_base.py` : décode seulement les images clés (≈ 1 toutes les 4,2 s chez OBS, ~30 s pour 45 min) et suit le rectangle blanc de la caméra sur la minimap (crop 300×300 à (1620,780)). Arrivée brutale dans le coin de la fontaine = rappel (ou réapparition si une mort précède) ; le back va de arrivée − 9 s jusqu'à la sortie de base (> 105 px de la fontaine). Attention : `-v info` obligatoire pour que `showinfo` donne les temps.
- `07_plan_v2.py` : part de plan_v1 ; rend les morts visibles (8 s avant, 2,5 s après, en comblant un trou < 6 s), voix retirée seulement dans les zones de colère ; backs : silence ≥ 5 s coupé, reste accéléré si gain ≥ 3 s (vitesse = durée / (parole + 0,3 s par phrase + 0,4), max ×2, pas de 5 %), phrases posées à vitesse normale. Jamais une phrase coupée au bord d'un retour (bornes recalées sur les mots).
- `08_construction_v2.py` : intro (`propositions/intro_v2.json`) + partie + habillage (`habillage_v2.json`, positions en secondes source) → `construction_v2.json` (frames). Placement par `append_to_timeline` (clip_infos par piste), puis `set_speed` sur la vidéo ET le son du jeu (l'élément garde sa durée et consomme durée × vitesse images source), puis `set_fades` élément par élément (≈ 200 appels, ~25 ms chacun).
- `set_fades` marche aussi sur la vidéo : fondu au noir en fin d'intro (FadeOut 120) et fondu depuis le noir au début de la partie (FadeIn 72).
- **Ombre portée des runes** : un comp Fusion ajouté par l'API (outil `Shadow`) n'est pas rendu sur Studio 21.1 (comme documenté par le MCP). Contournement : copie de « Template Runes » sur V2 passée en noir par CDL (Slope 0, Saturation 0), opacité 60 %, décalée de (+12, −14) ; le vrai bloc sur V3. Position du bloc : Pan 20, Tilt −180 (milieu gauche).
- Musique v2 : `musique_ambiance_v2.wav` = v1 +3 dB (-33 LUFS). Effets : `sfx_kill.wav` (Impact Hit 1, -30), `whoosh_transition.wav` (Deep Whoosh 1, -32), titre `dans_cette_video.mov` (ffmpeg, Poppins Bold 56, barre jaune, fondus alpha).

## Montage v3 (29/09) — retours de la revue v2
- `08_construction_v2.py --version v3` : lit `intro_v3.json`, `habillage_v3.json` et `habillage/killfeed.json`. Intro : `prolonger_s` sur le dernier extrait = image et son du jeu prolongés sans la voix (le son fond sur la rallonge, puis fondu au noir). Titre fabriqué à la durée exacte (`jusqua: fin_voix`). Éléments d'habillage : `transform` (Pan/Tilt), `decalage_s`, `optionnel` (abandonné si sa seconde est coupée). Chevauchements V2/A4 signalés.
- **Fondus micro adaptatifs** (`fondus_voix`) : jamais plus long que le silence entre la coupe et le mot le plus proche.
- **Calage des coupes du micro sur l'énergie** : les fins de mots de Whisper sont souvent en avance de 0,1 s. Exemple : « partie » donné fini à 2692,30 alors que la syllabe « -tie » dure jusqu'à 2692,37 → la coupe à 2692,28 mangeait la fin du mot. Le script cherche maintenant, après chaque fin de morceau qui tombe dans la parole, le premier creux (fenêtre 20 ms < -36 dB, dans 0,45 s et sans empiéter sur le morceau voisin) ; idem avant un début (0,3 s). Pas de calage quand la parole continue dans un autre morceau (source contiguë). Ce qui reste en pleine parole → marqueur violet « À écouter » (`propositions/spec_v3_ecoute.json`).
- **Pas de réglage du début/de la fin d'un élément par l'API** : pour corriger un morceau de micro, `timeline delete_clips` (ripple false) puis `append_to_timeline` avec les nouvelles bornes, puis `set_fades`. Attention aux index : vérifier les ids avec `clip_where` avant de supprimer (une erreur d'un rang a supprimé le mauvais morceau, remis aussitôt). `delete_clips` archive la timeline (copie « archived_version ») la première fois.
- **Runes pré-rendues** : « Template Runes » rendu en QuickTime ProRes 4444 avec `ExportAlpha: true` (`habillage/runes_brut.mov`), puis ombre ajoutée par ffmpeg (alpha × 0,8, flou 3, décalage 4 px) → `runes_ombre.mov`. Lag de la v2 expliqué : timeline imbriquée de 9 pistes avec animations, recalculée image par image, en double (bloc + copie noire pour l'ombre). Un clip pré-rendu se lit sans calcul.
- Son des runes : `rune_sfx.wav` (Fleet_Footwork_SFX_2.ogg, -30 LUFS), calé 0,24 s avant l'apparition.
- S'abonner v3 : source 10–19,8 s, chromakey, crop 1420×400+250+560, réduit à 710×200, `setpts=PTS/1.4`, posé à (605,780) (au-dessus des sorts), 7 s.
- `zooms_hud.py` : kill feed = crop (1700,225) 220×120, zoom ×2, posé à (1210,200), cadre jaune ; 1,5 s ; kills d'équipe sans Tristan (± 10 s), avant 588 s vidéo (10 min de jeu − 12 s d'horloge), 30 s d'écart ; t0 = fin de la fenêtre de lecture HUD + 0,5 s (sinon l'entrée n'est pas encore affichée). `--kda <s>` pour le zoom KDA.
- **Piège ffmpeg (alpha)** : `overlay` sur un fond `color=black@0` avec `format=auto` (ou `rgb`) sort une image **sans alpha** → les zooms étaient des rectangles noirs plein écran dans Resolve. Utiliser `pad=1920:1080:x:y:color=black@0` sur une image rgba, puis `format=argb` (qtrle). Vérifier l'alpha : `alphaextract` et compter les pixels non nuls. Après régénération d'un fichier déjà dans le pool : `media_pool_item replace_clip` (même chemin) pour que Resolve le relise.
- Marqueurs par spec : `project_manager apply_spec` avec `{"project", "timelines":[{"name","markers":[{frame,color,name,note,duration}]}]}` — frames relatives au début de la timeline, deux marqueurs ne peuvent pas partager une image.

## Finitions v4 (29/09) — revue du v3
- **Gigotement des runes** : expressions Fusion de l'outil `Gigote` (Transform) de chaque piste de « Template Runes ». Pour les lire : `timeline_item_fusion export_comp` (fichier .comp texte). Pour les changer : `fusion_comp bulk_set_expressions` (timeline « Template Runes » courante). Amplitudes actuelles : position 0,003335 + 0,002 (unités d'image), angle 0,5°. Mesuré sur le rendu : déplacement crête à crête 1,4 → 0,66 px.
- `scripts/runes_habillage.py <runes_brut.mov> <sortie.mov>` : ombre contour (alpha × 0,8, flou boîte 3 px, décalage 4 px) + fondus d'opacité (0,35 s / 0,45 s), en numpy par tuyaux ffmpeg, sortie ProRes 4444 avec alpha (~40 s pour 5 s de runes). Remplace la recette ffmpeg ad hoc de la v3.
- Zooms v4 : ×1,5 (au lieu de ×2), collés au bord droit **par-dessus** le kill feed d'origine (1574,212) ; KDA ×3 en (1604,40) ; cadre discret (2 px noir 55 % + 1 px blanc 28 %). Réglages dans `config/reglages.yaml` (`zooms:`).
- Son du jeu baissé de 3 dB : `audio/jeu_mix_v4.wav` (`volume=-3dB`) puis `replace_clip` sur jeu_mix : les 78 éléments gardent coupes, vitesses et fondus.
- `replace_clip` touche le média du pool, donc **toutes** les timelines qui l'utilisent (la v3 affiche aussi les runes, zooms et le son v4).
