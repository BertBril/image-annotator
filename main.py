import sys, os, json
from PyQt6.QtWidgets import (
  QApplication, QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
  QPushButton, QLineEdit, QFileDialog, QMessageBox, QGridLayout, QFrame,
  QSplitter
)
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtCore import Qt, QSize
from annotator import annotate_image, resolve_path
from iconifier import create_icon_from_pil
from PIL import Image


class MainWindow(QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("Image Annotator")
    self.setWindowIcon(QIcon(resolve_path("app.svg")))

    with open(resolve_path("config.json"), "r") as f:
      self.cfg = json.load(f)

    self.default_units = ""
    self.value_fields = []
    self.unit_fields = []
    self.obj_map = {}

    self.combo = QComboBox()
    self.combo.setStyleSheet("font-size: 16pt")
    self.label_combo = QLabel("Image")
    self.label_combo.setStyleSheet("font-size: 16pt")
    self.label_combo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    self.image_label = QLabel()
    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    from PyQt6.QtWidgets import QStyle

    self.apply_button = QPushButton("&Apply")
    self.save_button = QPushButton("&Save...")

    icon_apply = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
    icon_save = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)

    self.apply_button.setIcon(icon_apply)
    self.save_button.setIcon(icon_save)

    self.apply_button.setStyleSheet("font-size: 16pt")
    self.save_button.setStyleSheet("font-size: 16pt")

    self.apply_button.setFixedSize(130, 40)
    self.save_button.setFixedSize(130, 40)

    self.frame_combo = QFrame()
    hcombo = QHBoxLayout()
    hcombo.addStretch(1)
    hcombo.addWidget(self.label_combo)
    hcombo.addWidget(self.combo)
    hcombo.addStretch(1)
    self.frame_combo.setLayout(hcombo)

    self.frame_fields = QFrame()
    self.grid = QGridLayout()
    self.frame_fields.setLayout(self.grid)

    self.frame_buttons = QFrame()
    hbtn = QHBoxLayout()
    hbtn.addStretch(1)
    hbtn.addWidget(self.apply_button)
    hbtn.addWidget(self.save_button)
    hbtn.addStretch(1)
    self.frame_buttons.setLayout(hbtn)

    self.frame_top = QFrame()
    vtop = QVBoxLayout()
    vtop.addWidget(self.frame_combo)
    vtop.addWidget(self.frame_fields)
    vtop.addWidget(self.frame_buttons)
    self.frame_top.setLayout(vtop)

    self.splitter = QSplitter(Qt.Orientation.Vertical)
    self.splitter.addWidget(self.frame_top)
    self.splitter.addWidget(self.image_label)
    self.splitter.setSizes([200, 500])
    self.splitter.setHandleWidth(6)
    self.splitter.setStyleSheet("QSplitter::handle { background-color: #888; }")

    layout = QVBoxLayout()
    layout.addWidget(self.splitter)
    self.setLayout(layout)

    for obj in self.cfg["objects"]:
      name = obj.get("name", obj["img"]).strip()
      img_path = os.path.join(resolve_path(self.cfg["inputdir"]), obj["img"])
      if os.path.exists(img_path):
        pil_image = Image.open(img_path)
        icon_image = create_icon_from_pil(pil_image, size=(16, 16))
        qimg = self.pil_to_qimage(icon_image)
        icon = QIcon(QPixmap.fromImage(qimg))
      else:
        icon = QIcon()
      self.combo.addItem(icon, name)
      self.obj_map[name] = obj

    self.combo_index_connected = False
    self.delayed_hookup()

  def delayed_hookup(self):
    self.combo.currentIndexChanged.connect(self.load_object)
    self.apply_button.clicked.connect(self.apply_annotations)
    self.save_button.clicked.connect(self.save_image)
    defobj = self.cfg.get("defobj")
    idx = self.combo.findText(defobj) if defobj else 0
    if idx < 0:
      idx = 0
    self.combo.setCurrentIndex(idx)
    self.load_object(idx)

  def load_object(self, idx):
    self.clear_fields()
    name = self.combo.currentText()
    obj = self.obj_map[name]
    annots = obj["annots"]
    self.value_fields = []
    self.unit_fields = []

    for row, a in enumerate(annots):
      lbl = QLabel(a.get("lbl", ""))
      lbl.setStyleSheet("font-size: 16pt")
      lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

      val = QLineEdit(str(a.get("value", a.get("default", ""))))
      val.setStyleSheet("font-size: 16pt")
      val.setMinimumWidth(100)
      val.returnPressed.connect(self.apply_annotations)

      units = QLineEdit(a.get("units", ""))
      units.setStyleSheet("font-size: 16pt")
      units.setMinimumWidth(60)
      units.returnPressed.connect(self.apply_annotations)

      self.grid.addWidget(lbl, row, 0)
      self.grid.addWidget(val, row, 1)
      self.grid.addWidget(units, row, 2)

      self.value_fields.append((a, val))
      self.unit_fields.append((a, units))

    self.apply_annotations()

  def clear_fields(self):
    while self.grid.count():
      item = self.grid.takeAt(0)
      w = item.widget()
      if w:
        w.deleteLater()

  def apply_annotations(self):
    name = self.combo.currentText()
    obj = self.obj_map[name]
    for (a, val), (_, units) in zip(self.value_fields, self.unit_fields):
      a["value"] = val.text()
      a["units"] = units.text()
    img_map = annotate_image(self.cfg, self.default_units)
    img, _ = img_map[name]
    self.image_label.setPixmap(QPixmap.fromImage(self.pil_to_qimage(img)))

  def save_image(self):
    name = self.combo.currentText()
    obj = self.obj_map[name]
    for (a, val), (_, units) in zip(self.value_fields, self.unit_fields):
      a["value"] = val.text()
      a["units"] = units.text()
    img_map = annotate_image(self.cfg, self.default_units)
    img, outdir = img_map[name]
    if not os.path.exists(outdir):
      os.makedirs(outdir)
    basename = os.path.splitext(obj["img"])[0]
    default_path = os.path.join(outdir, basename + "_annotated.png")
    path, _ = QFileDialog.getSaveFileName(self, "Save Image", default_path, "PNG Image (*.png)")
    if not path:
      return
    if not path.lower().endswith(".png"):
      path += ".png"
    img.save(path)
    QMessageBox.information(self, "Saved", "Saved to:\n" + path)

  def pil_to_qimage(self, im):
    if im.mode != "RGBA":
      im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    qimg = QImage(data, im.size[0], im.size[1], QImage.Format.Format_RGBA8888)
    return qimg


if __name__ == "__main__":
  app = QApplication(sys.argv)
  w = MainWindow()
  w.resize(1000, 800)
  w.show()
  sys.exit(app.exec())

