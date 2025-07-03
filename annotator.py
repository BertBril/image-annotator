import os, sys
from PIL import Image, ImageDraw, ImageFont

def resolve_path(path):
  if path.upper().startswith("APP:"):
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, path[4:])
  return path

def annotate_image(config, default_units):
  inp = resolve_path(config["inputdir"])
  fonts = {}
  results = {}
  for obj in config["objects"]:
    imgpath = os.path.join(inp, obj["img"])
    im = Image.open(imgpath).convert("RGBA")
    draw = ImageDraw.Draw(im)
    fam = resolve_path(config.get("fontfamily", "APP:app.ttf"))
    for a in obj["annots"]:
      x, y = a["pix"]
      fs = int(a.get("fontsize", 12))
      key = (fam, fs)
      if key not in fonts:
        try:
          fonts[key] = ImageFont.truetype(fam, fs)
        except:
          fonts[key] = ImageFont.load_default()
      font = fonts[key]
      val = a.get("value", a.get("default", ""))
      units = a.get("units") or default_units
      text = val + (units if units else "")
      bbox = draw.textbbox((0, 0), text, font=font)
      w = bbox[2] - bbox[0]
      h = bbox[3] - bbox[1]
      bg = a.get("bgcolor", "#ffffff")
      fg = a.get("fgcolor", "#000000")
      place = a.get("placeat", "right").lower()
      if place == "top":
        pos = (x - w // 2, y - h)
      elif place == "bottom":
        pos = (x - w // 2, y)
      elif place == "left":
        pos = (x - w, y - h // 2)
      else:
        pos = (x, y - h // 2)
      draw.rectangle([pos, (pos[0] + w, pos[1] + h)], fill=bg)
      draw.text(pos, text, fill=fg, font=font)
    key = obj.get("name", obj["img"]).strip()
    results[key] = (im, obj["outputdir"])
  return results

