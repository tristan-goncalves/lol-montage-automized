"""Fabrique les titres animés : image PNG transparente puis clip .mov ProRes 4444 (avec transparence).

Pourquoi des clips vidéo : les titres Text+ de Resolve ne se placent pas proprement par script
(ils atterrissent sous la tête de lecture), et les images fixes sont forcées à 5 s.

Entrée : habillage/titres.json, liste de titres :
  [{"id": "t1", "style": "badge", "texte": "4 / 0 / 1", "sous_texte": "10 MIN DE JEU", "images": 200},
   {"id": "t2", "style": "narratif", "texte": "…et puis.", "images": 120},
   {"id": "t3", "style": "impact", "texte": "ONE SHOT.", "images": 200},
   {"id": "t4", "style": "carte", "texte": "ELLE ÉTAIT SI BIEN LA GAME", "sous_texte": "SHYVANA JUNGLE · AUTOFILL", "images": 290}]
Styles : badge (haut gauche, glisse), narratif (bas centre, fondu), impact (gros, rouge, effet pop),
carte (titre de fin sur un artwork, dégradé sombre).

Usage : python scripts/titres.py "<vidéo.mp4>"
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from commun import DEPOT, Travail, argument_video, ffmpeg

W, H = 1920, 1080
OR, ROUGE, BLANC = (240, 200, 90, 255), (235, 50, 50, 255), (255, 255, 255, 255)
POLICES = [DEPOT / "templates" / "polices", Path("/usr/share/fonts/truetype/google-fonts"),
           Path.home() / "AppData/Local/Microsoft/Windows/Fonts", Path("C:/Windows/Fonts")]


def police(nom, taille):
    for d in POLICES:
        if (d / nom).exists():
            return ImageFont.truetype(str(d / nom), taille)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", taille)


def calque():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def texte(img, xy, txt, f, couleur, contour=6, halo=None, ombre=True, ancre="mm"):
    if halo:
        g = calque()
        ImageDraw.Draw(g).text(xy, txt, font=f, fill=halo, anchor=ancre, stroke_width=contour + 10, stroke_fill=halo)
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(22)))
    if ombre:
        s = calque()
        ImageDraw.Draw(s).text((xy[0] + 6, xy[1] + 8), txt, font=f, fill=(0, 0, 0, 170), anchor=ancre,
                               stroke_width=contour, stroke_fill=(0, 0, 0, 170))
        img.alpha_composite(s.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text(xy, txt, font=f, fill=couleur, anchor=ancre, stroke_width=contour, stroke_fill=(15, 15, 25, 255))


def dessiner(t):
    im = calque()
    if t["style"] == "badge":
        x, y, l, h = 90, 60, 520, 190
        p = calque()
        ImageDraw.Draw(p).rounded_rectangle((x, y, x + l, y + h), 26, fill=(10, 12, 25, 175))
        im.alpha_composite(p)
        ImageDraw.Draw(im).rectangle((x, y + 22, x + 10, y + h - 22), fill=OR)
        texte(im, (x + 45, y + 48), t.get("sous_texte", ""), police("Poppins-Medium.ttf", 34), (200, 205, 220, 255),
              contour=0, ombre=False, ancre="lm")
        texte(im, (x + 42, y + 125), t["texte"], police("Poppins-Bold.ttf", 96), OR, contour=4, ancre="lm")
    elif t["style"] == "narratif":
        texte(im, (W // 2, 900), t["texte"], police("Poppins-MediumItalic.ttf", 110), BLANC, contour=5)
    elif t["style"] == "impact":
        texte(im, (W // 2, H // 2 + 250), t["texte"], police("Poppins-Bold.ttf", 210), ROUGE, contour=8, halo=(255, 40, 40, 150))
    elif t["style"] == "carte":
        g = calque()
        d = ImageDraw.Draw(g)
        for yy in range(H // 2, H):
            d.line((0, yy, W, yy), fill=(5, 5, 15, int(210 * ((yy - H // 2) / (H // 2)) ** 1.3)))
        im.alpha_composite(g)
        texte(im, (W // 2, 820), t["texte"], police("Poppins-Bold.ttf", 118), BLANC, contour=6, halo=(240, 200, 90, 90))
        ImageDraw.Draw(im).line((W // 2 - 260, 905, W // 2 + 260, 905), fill=OR, width=4)
        texte(im, (W // 2, 960), t.get("sous_texte", ""), police("Poppins-Medium.ttf", 48), OR, contour=2)
    return im


def animer(png: Path, mov: Path, style: str, n: int, fps: int = 60):
    d = n / fps
    sortie = ["-frames:v", str(n), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(mov)]
    vide = ["-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H}:r={fps}:d={d + 0.1},format=rgba"]
    image = ["-loop", "1", "-framerate", str(fps), "-i", str(png)]
    fin = f"fade=t=out:st={d - 0.45:.2f}:d=0.4:alpha=1"
    if style == "badge":  # glisse depuis la gauche
        ffmpeg(*vide, *image, "-filter_complex",
               f"[1:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,{fin}[t];"
               f"[0:v][t]overlay=x='-400*pow(max(0,1-t/0.4),3)':y=0:shortest=1,format=yuva444p10le", *sortie)
    elif style == "impact":  # effet pop : 135 % -> 100 % en 0,25 s
        z = "(1+0.35*pow(max(0,1-t/0.25),2))"
        ffmpeg(*vide, *image, "-filter_complex",
               f"[1:v]format=rgba,scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame,{fin}[t];"
               f"[0:v][t]overlay=x='(W-w)/2':y='(H-h)/2':shortest=1,format=yuva444p10le", *sortie)
    else:  # fondu simple (plus lent pour la carte)
        entree = "fade=t=in:st=0.2:d=0.8:alpha=1" if style == "carte" else "fade=t=in:st=0:d=0.35:alpha=1"
        ffmpeg(*image, "-vf", f"format=rgba,{entree},{fin},format=yuva444p10le", *sortie)


if __name__ == "__main__":
    tr = Travail(argument_video())
    dossier = tr / "habillage/titres"
    dossier.mkdir(exist_ok=True)
    for t in tr.lire("habillage/titres.json"):
        png, mov = dossier / f"{t['id']}.png", dossier / f"{t['id']}.mov"
        dessiner(t).save(png)
        animer(png, mov, t["style"], t.get("images", 180), int(tr.infos()["fps"]))
        print(f"{t['id']} ({t['style']}) -> {mov.name}")
