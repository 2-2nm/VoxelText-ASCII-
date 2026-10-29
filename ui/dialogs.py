from PySide6.QtWidgets import QFileDialog

IMAGE_FILTER = "Image Files (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.jfif);;All Files (*.*)"
VIDEO_FILTER = "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
TEXT_FILTER = "Text File (*.txt)"
PNG_FILTER = "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)"
MP4_FILTER = "MP4 Video (*.mp4);;All Files (*.*)"
VXL_FILTER = "Voxel Model (*.vxl);;All Files (*.*)"


def open_file(parent, title, name_filter):
    return QFileDialog.getOpenFileName(parent, title, "", name_filter)[0]


def save_file(parent, title, default_name, name_filter):
    return QFileDialog.getSaveFileName(parent, title, default_name, name_filter)[0]
