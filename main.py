import sys, os, json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QComboBox, QLineEdit, QFileDialog
)
from PyQt6.QtGui import QPixmap, QImage
from annotator import annotate_image, resolve_path

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Annotator")
        layout = QVBoxLayout()
        cfgfile = resolve_path("APP:config.json")
        with open(cfgfile, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.def_unit = QLineEdit(self)
        self.def_unit.setPlaceholderText("Default units (e.g. cm)")
        layout.addWidget(self.def_unit)
        self.objs = annotate_image(self.cfg, "")
        self.objsel = QComboBox()
        self.objsel.addItems(list(self.objs.keys()))
        layout.addWidget(self.objsel)
        self.preview = QLabel()
        layout.addWidget(self.preview)
        btnapply = QPushButton("Apply")
        btnapply.clicked.connect(self.apply)
        layout.addWidget(btnapply)
        btnsave = QPushButton("Save As...")
        btnsave.clicked.connect(self.save)
        layout.addWidget(btnsave)
        self.setLayout(layout)
        defobj = self.cfg.get("defobj", "")
        idx = self.objsel.findText(defobj)
        if idx >= 0:
            self.objsel.setCurrentIndex(idx)
        self.apply()

    def apply(self):
        default = self.def_unit.text()
        self.objs = annotate_image(self.cfg, default)
        key = self.objsel.currentText()
        im, od = self.objs[key]
        qim = QImage(im.tobytes(), im.width, im.height, QImage.Format.Format_RGBA8888)
        self.preview.setPixmap(QPixmap.fromImage(qim))

    def save(self):
        key = self.objsel.currentText()
        im, od = self.objs[key]
        fn, _ = QFileDialog.getSaveFileName(self, "Save Image", od, "PNG Files (*.png)")
        if fn:
            im.save(fn, "PNG")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

