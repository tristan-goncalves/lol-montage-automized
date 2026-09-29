-- Revue : change la couleur du marqueur sous la tête de lecture,
-- puis saute au marqueur suivant et pose l'entrée / la sortie autour de lui.
-- Il ne reste plus qu'à lancer « Lire de l'entrée à la sortie ».
-- COULEUR est remplacée à l'installation (Red / Green / Cyan / Yellow).
local COULEUR = "__COULEUR__"

local resolve = resolve or Resolve()
local projet = resolve:GetProjectManager():GetCurrentProject()
local tl = projet and projet:GetCurrentTimeline()
if not tl then print("Pas de timeline ouverte") return end

local fps = tonumber(tl:GetSetting("timelineFrameRate")) or 60
fps = math.floor(fps + 0.5)
local debut_tl = tl:GetStartFrame()

local function vers_images(tc)
  local h, m, s, f = tc:match("(%d+)[:;](%d+)[:;](%d+)[:;](%d+)")
  return ((tonumber(h) * 3600 + tonumber(m) * 60 + tonumber(s)) * fps + tonumber(f)) - debut_tl
end

local function vers_tc(images)
  local t = images + debut_tl
  local f = t % fps
  local s = math.floor(t / fps)
  return string.format("%02d:%02d:%02d:%02d", math.floor(s / 3600), math.floor(s / 60) % 60, s % 60, f)
end

-- Marqueurs revus : coupes (C, D), moments forts (M), idées (I).
-- Les marqueurs de plus de 2 min (intros qui couvrent toute la partie) sont exclus de l'enchaînement :
-- ils se décident en lisant la note.
local DUREE_MAX = 120 * fps
local function est_revu(m)
  return m ~= nil and m.name ~= nil and m.name:match("^[CDMI]%d+") ~= nil and m.duration <= DUREE_MAX
end

local p = vers_images(tl:GetCurrentTimecode())
local marqueurs = tl:GetMarkers() or {}

-- 1) Si une entrée est posée pile au début d'un marqueur qui contient la tête de lecture
--    (cas normal : X ou ce script l'a posée), c'est lui.
-- 2) Sinon, le marqueur qui contient la tête de lecture et commence le plus tard.
local choisi = nil
local ok_io, mio = pcall(function() return tl:GetMarkInOut() end)
local entree = ok_io and type(mio) == "table" and mio.video and mio.video["in"] or nil
if entree and marqueurs[entree] and est_revu(marqueurs[entree])
   and entree <= p and p <= entree + marqueurs[entree].duration then
  choisi = entree
end
for f, m in pairs(choisi == nil and marqueurs or {}) do
  if est_revu(m) and f <= p and p <= f + m.duration then
    if choisi == nil or f > choisi then choisi = f end
  end
end
if choisi == nil then
  print("Aucun marqueur sous la tête de lecture à " .. vers_tc(p))
  return
end

local m = marqueurs[choisi]
if m.color ~= COULEUR then
  tl:DeleteMarkerAtFrame(choisi)
  local ok = tl:AddMarker(choisi, COULEUR, m.name, m.note or "", m.duration, m.customData or "")
  if not ok then
    tl:AddMarker(choisi, m.color, m.name, m.note or "", m.duration, m.customData or "")
    print("Échec du changement de couleur pour " .. m.name)
    return
  end
end
print(m.name .. " -> " .. COULEUR)

-- Marqueur suivant
local suivant = nil
for f, mm in pairs(marqueurs) do
  if est_revu(mm) and f > choisi and (suivant == nil or f < suivant) then suivant = f end
end
if suivant == nil then
  print("C'était la dernière proposition.")
  return
end
local ms = marqueurs[suivant]
tl:SetCurrentTimecode(vers_tc(suivant))
pcall(function() tl:SetMarkInOut(suivant, suivant + ms.duration - 1) end)
print("Suivant : " .. ms.name)
