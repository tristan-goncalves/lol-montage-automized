# Guide de montage — le style de Tristan

Les règles éditoriales, apprises vidéo après vidéo. Claude le relit **avant chaque montage** et le
met à jour **après chaque retour**. Le détail technique est dans [technique.md](technique.md),
l'historique complet dans [journal/](journal/).

## Principes
- Garder la majorité de la partie et retirer seulement ce qui est vraiment inutile (repère : 30 min → environ 20 min).
- Tristan est le directeur du montage : Claude propose, Tristan valide. Rien n'est appliqué sans validation.
- Dans le doute sur l'intérêt d'un passage : demander plutôt que couper (un cas « à discuter » non tranché est gardé).

## Intro
- 15 à 25 s en tout début de vidéo, pour accrocher.
- Toujours proposer 3 styles : **storytelling** (tout va bien → tournant → frustration), **spectaculaire** (les meilleures actions), **humour** (les meilleures phrases).
- Le storytelling a été jugé bien (17/08) — à confirmer sur d'autres vidéos.
- Boîte à outils validée : ralenti (optical flow), zoom punch, fondus enchaînés entre plans calmes, coupes franches sur les impacts, whoosh / impact, musique en fond, titres animés.
- Titres : style à simplifier (retour du 28/09 : « j'adore l'idée, mais un peu plus basique »).
- **Cuts de voix doux** : chaque extrait finit sur une phrase entière, coupé dans le silence qui suit (jamais au ras du dernier mot) ; fondus audio sur chaque extrait (29/09).
- **Effets sonores sur les kills** (impact calé sur le bandeau « Ennemi tué »), pas de jingle en plein combat (29/09).
- **Plus de jingle Victory dans l'intro** (trop compliqué à caler automatiquement) (29/09, revue v2).
- **« Dans cette vidéo… »** en haut à gauche, affiché **pendant toute l'intro** (jusqu'à la fin de la dernière phrase) (29/09, revue v2).
- **Fin d'intro** : la dernière phrase est entendue **en entier** ; le fondu du son ne commence qu'**après** elle (le plan est prolongé de ~2,5 s sans la voix), puis le fondu au noir de l'image, un temps de noir, whoosh (validé), et la partie arrive en fondu depuis le noir. Jamais de cut sec entre l'intro et la partie (29/09, revue v2).

