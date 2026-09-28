"""Outils partagés par tous les scripts : réglages, dossiers de travail, ffmpeg, timecodes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

DEPOT = Path(__file__).resolve().parent.parent
REGLAGES = DEPOT / "config" / "reglages.yaml"


def reglages() -> dict:
    with open(REGLAGES, encoding="utf-8") as f:
        return yaml.safe_load(f)


def racine_locale(cfg: dict) -> Path:
    """Dossier Records vu par le script (Windows natif ou Linux de Cowork)."""
    r = cfg["chemins"].get("racine_locale")
    if r:
        return Path(r)
    for cand in (Path.home() / "mnt" / "Records", Path(cfg["chemins"]["racine_windows"])):
        if cand.exists():
            return cand
    sys.exit("Dossier Records introuvable : renseigne chemins.racine_locale dans config/reglages.yaml")


def vers_windows(cfg: dict, chemin: Path) -> str:
    """Traduit un chemin local en chemin Windows (celui que Resolve comprend)."""
    rel = Path(chemin).resolve().relative_to(racine_locale(cfg).resolve())
    return cfg["chemins"]["racine_windows"].rstrip("\\") + "\\" + str(rel).replace("/", "\\")


class Travail:
    """Dossier de travail d'une vidéo : <Records>/_montage/<nom>/ et ses sous-dossiers."""

    def __init__(self, video: str | Path, cfg: dict | None = None):
        self.cfg = cfg or reglages()
        self.video = Path(video).resolve()
        if not self.video.exists():
            sys.exit(f"Vidéo introuvable : {self.video}")
        self.nom = self.video.stem
        self.dossier = racine_locale(self.cfg) / self.cfg["chemins"]["travail"] / self.nom
        for sous in ("audio", "analyse", "propositions", "habillage", "exports"):
            (self.dossier / sous).mkdir(parents=True, exist_ok=True)

    def __truediv__(self, rel: str) -> Path:
        return self.dossier / rel

    def lire(self, rel: str):
        with open(self / rel, encoding="utf-8") as f:
            return json.load(f)

    def ecrire(self, rel: str, data) -> Path:
        p = self / rel
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return p

    def infos(self) -> dict:
        p = self / "video.json"
        return self.lire("video.json") if p.exists() else sonder(self.video)


def sonder(video: Path) -> dict:
    """Durée, fps, nombre de pistes audio d'une vidéo (ffprobe)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=index,codec_type,avg_frame_rate,width,height",
         "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in v["avg_frame_rate"].split("/"))
    return {
        "fichier": str(video),
        "duree_s": float(d["format"]["duration"]),
        "fps": round(num / den, 3),
        "largeur": v["width"], "hauteur": v["height"],
        "pistes_audio": sum(1 for s in d["streams"] if s["codec_type"] == "audio"),
    }


def ffmpeg(*args: str, capture: bool = False):
    # En mode capture on garde les messages (les filtres d'analyse y écrivent leurs mesures)
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", *([] if capture else ["-loglevel", "error"]), *args]
    return subprocess.run(cmd, capture_output=capture, text=capture, check=not capture)


def tc(s: float) -> str:
    """Secondes -> m:ss (ou h:mm:ss)."""
    s = max(0, int(round(s)))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def images(s: float, fps: float) -> int:
    return int(round(s * fps))


def argument_video() -> Path:
    if len(sys.argv) < 2:
        sys.exit(f"Usage : python {Path(sys.argv[0]).name} <chemin de la vidéo .mp4>")
    return Path(sys.argv[1])
