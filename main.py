import sys, os, json
from PyQt6.QtWidgets import (
  QApplication, QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
  QPushButton, QLineEdit, QMessageBox, QScrollArea, QFormLayout, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt, QSize
from annotator import annotate_image, resolve_path

class MainWindow(QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("Image Annotator")

    with open(resolve_path("config.json"), "r") as f:
      self.cfg = json.load(f)

    self.default_font = self.cfg.get("fontfamily", "arial")
    self.default_units = ""
    self.obj_map = {}
    self.value_fields = []
    self.font16 = QFont(self.default_font, 16)

    self.max_fields = self.estimate_max_fields()
    self.top_reserved_height = self.max_fields * 40 + 40

    # --- UI Setup ---
    self.combo = QComboBox()
    self.combo.setFont(self.font16)

    top_label = QLabel("Image")
    top_label.setFont(self.font16)

    self.image_label = QLabel()
    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    self.form_layout = QFormLayout()
    self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    self.form_frame = QFrame()
    self.form_frame.setLayout(self.form_layout)
    self.form_frame.setMinimumHeight(self.top_reserved_height)

    self.scroll = QScrollArea()
    self.scroll.setWidgetResizable(True)
    self.scroll.setWidget(self.form_frame)

    self.apply_button = QPushButton("Apply")
    self.save_button = QPushButton("Save")
    self.apply_button.setFont(self.font16)
    self.save_button.setFont(self.font16)

    # Layouts
    top_layout = QHBoxLayout()
    top_layout.addWidget(top_label)
    top_layout.addWidget(self.combo)

    button_layout = QHBoxLayout()
    button_layout.addWidget(self.apply_button)
    button_layout.addWidget(self.save_button)

    layout = QVBoxLayout()
    layout.addLayout(top_layout)
    layout.addWidget(self.scroll)
    layout.addLayout(button_layout)
    layout.addWidget(self.image_label)
    self.setLayout(layout)

    # Load object map
    for obj in self.cfg["objects"]:
      name = obj.get("name", obj["img"])
      self.combo.addItem(name)
      self.obj_map[name] = obj

    # Hook up signals AFTER init
    self.combo.currentIndexChanged.connect(self.load_object)
    self.apply_button.clicked.connect(self.apply_annotations)
    self.save_button.clicked.connect(self.save_image)

    defobj = self.cfg.get("defobj")
    idx = self.combo.findText(defobj) if defobj else 0
    self.combo.setCurrentIndex(idx)
    self.load_object(idx)

  def estimate_max_fields(self):
    return max(len(obj.get("annots", [])) for obj in self.cfg["objects"])

  def form_clear(self):
    while self.form_layout.count():
      item = self.form_layout.takeAt(0)
      w = item.widget()
      if w:
        w.deleteLater()

  def load_object(self, idx):
    self.value_fields = []
    self.form_clear()

    name = self.combo.itemText(idx)
    if name not in self.obj_map:
      return
    obj = self.obj_map[name]

    for a in obj["annots"]:
      lbl_txt = a.get("lbl", "")
      val = a.get("value", a.get("default", ""))
      lbl = QLabel(lbl_txt)
      lbl.setFont(self.font16)
      field = QLineEdit(str(val))
      field.setFont(self.font16)
      field.setMinimumWidth(120)
      field.setMinimumHeight(30)
      field.returnPressed.connect(self.apply_annotations)
      self.form_layout.addRow(lbl, field)
      self.value_fields.append((a, field))

    self.apply_annotations()

  def apply_annotations(self):
    name = self.combo.currentText()
    if name not in self.obj_map:
      return
    obj = self.obj_map[name]

    for a, field in self.value_fields:
      a["value"] = field.text()

    img_map = annotate_image(self.cfg, self.default_units)
    img, _ = img_map.get(name, (None, None))
    if img:
      qimg = self.pil_to_qimage(img)
      self.image_label.setPixmap(QPixmap.fromImage(qimg))

      # Resize the main window to match image + top area
      img_w, img_h = img.size
      total_h = img_h + self.top_reserved_height + 80
      self.resize(max(img_w + 40, 600), total_h)

  def save_image(self):
    name = self.combo.currentText()
    if name not in self.obj_map:
      return
    obj = self.obj_map[name]

    for a, field in self.value_fields:
      a["value"] = field.text()

    img_map = annotate_image(self.cfg, self.default_units)
    img, outdir = img_map.get(name, (None, None))
    if not img:
      return

    if not os.path.exists(outdir):
      os.makedirs(outdir)
    outname = os.path.splitext(obj["img"])[0] + "_annotated.png"
    path = os.path.join(outdir, outname)
    img.save(path)
    QMessageBox.information(self, "Saved", f"Saved to:\n{path}")

  def pil_to_qimage(self, im):
    if im.mode != "RGBA":
      im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    return QImage(data, im.size[0], im.size[1], QImage.Format.Format_RGBA8888)

if __name__ == "__main__":
  app = QApplication(sys.argv)
  w = MainWindow()
  w.show()
  sys.exit(app.exec())

