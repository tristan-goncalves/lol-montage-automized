; Revue des marqueurs dans DaVinci Resolve : une seule touche = « Marquer » puis « Lire de l'entrée à la sortie ».
; Nécessite AutoHotkey v2 (gratuit) : https://www.autohotkey.com — double-cliquer sur ce fichier pour l'activer.
; Ne fonctionne que quand Resolve est au premier plan.
;
; RÉGLAGES — à adapter aux raccourcis que tu as mis dans Resolve (Keyboard Customization) :
;   TOUCHE_REVUE    : la touche sur laquelle tu appuies (ici Maj + Espace, noté +Space)
;   RACC_MARQUER    : le raccourci Resolve de X ou, mieux, du script « Revue 0 Marquer » (ici F9)
;   RACC_LECTURE    : le raccourci Resolve de « Play In to Out »          (ici F10)
; Notation AutoHotkey : "{F9}", "0", "^m" (Ctrl+M), "+m" (Maj+M), "!m" (Alt+M).
RACC_MARQUER := "{F9}"
RACC_LECTURE := "{F10}"
DELAI_MS := 800   ; temps laissé au script Resolve avant de lancer la lecture

; Lancer ce fichier ouvre aussi Resolve s'il n'est pas déjà ouvert : utilise-le à la place de l'icône Resolve.
CHEMIN_RESOLVE := "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
if !ProcessExist("Resolve.exe") && FileExist(CHEMIN_RESOLVE)
    Run CHEMIN_RESOLVE

#HotIf WinActive("ahk_exe Resolve.exe")
+Space:: {
    Send RACC_MARQUER
    Sleep DELAI_MS
    Send RACC_LECTURE
}
#HotIf
