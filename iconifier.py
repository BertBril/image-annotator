from PIL import Image, ImageFilter, ImageOps

def map_to_gray(val, revert=False, skew=2.0):
  if revert:
    val = 1.0 - val
  val = min(max(val, 0.0), 1.0)
  val = val ** skew
  v = int(round((1.0 - val) * 255))
  return (v, v, v)

def create_icon_from_pil(pil_image, size=(32, 32), cutoff_percentile=50, use_gray=True, revert=False, skew=1.0):
  img = pil_image.convert("L")
  img = ImageOps.autocontrast(img)

  # Step 1: Edge detection
  edge_kernel = ImageFilter.Kernel(
    size=(3, 3),
    kernel=[0, -1, 0,
           -1,  4, -1,
            0, -1, 0],
    scale=1
  )
  edge = img.filter(edge_kernel)

  # Step 2: Max filter (5x5 spread)
  edge_spread = edge.filter(ImageFilter.MaxFilter(5))

  # Step 3: Threshold
  flat = list(edge_spread.getdata())
  sorted_vals = sorted(flat)
  idx = int(len(sorted_vals) * 0.8)
  threshold = sorted_vals[min(idx, len(sorted_vals) - 1)]

  # Step 4: Binarize
  w, h = edge_spread.size
  binary = [[1 if edge_spread.getpixel((x, y)) > threshold else 0 for x in range(w)] for y in range(h)]

  # Step 5: Local blackness in 5x5 neighborhood
  def local_blackness(y, x):
    count = 0
    for dy in range(-2, 3):
      for dx in range(-2, 3):
        ny = y + dy
        nx = x + dx
        if 0 <= ny < h and 0 <= nx < w:
          count += binary[ny][nx]
    return count / 25.0  # normalize to 0..1

  blackness = [[local_blackness(y, x) for x in range(w)] for y in range(h)]

  # Step 6: Apply cutoff percentile
  all_vals = [v for row in blackness for v in row]
  all_vals.sort()
  cutoff_index = int(len(all_vals) * cutoff_percentile / 100)
  cutoff = all_vals[min(cutoff_index, len(all_vals) - 1)]

  for y in range(h):
    for x in range(w):
      v = blackness[y][x]
      if v < cutoff:
        blackness[y][x] = 0.0
      else:
        blackness[y][x] = (v - cutoff) / (1.0 - cutoff) if (1.0 - cutoff) > 0 else 0.0

  # Step 7: Map to RGB
  out = Image.new("RGB", (w, h))
  for y in range(h):
    for x in range(w):
      val = blackness[y][x]
      color = map_to_gray(val, revert=revert, skew=skew)
      out.putpixel((x, y), color)

  # Step 8: Stepwise downscale
  for target in [128, 64, 32]:
    if out.size[0] > target:
      out = out.resize((target, target), Image.BILINEAR)

  return out.resize(size, Image.LANCZOS)

