import sys, os, json
from PyQt6.QtWidgets import (
  QApplication, QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
  QPushButton, QLineEdit, QMessageBox, QScrollArea, QFormLayout
)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt
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

    self.combo = QComboBox()
    self.combo.setFont(QFont(self.default_font, 16))

    self.image_label = QLabel()
    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    self.form_layout = QFormLayout()
    self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    self.scroll = QScrollArea()
    self.form_widget = QWidget()
    self.form_widget.setLayout(self.form_layout)
    self.scroll.setWidgetResizable(True)
    self.scroll.setWidget(self.form_widget)

    self.apply_button = QPushButton("Apply")
    self.save_button = QPushButton("Save")
    self.apply_button.setFont(QFont(self.default_font, 16))
    self.save_button.setFont(QFont(self.default_font, 16))

    top_layout = QHBoxLayout()
    img_label = QLabel("Image")
    img_label.setFont(QFont(self.default_font, 16))
    top_layout.addWidget(img_label)
    top_layout.addWidget(self.combo)

    button_layout = QHBoxLayout()
    button_layout.addWidget(self.apply_button)
    button_layout.addWidget(self.save_button)

    layout = QVBoxLayout()
    layout.addLayout(top_layout)
    layout.addWidget(self.scroll, stretch=1)
    layout.addLayout(button_layout)
    layout.addWidget(self.image_label, stretch=3)
    self.setLayout(layout)

    # Populate combo and object map
    for obj in self.cfg["objects"]:
      name = obj.get("name", obj["img"])
      self.combo.addItem(name)
      self.obj_map[name] = obj

    # Hook up signals only after everything is initialized
    self.combo.currentIndexChanged.connect(self.load_object)
    self.apply_button.clicked.connect(self.apply_annotations)
    self.save_button.clicked.connect(self.save_image)

    defobj = self.cfg.get("defobj")
    if defobj:
      idx = self.combo.findText(defobj)
      if idx >= 0:
        self.combo.setCurrentIndex(idx)
        self.load_object(idx)
    else:
      self.load_object(0)

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
      lbl = a.get("lbl", "")
      val = a.get("value", a.get("default", ""))
      field = QLineEdit(str(val))
      field.setFont(QFont(self.default_font, 16))
      field.returnPressed.connect(self.apply_annotations)
      self.form_layout.addRow(QLabel(lbl), field)
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
  w.resize(900, 700)
  w.show()
  sys.exit(app.exec())