## Coupes
- **Moments forts refusés** (rouge) : ils sont coupés — s'ils ne sont pas gardés, c'est que l'écran n'avait rien d'intéressant (29/09).
- **Morts sans commentaire** : coupées presque toujours (20/22 sur la partie du 29/09).
- **Accéléré ×2** : ne plus le proposer par défaut (1 accepté sur 4) — couper ou garder (29/09).
- **Retours à la base (backs, réapparitions)** : toujours proposés. Sans commentaire → coupés ; s'il parle → accélérés (**jusqu'à ×3**, ne pas hésiter) avec **sa voix à vitesse normale** (phrases posées à la suite dans le passage accéléré). Repérés sur la minimap (`06_retours_base.py`) (29/09, revue v2).
- **Ne jamais couper un de ses kills** (ni une mort) : même si le marqueur qui le contient est rouge, le kill reste visible (~6 s avant, 2 s après) ; seule la voix en colère peut partir (29/09, revue v2 : kill de 28:58 perdu à cause d'un marqueur rouge « Kill n°2 »).
- **Ne jamais masquer une mort** : on voit toujours le combat qui y mène et l'écran gris (~8 s avant, 2,5 s après). Si la voix est à couper (colère), on ne retire que la voix et on garde le jeu (29/09).
- **Analyses de build / stratégie** : les garder ; couper plutôt les calculs et détails trop longs (29/09).
- **Coupes jamais au milieu d'une phrase** (29/09). **Aucune phrase dans un fondu** : chaque fin de morceau de voix est calée sur le vrai silence qui suit le dernier mot (énergie du micro, pas seulement Whisper), et le fondu est raccourci s'il toucherait un mot. Les coupes en pleine parole qui restent sont signalées par un marqueur violet « À écouter » (29/09, revue v2).
- **Coups de colère** (surtout pendant une mort) : on les coupe. Garder au plus une ou deux phrases ; dès que ça part trop loin sous l'émotion, proposer une coupe (29/09).
- Couper les silences en phase calme (farm, déplacements) et les morts sans commentaire.
- Ne jamais couper automatiquement près d'un kill, d'une mort ou d'un combat (± 4 s).
- Proposer d'accélérer (×2) plutôt que couper quand l'action à l'écran aide à comprendre.
- **Jamais de coupe sèche sur la voix** : couper un peu après la fin d'une phrase (0,9 s) ou un peu avant la suivante (0,6 s).
- **Fondu audio à chaque coupe, sans exception** : jeu 8 images, micro 4 images, 15 images au début et à la fin d'une accélération (sinon le son « casse ») (29/09).

## Habillage
- **Montage sobre mais pas plat** : pas de mise en valeur systématique des moments forts ; quelques petits effets / jingles ponctuels pour donner du peps (zoom KDA, Got Ganked, Level Up, Victory), sans en faire trop (29/09).
- **Musique d'ambiance** sous toute la partie : **-33 LUFS, à viser à chaque partie** (« son nickel ») (29/09, revue v2).
- **Runes** : template toujours placé ~5 s après le début de la partie, **au milieu gauche** de l'écran (centré verticalement, validé), avec une **ombre très proche, à peine plus qu'un contour** (4 px, légèrement floutée), **gigotement très léger** (±0,3 px, ±0,5°), **fondu à l'apparition et à la disparition**, et le son **Fleet_Footwork_SFX_2.ogg** (Runes Artworks/Sound Effects) à l'apparition. Le bloc est **pré-rendu** en clip transparent (sinon Resolve rame à la lecture). Tristan change les images lui-même (29/09, revue v2 ; finalisé revue v3).
- **« S'abonner »** : au début, pendant que Tristan explique le matchup / la lane (moment validé), **en bas au centre, juste au-dessus des sorts**, animation **accélérée de 40 %** (29/09, revue v2 ; validé tel quel revue v3).
- **Zoom sur le kill feed** (colonne des kills à droite, entre le score et la minimap) : pendant la phase de lane (10 premières minutes de jeu), sur un creux, quand un kill a lieu sans Tristan ; **1,5 s** par zoom, au plus un toutes les 30 s. Même durée (1,5 s) pour le zoom KDA (29/09, revue v2). Zoom **petit (×1,5), collé au bord droit** par-dessus le kill feed, **cadre discret** (fin liseré sombre, pas de gros contour jaune) (29/09, revue v3).
- **Runes** au début de la partie : bloc « Template Runes » (une rune par piste, gigotement ÷2 depuis la revue v3). Tristan change les images lui-même (Replace Clip).
- **Musique** : ambiance JRPG / chill (Pokémon, médiéval, lofi). Libre de droits, ou libre tant que la vidéo n'est pas monétisée.
- **Jingles Pokémon** (Level Up, Objet obtenu, Victoire…) : bons candidats pour ponctuer un kill, un objet ou une victoire.
- **Pistes « Got ganked »** : à priori pour les moments où Tristan se fait ganker (à confirmer).
- **Textes à l'écran** : jamais sur le HUD (chat en bas à gauche, minimap en bas à droite, score en haut à droite). Le haut gauche est libre.
- Ressources : dossiers Sound Effects, Memes, Champions Artworks, Items / Map Artworks, animation « S'abonner ».

## Son
- Voix toujours devant. Niveaux : micro -16, **jeu -27** (-24 était un peu fort face à la voix et la musique, revue v3), effets -30, musique -33 LUFS.
- Un effet sonore ne passe **jamais** au-dessus de la voix (6 à 8 dB en dessous).
- Toujours appliquer le gain conseillé du catalogue, jamais un son brut.

## Organisation
- Un dossier de travail par vidéo (`_montage/<vidéo>/`), les 3 intros séparées, audio séparé jeu / micro, notes dans des marqueurs : structure validée, à conserver.
- Chaque étape crée une nouvelle timeline, on ne modifie jamais la précédente.
- **Montage livré en timeline plate** (intro + partie dans la même timeline, pas de timeline imbriquée sauf le template des runes), pistes nommées, marqueurs sur chaque choix automatique : Tristan relit et retouche directement dans Edit (29/09).

## Journal des règles
| Date | Vidéo | Retour de Tristan | Règle retenue |
|---|---|---|---|
| 28/09 | 17/08 | Intro storytelling jugée bien | Privilégier le storytelling (à confirmer) |
| 28/09 | 17/08 | Coupes trop abruptes | Marges autour de la voix + fondus audio courts |
| 28/09 | 17/08 | Dossiers, 3 intros, audio séparé, notes : validés | Structure par défaut |
| 28/09 | 17/08 | Effets sonores beaucoup trop forts, musique un peu forte | Effets sous la voix, musique ~20 dB sous la voix |
| 28/09 | 17/08 | Effets encore un peu forts à -24 LUFS | Effets à -30 LUFS |
| 28/09 | — | Template de runes Vegas à reproduire, Tristan change les images | Bloc runes Resolve en début de vidéo |
| 28/09 | — | Gigotement des runes trop fort | Divisé par 3 |
| 28/09 | — | Titres motion design : « un peu plus basique » | Simplifier le style des titres |
| 29/09 | 29/09 | Besoin d'un moyen très simple de valider les coupes | Décisions par couleur des marqueurs dans Resolve (rouge couper, vert garder, cyan accélérer) |
| 29/09 | 29/09 | Voir où finit chaque proposition sans comparer les timecodes (bandeaux superposés jugés trop lourds) | Rush annoté découpé au début et à la fin de chaque coupe C/D : X (Marquer le clip) puis Alt+/ (Lire de l'entrée à la sortie) |
| 29/09 | 29/09 | « Pas besoin de mettre en valeur les moments forts, je veux un montage très sobre, hormis l'intro » | Pas de musique / zoom / effet sur les moments forts ; l'habillage est réservé à l'intro (et aux runes) |
| 29/09 | 29/09 | « Le but sera de couper les moments où je commence à m'énerver (notamment quand je suis mort) » | Proposer une coupe D pour chaque énervement qui dépasse une ou deux phrases |
| 29/09 | 29/09 | Revue des couleurs : moments forts rouges coupés, petits effets gardés, musique d'ambiance, runes à 5 s, S'abonner au début | Règles ajoutées dans Coupes et Habillage |
| 29/09 | 29/09 | Revue du montage v1 : relire dans Edit, fondus audio partout, backs à couper ou accélérer voix normale, ne pas masquer les morts, intro plus douce (SFX kills, « Dans cette vidéo… », fondu au noir), runes plus bas avec ombre, musique un peu plus forte | Règles ajoutées dans Intro, Coupes, Habillage, Son, Organisation |
| 29/09 | 29/09 | Revue du montage v2 : plus de jingle Victory, titre sur toute l'intro, dernière phrase coupée par le fondu, ombre des runes trop loin + son Fleet Footwork, lag sur les runes, S'abonner en bas au centre ×1,4, musique -33 parfaite, backs accélérables davantage, phrases dans les fondus, zooms kill feed 1,5 s en lane, kill coupé à 28:58 | Règles ajoutées dans Intro, Coupes, Habillage |
| 29/09 | 29/09 | Revue du montage v3 : gigotement des runes encore ÷2 + fondus entrée/sortie (runes finalisées), S'abonner validé, zooms : cadre jaune trop voyant, plus près du bord droit, 25 % plus petits ; son du jeu un peu fort ; coupures de voix « bien meilleures » | Runes, zooms et niveau du jeu mis à jour ; prochaine étape : test complet sur une nouvelle partie |
