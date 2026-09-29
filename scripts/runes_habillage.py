"""Runes pré-rendues : ombre « contour » + fondus d'entrée / sortie, à partir du rendu alpha de « Template Runes ».

Resolve rend « Template Runes » en QuickTime ProRes 4444 avec alpha (habillage/runes_brut*.mov).
Ce script ajoute, image par image :
  - une ombre très proche (alpha × OPACITE, flou RAYON px, décalée de DECALAGE px vers le bas-droite),
  - un fondu d'entrée et de sortie sur l'opacité de tout le bloc.
Un clip pré-rendu se lit sans calcul dans Resolve (le template imbriqué faisait ramer la lecture).
Usage : python scripts/runes_habillage.py <runes_brut.mov> <sortie.mov> [--entree 0.35] [--sortie 0.45]
"""
import subprocess
import sys

import numpy as np

src, dst = sys.argv[1], sys.argv[2]
arg = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
FONDU_IN, FONDU_OUT = arg("--entree", 0.35), arg("--sortie", 0.45)
OPACITE, RAYON, DECALAGE = 0.8, 3, 4
L, H, FPS = 1920, 1080, 60

n = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
lire = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                        stdout=subprocess.PIPE)
ecrire = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{L}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                           "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", dst], stdin=subprocess.PIPE)


def flou(a, r):
    """Flou boîte séparable (rayon r) par sommes cumulées."""
    for axe in (0, 1):
        c = np.cumsum(np.pad(a, [(r + 1, r) if i == axe else (0, 0) for i in range(2)], mode="edge"), axis=axe)
        a = (np.take(c, range(2 * r + 1, c.shape[axe]), axis=axe) - np.take(c, range(0, c.shape[axe] - 2 * r - 1), axis=axe)) / (2 * r + 1)
    return a


for i in range(n):
    im = np.frombuffer(lire.stdout.read(L * H * 4), np.uint8).reshape(H, L, 4).astype(np.float32) / 255
    a = im[..., 3]
    ombre = np.zeros_like(a)
    ombre[DECALAGE:, DECALAGE:] = flou(a, RAYON)[:-DECALAGE, :-DECALAGE] * OPACITE
    a_out = a + ombre * (1 - a)                                   # bloc par-dessus son ombre noire
    rgb = np.where(a_out[..., None] > 0, im[..., :3] * a[..., None] / np.maximum(a_out[..., None], 1e-6), 0)
    t = i / FPS
    k = min(1.0, t / FONDU_IN, (n / FPS - t) / FONDU_OUT) if FONDU_IN and FONDU_OUT else 1.0
    out = np.dstack([rgb, a_out * max(0.0, k)])
    ecrire.stdin.write((out * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
ecrire.stdin.close()
ecrire.wait()
print(f"{n} images -> {dst} (fondus {FONDU_IN} s / {FONDU_OUT} s)")
