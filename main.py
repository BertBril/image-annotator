import sys, os, json
from PyQt6.QtWidgets import (
  QApplication, QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
  QPushButton, QLineEdit, QFileDialog, QMessageBox, QGridLayout, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt6.QtCore import Qt
from annotator import annotate_image, resolve_path

class MainWindow(QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("Image Annotator")
    self.setWindowIcon(QIcon(resolve_path("app.svg")))

    with open(resolve_path("config.json"), "r") as f:
      self.cfg = json.load(f)

    self.default_font = self.cfg.get("fontfamily", "arial")
    self.default_units = ""

    # UI Elements
    self.combo = QComboBox()
    self.combo.setFont(QFont('', 16))
    self.image_label = QLabel()
    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    self.value_fields = []
    self.unit_fields = []

    self.grid = QGridLayout()
    label = QLabel("Image")
    label.setFont(QFont('', 16))
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    self.grid.addWidget(label, 0, 0)
    self.grid.addWidget(self.combo, 0, 1)

    self.grid_frame = QFrame()
    self.grid_frame.setLayout(self.grid)

    self.apply_button = QPushButton("Apply")
    self.save_button = QPushButton("Save")
    self.apply_button.setFont(QFont('', 16))
    self.save_button.setFont(QFont('', 16))

    self.apply_button.clicked.connect(self.apply_annotations)
    self.save_button.clicked.connect(self.save_image)

    top_layout = QVBoxLayout()
    top_layout.addWidget(self.grid_frame)

    button_layout = QHBoxLayout()
    button_layout.addWidget(self.apply_button)
    button_layout.addWidget(self.save_button)

    layout = QVBoxLayout()
    layout.addLayout(top_layout)
    layout.addLayout(button_layout)
    layout.addWidget(self.image_label, stretch=3)
    self.setLayout(layout)

    # Delay connections until initialized
    self.obj_map = {}
    for obj in self.cfg["objects"]:
      name = obj.get("name", obj["img"])
      self.obj_map[name] = obj
      self.combo.addItem(name)

    defobj = self.cfg.get("defobj")
    if defobj:
      idx = self.combo.findText(defobj)
      if idx >= 0:
        self.combo.setCurrentIndex(idx)

    self.combo.currentIndexChanged.connect(self.load_object)
    self.load_object(self.combo.currentIndex())

  def load_object(self, idx):
    self.value_fields = []
    self.unit_fields = []

    # Clear grid except row 0
    while self.grid.count() > 2:
      item = self.grid.takeAt(2)
      w = item.widget()
      if w:
        w.deleteLater()

    name = self.combo.currentText()
    obj = self.obj_map.get(name)
    if not obj:
      return

    annots = obj.get("annots", [])
    for i, a in enumerate(annots):
      row = i + 1
      lbl = QLabel(a.get("lbl", ""))
      lbl.setFont(QFont('', 16))
      lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

      val_edit = QLineEdit(str(a.get("value", a.get("default", ""))))
      val_edit.setFont(QFont('', 16))
      val_edit.setMinimumWidth(100)
      val_edit.returnPressed.connect(self.apply_annotations)

      units_edit = QLineEdit(str(a.get("units", "")))
      units_edit.setFont(QFont('', 16))
      units_edit.setMinimumWidth(80)
      units_edit.returnPressed.connect(self.apply_annotations)

      self.grid.addWidget(lbl, row, 0)
      self.grid.addWidget(val_edit, row, 1)
      self.grid.addWidget(units_edit, row, 2)

      self.value_fields.append((a, val_edit))
      self.unit_fields.append(units_edit)

    self.adjustSize()
    self.apply_annotations()

  def apply_annotations(self):
    name = self.combo.currentText()
    obj = self.obj_map[name]

    for (a, val_edit), units_edit in zip(self.value_fields, self.unit_fields):
      a["value"] = val_edit.text()
      a["units"] = units_edit.text()

    img_map = annotate_image(self.cfg, self.default_units)
    img, _ = img_map[name]
    qimg = self.pil_to_qimage(img)
    self.image_label.setPixmap(QPixmap.fromImage(qimg))

  def save_image(self):
    name = self.combo.currentText()
    obj = self.obj_map[name]

    for (a, val_edit), units_edit in zip(self.value_fields, self.unit_fields):
      a["value"] = val_edit.text()
      a["units"] = units_edit.text()

    img_map = annotate_image(self.cfg, self.default_units)
    img, outdir = img_map[name]
    if not os.path.exists(outdir):
      os.makedirs(outdir)

    base = os.path.splitext(obj["img"])[0]
    suggested = os.path.join(outdir, base + "_annotated.png")
    path, _ = QFileDialog.getSaveFileName(self, "Save Image As", suggested, "PNG Files (*.png)")
    if not path:
      return
    if not path.lower().endswith(".png"):
      path += ".png"
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
  w.resize(1000, 800)
  w.show()
  sys.exit(app.exec())

