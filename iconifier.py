import numpy as np
from PIL import Image, ImageFilter, ImageOps

# grayscale mapping (preserved for future use)
def map_to_gray(val, revert=False, skew=2.5):
  if revert:
    val = 1.0 - val
  val = val ** skew  # skew > 1 darkens the result
  v = int(round((1.0 - val) * 255))
  return (v, v, v)

# Approximate Viridis colormap with 20 RGB values (from light to dark)
# unfortunately, delivers ugliness
VIRIDIS_COLORS = [
  (253, 231, 37), (244, 228, 52), (235, 225, 65), (217, 217, 81),
  (199, 209, 95), (181, 201, 108), (154, 190, 122), (127, 179, 133),
  (102, 166, 142), (78, 154, 149), (61, 143, 153), (45, 132, 155),
  (36, 121, 154), (31, 110, 151), (31, 99, 146), (35, 88, 139),
  (41, 74, 129), (46, 61, 115), (51, 47, 99), (53, 35, 82)
]

def map_to_viridis(val, revert=False):
  if revert:
    val = 1.0 - val
  idx = min(int(val * (len(VIRIDIS_COLORS) - 1)), len(VIRIDIS_COLORS) - 1)
  return VIRIDIS_COLORS[idx]

def create_icon_from_pil(pil_image, size=(32, 32), cutoff_percentile=50, use_gray=True, revert=False):
  img = pil_image.convert("L")  # Grayscale
  img = ImageOps.autocontrast(img)

  # 1. Edge detection using Laplacian-like kernel
  edge_kernel = ImageFilter.Kernel(
    size=(3, 3),
    kernel=[0, -1, 0,
           -1,  4, -1,
            0, -1, 0],
    scale=1
  )
  edge = img.filter(edge_kernel)

  # 2. Spread: 5x5 max filter to thicken edges
  edge_spread = edge.filter(ImageFilter.MaxFilter(11))

  # 3. Binarize
  edge_np = np.array(edge_spread)
  threshold = np.percentile(edge_np, 60)
  binary = (edge_np > threshold).astype(np.uint8)

  # 4. Compute blackness: 5x5 window of black pixel count using summed convolution
  kernel = np.ones((5, 5), dtype=np.uint8)
  padded = np.pad(binary, 2, mode="edge")
  blackness = np.zeros_like(binary, dtype=np.uint8)
  for y in range(binary.shape[0]):
    for x in range(binary.shape[1]):
      blackness[y, x] = np.sum(padded[y:y+5, x:x+5])

  # 5. Cut off lowest X% and normalize
  cutoff = np.percentile(blackness, cutoff_percentile)
  blackness = blackness.astype(np.float32)
  blackness[blackness < cutoff] = 0
  blackness[blackness >= cutoff] -= cutoff
  blackness = blackness / (blackness.max() or 1)

  # 6. Map to color
  h, w = blackness.shape
  rgb_array = np.zeros((h, w, 3), dtype=np.uint8)
  for y in range(h):
    for x in range(w):
      if use_gray:
        rgb_array[y, x] = map_to_gray(blackness[y, x], revert=revert)
      else:
        rgb_array[y, x] = map_to_viridis(blackness[y, x], revert=revert)

  # 7. Convert to image and stepwise downscale
  rgb_img = Image.fromarray(rgb_array, mode="RGB")
  for target in [128, 64, 32]:
    if rgb_img.size[0] > target:
      rgb_img = rgb_img.resize((target, target), Image.BILINEAR)

  return rgb_img.resize(size, Image.LANCZOS)

