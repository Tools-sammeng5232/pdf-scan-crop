"""扫描 PDF 裁边桌面程序（PySide6）。"""

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
import time
import traceback
import webbrowser
from dataclasses import replace
from pathlib import Path

from PIL import Image
from PySide6.QtCore import (
    QEvent,
    QItemSelectionModel,
    QLibraryInfo,
    QPoint,
    QRect,
    QSettings,
    QSize,
    Qt,
    QTimer,
    QTranslator,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QImage, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import fix_pdf_edges as crop


HANDLE = 7
ROTATE_LIMIT = 180.0
PREVIEW_MAX = 2400
MIN_ZOOM = 1.0
MAX_ZOOM = 8.0
ZOOM_STEP = 1.2
UI_SETTINGS = "ui-settings.json"

STRINGS = {
    "zh": {
        "app_title": "PDF 扫描裁边",
        "subtitle": "只去扫描脏边，空白页边尽量留着 · 用下方滑条旋转页面 · 不覆盖原 PDF",
        "language": "界面语言",
        "file": "文件",
        "src_pdf": "源 PDF",
        "out_pdf": "输出 PDF",
        "browse": "浏览",
        "reuse": "复用已抽出的页面图（同一本书再次处理时更快）",
        "open_after": "完成后自动打开 PDF",
        "crop_mode": "裁切方式",
        "tight": "贴着文字继续往里裁（会多切掉空白页边）",
        "auto_rotate": "自动校直歪斜页面（书脊、轻微倾斜）",
        "ocr": "生成时 OCR（可搜索 PDF，繁/简/英/日，较慢）",
        "ocr_txt": "另外写出同名 txt",
        "hint": "默认只去掉黑边、装订阴影和扫描脏边。扫描件本身没有文字层，必须勾选 OCR 或事后点「OCR 全书」，才能在 PDF 里复制文字。",
        "min_full": "相对原图最少保留",
        "min_page": "稀疏页最少保留",
        "pages_section": "页码（可空）",
        "pages_only": "只处理这些页（按整理后的页码）",
        "pages_ph": "只处理部分页，例如 1,14,20-23",
        "inspect_pages": "检查图页码",
        "inspect_ph": "生成后再渲染这些页的检查图",
        "advanced": "高级选项",
        "jobs": "并行线程",
        "dpi": "渲染 DPI",
        "work_dir": "缓存目录",
        "analyze": "分析预览",
        "generate": "生成 PDF",
        "ocr_page": "OCR 本页",
        "ocr_book": "OCR 全书",
        "cancel": "取消",
        "open_result": "打开结果",
        "open_folder": "打开文件夹",
        "log": "运行日志",
        "prev": "上一页",
        "next": "下一页",
        "no_pdf": "尚未打开 PDF",
        "reset_page": "恢复本页自动裁切",
        "keep_full_page": "本页不裁切",
        "keep_full_all": "全部不裁切（每页整页）",
        "kept_full_page": "第 {page} 页已改为整页保留",
        "kept_full_all": "已将 {n} 页改为整页保留，生成时不再裁切",
        "need_analyze_keep": "请先分析预览，再一键不裁切。",
        "uniform_btn": "统一裁边（全书同尺寸）…",
        "uniform_title": "统一裁边",
        "uniform_intro": "从每页原始页边向内裁掉同一尺寸，左 / 上 / 右 / 下可分别填写。重复设置同一数值结果不变；自动裁边裁得更多时保持更内侧的线。",
        "uniform_unit": "单位",
        "unit_cm": "厘米",
        "unit_mm": "毫米",
        "unit_in": "英寸",
        "uniform_hint": "数值按输出 PDF 的实际尺寸换算（未裁整页高约 29.7 厘米），与扫描分辨率无关。应用后蓝框立即更新，可翻页检查；把数值改回 0 再确定即可恢复统一裁边前的框。尚未分析时也可以直接点「按此生成 PDF」。",
        "uniform_generate": "按此生成 PDF",
        "uniform_margins_fmt": "左 {l:g} / 上 {t:g} / 右 {r:g} / 下 {b:g} 厘米",
        "uniform_applied": "已统一裁边 {n} 页：{margins}（从原始页边起至少裁这么多）",
        "uniform_restored": "已恢复统一裁边前的裁切框（{n} 页）",
        "uniform_set_no_plans": "已设置统一裁边：{margins}。可直接点「生成 PDF」，或先「分析预览」再逐页微调。",
        "uniform_preview_note": "统一裁边预览（蓝框）。点「分析预览」后自动套用、可逐页微调；或直接点「生成 PDF」。",
        "rotate_all_ccw": "全书左转 90°",
        "rotate_all_cw": "全书右转 90°",
        "rotate_dir_ccw": "左转 90°",
        "rotate_dir_cw": "右转 90°",
        "rotate_all_confirm": "把全书 {n} 页{dir}？\n\n已分析的页面会按新方向重新计算裁切框；手工拖过的裁切框不保留（旋转后坐标不再适用），统一裁边设置和每页旋转角度会保留累计。",
        "rotate_all_done": "全书已{dir}，正在重新分析…",
        "rotate_all_done_no_plans": "全书已{dir}。点「分析预览」检查，或直接点「生成 PDF」。",
        "organize_btn": "页面整理（排序 / 删页 / 插页）…",
        "organize_title": "页面整理",
        "organize_hint": "不必先「分析预览」即可整理，页码就是整理后的页码（插入页与原有页完全等价）。缩略图一行多页，直接拖动即可移动页面（按住 Ctrl / Shift 可多选后一起拖）；几百页的书可用「移到第 N 页」一步跳转，或点「全屏」放大。删除所选把源页面移出输出（可用「恢复所选」放回末尾），删除插入页则是整个移除。未分析的页面在生成时会自动补算，顺序只影响生成的 PDF，不会改动源文件。",
        "organize_deleted_label": "已删除的页（可恢复）：",
        "org_move_up": "上移 ↑",
        "org_move_down": "下移 ↓",
        "org_delete": "删除所选",
        "org_restore": "恢复所选",
        "org_insert_pdf": "插入 PDF 页…",
        "org_insert_image": "插入图片…",
        "org_insert_blank": "插入空白页",
        "org_duplicate": "复制所选页",
        "org_reset": "恢复原顺序",
        "ins_pdf_title": "插入 PDF 页",
        "import_done_partial": "已插入 {n} 页（来源：{src}），页码 {pages} 无效已跳过",
        "import_page_failed": "插入失败：源 PDF 第 {page} 页 · {exc}",
        "ins_pdf_range": "「{name}」只有 {total} 页，页码 {pages} 无效",
        "ins_pages_label": "要插入的页码（如 3,7,10-12）",
        "ins_pages_ph": "页码，如 3,7,10-12",
        "ins_at_start": "插到开头",
        "ins_at_end": "插到末尾",
        "ins_after_sel": "插到所选之后",
        "ins_image_title": "插入图片",
        "ins_image_filter": "图片文件 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp);;所有文件 (*.*)",
        "ins_enhance_title": "自动优化",
        "ins_enhance_q": "插入的图片要自动优化页面外观吗？",
        "ins_enhance_check": "提亮纸面、加深字迹（像扫描软件）",
        "ins_progress": "正在处理插入页 {i}/{n}…",
        "import_done": "已插入 {n} 页（来源：{src}）",
        "import_failed": "插入页处理失败：{exc}",
        "import_missing": "插入页 {label} 的来源不可用，已保留占位页（可在整理窗口删除）：{exc}",
        "import_page_label": "插入页 {n}",
        "import_src_image": "{n} 张图片",
        "import_src_blank": "空白页",
        "import_src_dup": "复制页",
        "page_label": "第 {page} 页",
        "page_label_orig": "原第 {page} 页",
        "page_label_inserted": "插入页",
        "del_page": "删页",
        "del_page_tip": "把当前页从输出中删除（页面整理里可恢复）",
        "page_deleted": "{label}已从输出中删除，还剩 {n} 页；可在「页面整理」恢复",
        "pages_deleted": "已删除 {n} 页，输出还剩 {m} 页",
        "pages_reordered": "已调整页面顺序（共 {n} 页）",
        "pages_restored": "已恢复 {n} 页",
        "not_analyzed": "未分析",
        "pages_filter_bad": "页码范围无法识别：{text}",
        "no_output_pages": "输出里已经没有页面了：请检查删掉的页面或页码范围设置。",
        "pages_filter_hint": "生成时只输出：{text}（按整理后的页码，共 {n} 页）",
        "pages_filter_empty": "页码范围里没有可用的页",
        "pages_filter_range": "页码超出范围（共 {n} 页）",
        "organize_fullscreen": "全屏",
        "list_updated": "页面列表已更新：共 {n} 页，当前 {page}",
        "organize_zoom_hint": "Ctrl + 滚轮（或 Ctrl + / -）缩放缩略图",
        "ins_select_title": "选择要插入的页",
        "ins_select_hint": "点缩略图勾选要插入的页；也可以在上面的页码框里直接输入（如 3,7,10-12）后点「应用」。",
        "select_spec_apply": "应用",
        "pages_reordered_log": "已调整页面顺序，共 {n} 页",
        "insert_removed": "已移除 {n} 个插入页（记录与图片已清除）",
        "select_pages_btn": "按缩略图选页…",
        "select_pages_title": "选择要导出的页",
        "select_pages_hint": "点缩略图勾选 / 取消勾选，只导出勾选的页；页码就是整理后的页码，插入页同样可选。",
        "select_all": "全选",
        "select_none": "全不选",
        "select_invert": "反选",
        "select_pages_count": "已选 {n} 页",
        "select_pages_applied": "导出页已更新：共 {n} 页",
        "import_orphans": "发现 {n} 个未登记的插入页图片（可能是上次插入未完成）：{names}",
        "org_move_to": "移到第",
        "org_move_apply": "移动",
        "organize_windowed": "退出全屏",
        "ctx_move_up": "上移",
        "ctx_move_down": "下移",
        "ctx_delete_page": "删除此页",
        "ctx_restore_page": "恢复此页（放回末尾）",
        "ctx_duplicate": "复制此页",
        "ctx_insert_after": "在此之后插入",
        "ctx_ins_pdf": "PDF 页…",
        "ctx_ins_image": "图片…",
        "ctx_ins_blank": "空白页",
        "ctx_organize": "页面整理…",
        "need_analyze_organize": "请先「分析预览」或先插入页，再整理页面。",
        "zoom_in": "放大",
        "zoom_out": "缩小",
        "zoom_fit": "适应窗口",
        "hide_left": "隐藏设置",
        "show_left": "显示设置",
        "fullscreen": "全屏裁切",
        "exit_fullscreen": "退出全屏",
        "rotate_ccw": "左转 90°",
        "rotate_cw": "右转 90°",
        "fs_hint": "Esc 退出全屏 · 左右键翻页 · 滚轮缩放 · 下方可旋转",
        "zoom_hint": "滚轮放大；空白处拖动平移。点「全屏裁切」可全屏改裁切和旋转，不必先退出。",
        "rotate_hint": "用下方滑条或数字旋转，范围 -180° 到 180°。拖动时只预览，松开滑条或点“应用旋转”后才重算。",
        "crop_box": "裁切框",
        "left": "左",
        "top": "上",
        "right": "右",
        "bottom": "下",
        "rotate": "旋转",
        "apply_rotate": "应用旋转",
        "page_results": "各页结果",
        "col_page": "页",
        "col_note": "说明",
        "col_box": "裁切框",
        "placeholder": "请先选择一份扫描 PDF",
        "status_idle": "选择一份扫描 PDF，先分析预览，再生成裁边结果。",
        "pick_src": "选择扫描 PDF",
        "save_out": "保存裁边 PDF",
        "pdf_filter": "PDF 文件 (*.pdf);;所有文件 (*.*)",
        "pdf_filter_save": "PDF 文件 (*.pdf)",
        "need_src": "请先选择源 PDF",
        "need_analyze_ocr": "请先分析预览，再对本页做 OCR。",
        "need_analyze_or_out": "请先分析预览，或把已生成的裁边 PDF 填进输出路径，再 OCR 全书。",
        "same_path": "输出文件不能和源 PDF 相同，以免覆盖原书。",
        "missing_src": "找不到源 PDF。",
        "no_result": "还没有生成结果。",
        "busy_quit": "正在处理，确定退出？",
        "job_failed": "处理失败，详见左侧日志。",
        "ocr_fail": "OCR 失败：\n{exc}",
        "ocr_empty": "（没有识别到文字）",
        "ocr_page_title": "第 {page} 页 OCR",
        "read_pages_fail": "无法读取 PDF 页数：\n{exc}",
        "reanalyze_fail": "重新分析失败：\n{exc}",
        "preview_fail": "预览失败：{exc}",
        "open_page_fail": "无法打开第 {page} 页图像：{exc}",
        "opened": "已打开 {name}，共 {pages} 页。可先看预览，再点分析。",
        "opened_log": "打开 {src} ，{pages} 页",
        "pages_total": "共 {pages} 页",
        "crop_unanalyzed": "裁切框：尚未分析",
        "preview_note": "这是原 PDF 预览。点“分析预览”后可拖动蓝色框调整裁切。",
        "crop_fmt": "裁切框：{l}, {t}, {r}, {b}  （{w}×{h}）",
        "page_note": "第 {page} 页 · {note}",
        "page_analyzed": "第 {page} 页 / 已分析 {n} 页",
        "rotating": "第 {page} 页旋转 {angle:+.1f}°，正在重算裁切…",
        "rotated": "第 {page} 页已旋转 {angle:+.1f}°",
        "rotated_log": "第 {page} 页旋转 {angle:+.1f}° · {note}",
        "used_ref": "已用对照文本 {name} 辅助识别",
        "ocr_page_done": "第 {page} 页 OCR 完成，{n} 字",
        "ocr_book_ref": "OCR 全书将对照 {name}",
        "ocr_existing_ref": "给已有 PDF 写入文字层，对照 {name}",
        "ocr_existing": "给已有 PDF 写入文字层：{name}",
        "write_preview": "按当前预览结果写入 {name}",
        "start_job": "开始{title}：{name}",
        "cancelling": "正在取消…",
        "cancel_log": "已请求取消",
        "cancelled": "已取消",
        "failed": "处理失败",
        "ocr_layer_done": "已写入文字层 {name}",
        "ocr_layer_log": "完成：{path}，现在可以复制文字",
        "open_fail": "自动打开失败：{exc}",
        "generated": "已生成 {name}，共 {n} 页",
        "generated_ocr": "完成：{path}，已写入文字层，可以复制文字",
        "generated_no_ocr": "完成：{path}（未 OCR，扫描页无法复制文字）",
        "analyzed": "已分析 {n} 页，可拖动蓝框微调后再生成 PDF",
        "analyzed_log": "分析完成 {n} 页",
        "no_tess": "未找到 Tesseract。请安装 Tesseract-OCR，或把它的安装目录加入 PATH。",
        "no_tessdata": "未找到 OCR 字库（繁中 / 简中 / 英文 / 日文）。",
        "clear_cache": "清理缓存",
        "clear_cache_tip": "删除所有书的页面缓存图，手工调整记录保留",
        "clear_cache_confirm": "将删除 {n} 个缓存文件，共 {mb:.0f} MB。\n手工调整记录会保留，下次分析会重新抽图。确定清理？",
        "cache_empty": "缓存已经是空的。",
        "cache_cleared": "已清理 {n} 个缓存文件，释放 {mb:.0f} MB",
        "forget_edits": "清除本书手工调整",
        "forget_edits_confirm": "清除本书保存的全部手工裁切和旋转？\n清除后需要重新点「分析预览」。",
        "edits_forgotten": "已清除本书保存的手工调整，请重新分析",
        "edits_found": "找到上次保存的手工调整：{crops} 页裁切、{rotates} 页旋转，分析时会自动套用",
        "reset_done": "第 {page} 页已恢复自动裁切",
        "resetting": "第 {page} 页正在重新自动裁切…",
        "ocr_page_running": "正在 OCR 第 {page} 页…",
    },
    "en": {
        "app_title": "PDF Scan Crop",
        "subtitle": "Trim dirty scan edges, keep paper margins · rotate with the slider · never overwrite the original",
        "language": "Language",
        "file": "Files",
        "src_pdf": "Source PDF",
        "out_pdf": "Output PDF",
        "browse": "Browse",
        "reuse": "Reuse extracted page images (faster when processing the same book again)",
        "open_after": "Open the PDF when finished",
        "crop_mode": "Cropping",
        "tight": "Crop tighter to the text (removes more white margin)",
        "auto_rotate": "Auto-deskew tilted pages (spines and slight skew)",
        "ocr": "OCR when generating (searchable PDF; Traditional/Simplified Chinese, English, Japanese; slower)",
        "ocr_txt": "Also write a sidecar .txt file",
        "hint": "By default only dirty edges are removed. Scans have no text layer — turn on OCR or click “OCR book” later if you need copyable text.",
        "min_full": "Keep at least this share of the original",
        "min_page": "Keep at least this share on sparse pages",
        "pages_section": "Pages (optional)",
        "pages_only": "Only these pages (arranged numbers)",
        "pages_ph": "Subset of pages, e.g. 1,14,20-23",
        "inspect_pages": "Inspection pages",
        "inspect_ph": "Render review images for these pages after export",
        "advanced": "Advanced",
        "jobs": "Worker threads",
        "dpi": "Render DPI",
        "work_dir": "Cache folder",
        "analyze": "Analyze / preview",
        "generate": "Export PDF",
        "ocr_page": "OCR this page",
        "ocr_book": "OCR book",
        "cancel": "Cancel",
        "open_result": "Open result",
        "open_folder": "Open folder",
        "log": "Log",
        "prev": "Previous",
        "next": "Next",
        "no_pdf": "No PDF opened",
        "reset_page": "Reset this page to auto crop",
        "keep_full_page": "Keep this page full",
        "keep_full_all": "Keep all pages full",
        "kept_full_page": "Page {page} now keeps the full page",
        "kept_full_all": "Set {n} pages to keep the full page; export will not crop them",
        "need_analyze_keep": "Analyze the book first, then keep pages uncropped.",
        "uniform_btn": "Uniform margins…",
        "uniform_title": "Uniform margins",
        "uniform_intro": "Crop the same size off every page, measured from each original page edge; left / top / right / bottom are set separately. Setting the same values again changes nothing; where auto-crop already cuts more, the inner line is kept.",
        "uniform_unit": "Unit",
        "unit_cm": "cm",
        "unit_mm": "mm",
        "unit_in": "inch",
        "uniform_hint": "Values use the output PDF's real size (an uncropped page is about 29.7 cm tall), independent of scan resolution. The blue boxes update immediately; set the values back to 0 to restore the boxes from before uniform cropping. Without analyzing first you can also click “Export with these margins”.",
        "uniform_generate": "Export with these margins",
        "uniform_margins_fmt": "left {l:g} / top {t:g} / right {r:g} / bottom {b:g} cm",
        "uniform_applied": "Applied uniform margins to {n} pages: {margins} (at least this much from each original edge)",
        "uniform_restored": "Restored the crop boxes from before uniform margins ({n} pages)",
        "uniform_set_no_plans": "Uniform margins set: {margins}. Click “Export PDF” directly, or analyze first and fine-tune per page.",
        "uniform_preview_note": "Uniform-margin preview (blue box). Analyze to apply and fine-tune per page, or click “Export PDF” directly.",
        "rotate_all_ccw": "Rotate all 90° CCW",
        "rotate_all_cw": "Rotate all 90° CW",
        "rotate_dir_ccw": "90° counterclockwise",
        "rotate_dir_cw": "90° clockwise",
        "rotate_all_confirm": "Rotate all {n} pages {dir}?\n\nAnalyzed pages are re-cropped in the new orientation; hand-dragged crop boxes are not kept (they no longer fit after rotation). The uniform-margin setting and per-page angles accumulate.",
        "rotate_all_done": "All pages rotated {dir}; re-analyzing…",
        "rotate_all_done_no_plans": "All pages rotated {dir}. Click Analyze to check, or Export PDF directly.",
        "organize_btn": "Organize pages…",
        "organize_title": "Organize pages",
        "organize_hint": "No analysis needed first; page numbers are the arranged ones and inserted pages behave exactly like source pages. Thumbnails flow several per row - drag pages straight to a new spot (Ctrl/Shift to drag a block); for long books use Move to page N or Full screen. Delete moves source pages out of the export (Restore puts them back at the end); deleting an inserted page removes it entirely. Unanalyzed pages are processed automatically at export time; the order only affects the exported PDF and source files are never touched.",
        "organize_deleted_label": "Deleted pages (restorable):",
        "org_move_up": "Move up",
        "org_move_down": "Move down",
        "org_delete": "Delete",
        "org_restore": "Restore",
        "org_insert_pdf": "Insert PDF pages…",
        "org_insert_image": "Insert images…",
        "org_insert_blank": "Insert blank page",
        "org_duplicate": "Duplicate selection",
        "org_reset": "Reset order",
        "ins_pdf_title": "Insert PDF pages",
        "import_done_partial": "Inserted {n} page(s) from {src}; page(s) {pages} were invalid and skipped",
        "import_page_failed": "Insert failed: source page {page} · {exc}",
        "ins_pdf_range": "{name} only has {total} pages; page(s) {pages} are invalid",
        "ins_pages_label": "Pages to insert (e.g. 3,7,10-12)",
        "ins_pages_ph": "pages, e.g. 3,7,10-12",
        "ins_at_start": "at the start",
        "ins_at_end": "at the end",
        "ins_after_sel": "after the selection",
        "ins_image_title": "Insert images",
        "ins_image_filter": "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp);;All files (*.*)",
        "ins_enhance_title": "Auto enhance",
        "ins_enhance_q": "Auto-enhance the inserted images?",
        "ins_enhance_check": "Whiten the paper and deepen the ink (scanner style)",
        "ins_progress": "Processing inserted page {i}/{n}…",
        "import_done": "Inserted {n} page(s) (source: {src})",
        "import_failed": "Failed to process inserted pages: {exc}",
        "import_missing": "Source for inserted page {label} is unavailable; kept a placeholder page (delete it from the organizer): {exc}",
        "import_page_label": "Inserted {n}",
        "import_src_image": "{n} image(s)",
        "import_src_blank": "blank page",
        "import_src_dup": "duplicate",
        "page_label": "page {page}",
        "page_label_orig": "was page {page}",
        "page_label_inserted": "inserted page",
        "del_page": "Delete",
        "del_page_tip": "Remove the current page from the export (restorable in Organize pages)",
        "page_deleted": "{label} removed from the export, {n} pages left; restore it via Organize pages",
        "pages_deleted": "Deleted {n} pages, {m} left in the export",
        "pages_reordered": "Page order updated ({n} pages)",
        "pages_restored": "Restored {n} page(s)",
        "not_analyzed": "Not analyzed yet",
        "pages_filter_bad": "Cannot read the page range: {text}",
        "no_output_pages": "No pages left in the output: check deleted pages or the page range.",
        "pages_filter_hint": "Export only: {text} (arranged numbers, {n} pages)",
        "pages_filter_empty": "The page range matches no page",
        "pages_filter_range": "Page number out of range ({n} pages)",
        "organize_fullscreen": "Full screen",
        "list_updated": "Page list updated: {n} page(s), now on {page}",
        "organize_zoom_hint": "Ctrl + wheel (or Ctrl + / -) zooms the thumbnails",
        "ins_select_title": "Choose pages to insert",
        "ins_select_hint": "Tick the pages to insert, or type page numbers above (e.g. 3,7,10-12) and press Apply.",
        "select_spec_apply": "Apply",
        "pages_reordered_log": "Page order updated, {n} page(s)",
        "insert_removed": "Removed {n} inserted page(s) (records and images cleared)",
        "select_pages_btn": "Pick pages...",
        "select_pages_title": "Choose pages to export",
        "select_pages_hint": "Tick the thumbnails to keep in the export; numbers follow the arrangement and inserted pages work the same way.",
        "select_all": "Select all",
        "select_none": "Select none",
        "select_invert": "Invert",
        "select_pages_count": "{n} page(s) selected",
        "select_pages_applied": "Export pages updated: {n}",
        "import_orphans": "{n} unregistered inserted image(s) found (a previous insert may not have finished): {names}",
        "org_move_to": "Move to",
        "org_move_apply": "Move",
        "organize_windowed": "Exit full screen",
        "ctx_move_up": "Move up",
        "ctx_move_down": "Move down",
        "ctx_delete_page": "Delete this page",
        "ctx_restore_page": "Restore this page (to the end)",
        "ctx_duplicate": "Duplicate this page",
        "ctx_insert_after": "Insert after this page",
        "ctx_ins_pdf": "PDF pages…",
        "ctx_ins_image": "Images…",
        "ctx_ins_blank": "Blank page",
        "ctx_organize": "Organize pages…",
        "need_analyze_organize": "Analyze first, or insert pages, before organizing.",
        "zoom_in": "Zoom in",
        "zoom_out": "Zoom out",
        "zoom_fit": "Fit",
        "hide_left": "Hide settings",
        "show_left": "Show settings",
        "fullscreen": "Full-screen crop",
        "exit_fullscreen": "Exit full screen",
        "rotate_ccw": "Rotate 90° CCW",
        "rotate_cw": "Rotate 90° CW",
        "fs_hint": "Esc exits · arrows change page · scroll zooms · rotate below",
        "zoom_hint": "Scroll to zoom; drag empty space to pan. Full-screen crop lets you crop and rotate without leaving.",
        "rotate_hint": "Rotate with the slider or the number box, −180° to 180°. Dragging only previews; release the slider or click Apply rotate to recompute.",
        "crop_box": "Crop box",
        "left": "L",
        "top": "T",
        "right": "R",
        "bottom": "B",
        "rotate": "Rotate",
        "apply_rotate": "Apply rotate",
        "page_results": "Page results",
        "col_page": "Page",
        "col_note": "Note",
        "col_box": "Crop",
        "placeholder": "Choose a scanned PDF first",
        "status_idle": "Choose a scanned PDF, analyze it, then export the cropped file.",
        "pick_src": "Choose scanned PDF",
        "save_out": "Save cropped PDF",
        "pdf_filter": "PDF files (*.pdf);;All files (*.*)",
        "pdf_filter_save": "PDF files (*.pdf)",
        "need_src": "Choose a source PDF first",
        "need_analyze_ocr": "Analyze the book first, then OCR this page.",
        "need_analyze_or_out": "Analyze first, or put an existing cropped PDF in the output path, then click OCR book.",
        "same_path": "The output file cannot be the same as the source PDF.",
        "missing_src": "Source PDF not found.",
        "no_result": "Nothing has been exported yet.",
        "busy_quit": "A job is still running. Quit anyway?",
        "job_failed": "The job failed. See the log on the left.",
        "ocr_fail": "OCR failed:\n{exc}",
        "ocr_empty": "(no text recognized)",
        "ocr_page_title": "Page {page} OCR",
        "read_pages_fail": "Could not read the PDF page count:\n{exc}",
        "reanalyze_fail": "Could not re-analyze this page:\n{exc}",
        "preview_fail": "Preview failed: {exc}",
        "open_page_fail": "Could not open page {page}: {exc}",
        "opened": "Opened {name}, {pages} pages. Preview first, then analyze.",
        "opened_log": "Opened {src} , {pages} pages",
        "pages_total": "{pages} pages",
        "crop_unanalyzed": "Crop box: not analyzed yet",
        "preview_note": "This is the original PDF. Click Analyze / preview, then drag the blue box.",
        "crop_fmt": "Crop: {l}, {t}, {r}, {b}  ({w}×{h})",
        "page_note": "Page {page} · {note}",
        "page_analyzed": "Page {page} / {n} analyzed",
        "rotating": "Page {page} rotated {angle:+.1f}°, recomputing crop…",
        "rotated": "Page {page} rotated {angle:+.1f}°",
        "rotated_log": "Page {page} rotated {angle:+.1f}° · {note}",
        "used_ref": "Using companion text {name} for OCR",
        "ocr_page_done": "Page {page} OCR done, {n} characters",
        "ocr_book_ref": "OCR book will use {name}",
        "ocr_existing_ref": "Adding a text layer to the existing PDF, using {name}",
        "ocr_existing": "Adding a text layer to {name}",
        "write_preview": "Writing {name} from the current preview",
        "start_job": "Starting {title}: {name}",
        "cancelling": "Cancelling…",
        "cancel_log": "Cancel requested",
        "cancelled": "Cancelled",
        "failed": "Failed",
        "ocr_layer_done": "Wrote text layer on {name}",
        "ocr_layer_log": "Done: {path}. Text can be copied now.",
        "open_fail": "Could not open automatically: {exc}",
        "generated": "Wrote {name}, {n} pages",
        "generated_ocr": "Done: {path}. Text layer written; text can be copied.",
        "generated_no_ocr": "Done: {path} (no OCR; scan pages are not copyable)",
        "analyzed": "Analyzed {n} pages. Drag the blue box if needed, then export.",
        "analyzed_log": "Analyzed {n} pages",
        "no_tess": "Tesseract was not found. Install Tesseract-OCR or add it to PATH.",
        "no_tessdata": "OCR language data is missing (Traditional/Simplified Chinese, English, Japanese).",
        "clear_cache": "Clear cache",
        "clear_cache_tip": "Delete cached page images of every book; saved manual edits are kept",
        "clear_cache_confirm": "Delete {n} cached files ({mb:.0f} MB)?\nSaved manual edits are kept; pages are extracted again on the next analysis.",
        "cache_empty": "The cache is already empty.",
        "cache_cleared": "Cleared {n} cached files, freed {mb:.0f} MB",
        "forget_edits": "Forget this book's manual edits",
        "forget_edits_confirm": "Forget all saved manual crops and rotations for this book?\nYou will need to click Analyze / preview again.",
        "edits_forgotten": "Forgot this book's saved manual edits; analyze again",
        "edits_found": "Found saved manual edits: {crops} crops, {rotates} rotations; they are applied on analysis",
        "reset_done": "Page {page} is back to the automatic crop",
        "resetting": "Re-running the automatic crop for page {page}…",
        "ocr_page_running": "Running OCR on page {page}…",
    },
}


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    """Bundled read-only file such as the icon: _internal\\ when frozen, the source folder otherwise."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def app_settings() -> QSettings:
    """%APPDATA%\\PDF裁边\\PDF裁边.ini, per user and never inside the program folder."""
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, crop.APP_NAME, crop.APP_NAME)


def load_ui_lang() -> str:
    lang = str(app_settings().value("lang", "") or "").lower()
    if not lang:
        # One-time migration from the old ui-settings.json that lived beside the exe.
        try:
            data = json.loads((app_dir() / UI_SETTINGS).read_text(encoding="utf-8"))
            lang = str(data.get("lang", "zh")).lower()
        except Exception:
            lang = "zh"
    return lang if lang in STRINGS else "zh"


def save_ui_lang(lang: str) -> None:
    app_settings().setValue("lang", lang)


def install_qt_translator(app: QApplication, lang: str) -> None:
    """Chinese labels for Qt's own buttons (是/否/确定/取消) in the Chinese UI."""
    old = getattr(app, "_pdf_crop_translator", None)
    if old is not None:
        app.removeTranslator(old)
        app._pdf_crop_translator = None
    if lang != "zh":
        return
    translator = QTranslator(app)
    if translator.load("qtbase_zh_CN", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator)
        app._pdf_crop_translator = translator


def open_path(path: Path) -> None:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(str(path))
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        import subprocess

        subprocess.Popen(["open", str(path)])
    else:
        webbrowser.open(path.as_uri())


def render_pdf_page(src: Path, page: int, dpi: int = 96) -> Image.Image:
    if not crop.HAS_FITZ:
        raise RuntimeError("未安装 PyMuPDF，无法预览 PDF")
    with crop.fitz.open(src) as doc:
        if page < 1 or page > doc.page_count:
            raise ValueError(f"页码 {page} 超出范围")
        pix = doc[page - 1].get_pixmap(dpi=dpi, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def pdf_page_thumbs(path: Path, dpi: int = 16) -> dict[int, QPixmap]:
    """Small previews of every page in an arbitrary PDF (for the insert picker)."""
    thumbs: dict[int, QPixmap] = {}
    with crop.fitz.open(path) as doc:
        for number in range(1, doc.page_count + 1):
            pix = doc[number - 1].get_pixmap(dpi=dpi)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            image.thumbnail((120, 168))
            thumbs[number] = pil_to_pixmap(image)
    return thumbs


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgb = image.convert("RGB")
    qimage = QImage(rgb.tobytes("raw", "RGB"), rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def load_preview_image(path: Path, max_side: int = PREVIEW_MAX) -> Image.Image:
    with Image.open(path) as im:
        if getattr(im, "format", None) == "JPEG":
            im.draft("RGB", (max_side, max_side))
        rgb = im.convert("RGB")
        rgb.thumbnail((max_side, max_side), Image.Resampling.BILINEAR)
        return rgb.copy()


def downscale_preview(image: Image.Image, max_side: int = PREVIEW_MAX) -> Image.Image:
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    width, height = rgb.size
    if max(width, height) <= max_side:
        return rgb.copy()
    scale = max_side / max(width, height)
    return rgb.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.BILINEAR)


def clamp_angle(angle: float) -> float:
    return max(-ROTATE_LIMIT, min(ROTATE_LIMIT, angle))


def wrap_angle(angle: float) -> float:
    """Wrap into (-180, 180] so repeated 90-degree turns accumulate instead of clamping."""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped <= -180.0 else wrapped


class CropView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(240, 120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.full_size = (1, 1)
        self.crop = (0, 0, 1, 1)
        self.scale = 1.0
        self.origin = QPoint(0, 0)
        self.pixmap: QPixmap | None = None
        self.original_pixmap: QPixmap | None = None
        self.enabled = False
        self.rotate_deg = 0.0
        self.live_angle = 0.0
        self._rotating = False
        self.on_change = None
        self.on_zoom = None
        self._drag: tuple[str, QPoint, tuple[int, int, int, int] | QPoint] | None = None
        self._placeholder = STRINGS["zh"]["placeholder"]
        self._cached_dest: QRect | None = None
        self.zoom = 1.0
        self._pan = QPoint(0, 0)

    def set_image(self, image: Image.Image, box: tuple[int, int, int, int] | None, enabled: bool) -> None:
        self.set_page(image, image, box, enabled, 0.0)

    def set_page(
        self,
        display: Image.Image,
        original: Image.Image | None,
        box: tuple[int, int, int, int] | None,
        enabled: bool,
        rotate_deg: float = 0.0,
        full_size: tuple[int, int] | None = None,
    ) -> None:
        self.full_size = full_size or display.size
        self.pixmap = pil_to_pixmap(downscale_preview(display))
        source = original if original is not None else display
        self.original_pixmap = pil_to_pixmap(downscale_preview(source))
        width, height = self.full_size
        self.crop = box or (0, 0, width, height)
        self.enabled = enabled and box is not None
        self.rotate_deg = float(rotate_deg or 0.0)
        self.live_angle = self.rotate_deg
        self._rotating = False
        self._cached_dest = None
        self.update()

    def reset_view(self) -> None:
        self.zoom = 1.0
        self._pan = QPoint(0, 0)
        self._cached_dest = None
        self._notify_zoom()
        self.update()

    def set_zoom(self, zoom: float, anchor: QPoint | None = None) -> None:
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, float(zoom)))
        if abs(zoom - self.zoom) < 1e-6:
            return
        dest = self._layout_rect()
        if dest.isNull():
            self.zoom = zoom
            self._cached_dest = None
            self._notify_zoom()
            self.update()
            return
        if anchor is None:
            anchor = dest.center()
        old_scale = self.scale
        if old_scale <= 0:
            self.zoom = zoom
            self._cached_dest = None
            self._notify_zoom()
            self.update()
            return
        img_x = (anchor.x() - self.origin.x()) / old_scale
        img_y = (anchor.y() - self.origin.y()) / old_scale
        self.zoom = zoom
        self._cached_dest = None
        dest = self._layout_rect()
        if self.scale > 0:
            new_x = dest.x() + img_x * self.scale
            new_y = dest.y() + img_y * self.scale
            self._pan += QPoint(int(round(anchor.x() - new_x)), int(round(anchor.y() - new_y)))
            self._cached_dest = None
        self._notify_zoom()
        self.update()

    def zoom_by(self, factor: float, anchor: QPoint | None = None) -> None:
        self.set_zoom(self.zoom * factor, anchor)

    def zoom_in(self) -> None:
        self.zoom_by(ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom_by(1.0 / ZOOM_STEP)

    def _notify_zoom(self) -> None:
        if self.on_zoom is not None:
            self.on_zoom(self.zoom)

    def set_crop(self, box: tuple[int, int, int, int]) -> None:
        width, height = self.full_size
        self.crop = crop.clamp_crop(box, width, height)
        self.update()

    def set_live_angle(self, angle: float) -> None:
        self.live_angle = clamp_angle(angle)
        self._rotating = abs(self.live_angle - self.rotate_deg) > 1e-3
        self.update()

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        self.update()

    def clear(self) -> None:
        self.pixmap = None
        self.original_pixmap = None
        self.enabled = False
        self._rotating = False
        self._cached_dest = None
        self.zoom = 1.0
        self._pan = QPoint(0, 0)
        self.update()

    def _layout_rect(self) -> QRect:
        if self._cached_dest is not None and self._drag is None and not self._rotating:
            return self._cached_dest
        pix = self.original_pixmap if self._rotating and self.original_pixmap is not None else self.pixmap
        if pix is None:
            return QRect()
        margin = 16
        avail = self.rect().adjusted(margin, margin, -margin, -margin)
        iw, ih = self.full_size
        if self._rotating and self.original_pixmap is not None:
            iw, ih = self.original_pixmap.width(), self.original_pixmap.height()
        fit = min(avail.width() / max(iw, 1), avail.height() / max(ih, 1))
        self.scale = max(fit * self.zoom, 1e-6)
        dw = max(1, int(round(iw * self.scale)))
        dh = max(1, int(round(ih * self.scale)))
        x = avail.x() + (avail.width() - dw) // 2 + self._pan.x()
        y = avail.y() + (avail.height() - dh) // 2 + self._pan.y()
        self.origin = QPoint(x, y)
        dest = QRect(x, y, dw, dh)
        if self._drag is None:
            self._cached_dest = dest
        return dest

    def _screen_rect(self) -> QRect:
        left, top, right, bottom = self.crop
        return QRect(
            int(round(self.origin.x() + left * self.scale)),
            int(round(self.origin.y() + top * self.scale)),
            max(1, int(round((right - left) * self.scale))),
            max(1, int(round((bottom - top) * self.scale))),
        )

    def _handles(self) -> list[tuple[str, QPoint]]:
        rect = self._screen_rect()
        return [
            ("nw", rect.topLeft()),
            ("n", QPoint(rect.center().x(), rect.top())),
            ("ne", rect.topRight()),
            ("e", QPoint(rect.right(), rect.center().y())),
            ("se", rect.bottomRight()),
            ("s", QPoint(rect.center().x(), rect.bottom())),
            ("sw", rect.bottomLeft()),
            ("w", QPoint(rect.left(), rect.center().y())),
        ]

    def _hit(self, pos: QPoint) -> str | None:
        dest = self._layout_rect()
        if dest.isNull() or not self.enabled or self._rotating:
            return None
        for name, point in self._handles():
            if abs(pos.x() - point.x()) <= HANDLE + 2 and abs(pos.y() - point.y()) <= HANDLE + 2:
                return name
        if self._screen_rect().contains(pos):
            return "move"
        return None

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if self._drag is None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#0F172A"))
        if self.pixmap is None:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
            return
        dest = self._layout_rect()
        if self._rotating and self.original_pixmap is not None:
            painter.save()
            painter.translate(dest.center())
            painter.rotate(-self.live_angle)
            painter.translate(-dest.center())
            painter.drawPixmap(dest, self.original_pixmap)
            painter.restore()
        else:
            painter.drawPixmap(dest, self.pixmap)
            if self.enabled:
                self._draw_crop_overlay(painter, dest)

    def _draw_crop_overlay(self, painter: QPainter, page: QRect) -> None:
        crop_rect = self._screen_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(2, 6, 23, 120))
        painter.drawRect(QRect(page.left(), page.top(), page.width(), max(0, crop_rect.top() - page.top())))
        painter.drawRect(QRect(page.left(), crop_rect.bottom() + 1, page.width(), max(0, page.bottom() - crop_rect.bottom())))
        painter.drawRect(QRect(page.left(), crop_rect.top(), max(0, crop_rect.left() - page.left()), crop_rect.height()))
        painter.drawRect(
            QRect(crop_rect.right() + 1, crop_rect.top(), max(0, page.right() - crop_rect.right()), crop_rect.height())
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#38BDF8"), 2))
        painter.drawRect(crop_rect)
        painter.setBrush(QColor("#0EA5E9"))
        painter.setPen(QPen(QColor("#E0F2FE"), 1))
        for _name, point in self._handles():
            painter.drawRect(QRect(point.x() - HANDLE, point.y() - HANDLE, HANDLE * 2, HANDLE * 2))

    def mousePressEvent(self, event) -> None:
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            return
        pos = event.position().toPoint()
        kind = self._hit(pos)
        if event.button() == Qt.MouseButton.MiddleButton or not kind:
            if self.pixmap is None:
                return
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._drag = ("pan", pos, self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._drag = (kind, pos, self.crop)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position().toPoint()
        if self._drag is None:
            cursors = {
                "nw": Qt.CursorShape.SizeFDiagCursor,
                "se": Qt.CursorShape.SizeFDiagCursor,
                "ne": Qt.CursorShape.SizeBDiagCursor,
                "sw": Qt.CursorShape.SizeBDiagCursor,
                "n": Qt.CursorShape.SizeVerCursor,
                "s": Qt.CursorShape.SizeVerCursor,
                "e": Qt.CursorShape.SizeHorCursor,
                "w": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.SizeAllCursor,
            }
            hit = self._hit(pos)
            if hit:
                self.setCursor(cursors.get(hit, Qt.CursorShape.ArrowCursor))
            elif self.pixmap is not None:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        kind, start_pos, start_value = self._drag
        if kind == "pan":
            start_pan = start_value
            self._pan = QPoint(
                start_pan.x() + pos.x() - start_pos.x(),
                start_pan.y() + pos.y() - start_pos.y(),
            )
            self._cached_dest = None
            self.update()
            return
        if self.scale <= 0:
            return
        dx = (pos.x() - start_pos.x()) / self.scale
        dy = (pos.y() - start_pos.y()) / self.scale
        left, top, right, bottom = start_value
        width, height = self.full_size
        if kind == "move":
            shift_x, shift_y = dx, dy
            if left + shift_x < 0:
                shift_x = -left
            if top + shift_y < 0:
                shift_y = -top
            if right + shift_x > width:
                shift_x = width - right
            if bottom + shift_y > height:
                shift_y = height - bottom
            left += shift_x
            right += shift_x
            top += shift_y
            bottom += shift_y
        else:
            if "w" in kind:
                left += dx
            if "e" in kind:
                right += dx
            if "n" in kind:
                top += dy
            if "s" in kind:
                bottom += dy
        self.crop = crop.clamp_crop((int(round(left)), int(round(top)), int(round(right)), int(round(bottom))), width, height)
        self.update()

    def mouseReleaseEvent(self, _event) -> None:
        if self._drag is None:
            return
        kind = self._drag[0]
        self._drag = None
        self._cached_dest = None
        if kind == "pan":
            self.update()
            return
        if self.on_change is not None:
            self.on_change(self.crop)

    def wheelEvent(self, event) -> None:
        if self.pixmap is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = ZOOM_STEP if delta > 0 else 1.0 / ZOOM_STEP
        self.zoom_by(factor, event.position().toPoint())
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._cached_dest = None
        self.update()


class ResultsTable(QTableWidget):
    """The page-results table, with drag-to-reorder rows."""

    def __init__(self, reorder_handler, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reorder_handler = reorder_handler
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event) -> None:
        if event.source() is not self or self._reorder_handler is None:
            event.ignore()
            return
        pos = event.position().toPoint()
        target = self.rowAt(pos.y())
        if target < 0:
            target = self.rowCount()
        rows = sorted({index.row() for index in self.selectionModel().selectedRows()})
        if not rows:
            event.ignore()
            return
        event.acceptProposedAction()
        event.setDropAction(Qt.DropAction.IgnoreAction)
        # Same reason as PageGrid: never rebuild the table inside dropEvent.
        handler = self._reorder_handler
        QTimer.singleShot(0, lambda: self._deferred_reorder(handler, rows, target))

    @staticmethod
    def _deferred_reorder(handler, rows: list[int], target: int) -> None:
        try:
            handler(rows, target)
        except RuntimeError:
            pass  # the window is gone


class UniformCropDialog(QDialog):
    """Book-wide uniform margins, cropped from each original page edge."""

    # Centimetres per one displayed unit.
    FACTORS = {"cm": 1.0, "mm": 0.1, "in": 2.54}
    STEPS = {"cm": 0.1, "mm": 1.0, "in": 0.1}

    def __init__(
        self,
        parent: QWidget,
        current: tuple[float, float, float, float] | None,
        unit: str,
        tr,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self._cm: tuple[float, float, float, float] = tuple(
            float(value) for value in (current or (0.0, 0.0, 0.0, 0.0))
        )
        self._generate = False
        self.setWindowTitle(tr("uniform_title"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("uniform_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.spins: list[QDoubleSpinBox] = []
        for key in ("left", "top", "right", "bottom"):
            column = QVBoxLayout()
            column.setSpacing(2)
            label = QLabel(tr(key))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 30.0)
            spin.setDecimals(2)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(label)
            column.addWidget(spin)
            row.addLayout(column)
            self.spins.append(spin)
        self.unit_combo = QComboBox()
        for unit_key in ("cm", "mm", "in"):
            self.unit_combo.addItem(tr(f"unit_{unit_key}"), unit_key)
        for index in range(self.unit_combo.count()):
            if self.unit_combo.itemData(index) == unit:
                self.unit_combo.setCurrentIndex(index)
                break
        self._shown_unit = self.unit_combo.currentData() or "cm"
        self.unit_combo.currentIndexChanged.connect(self._unit_changed)
        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel(tr("uniform_unit")))
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch(1)
        layout.addLayout(row)
        layout.addLayout(unit_row)
        hint = QLabel(tr("uniform_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept_values)
        buttons.rejected.connect(self.reject)
        self.generate_btn = QPushButton(tr("uniform_generate"))
        self.generate_btn.clicked.connect(self.accept_generate)
        actions = QHBoxLayout()
        actions.addWidget(self.generate_btn)
        actions.addStretch(1)
        actions.addWidget(buttons)
        layout.addLayout(actions)
        self._sync_suffixes()
        self._show_values(self._cm)

    def _unit(self) -> str:
        return self.unit_combo.currentData() or "cm"

    def _unit_changed(self, _index: int) -> None:
        new_unit = self._unit()
        factor = self.FACTORS[self._shown_unit] / self.FACTORS[new_unit]
        self._shown_unit = new_unit
        # Widen first: neither a growing nor a shrinking unit may clamp mid-conversion.
        for spin in self.spins:
            spin.setRange(0.0, 3000.0)
        for spin in self.spins:
            spin.setValue(round(spin.value() * factor, 2))
        self._sync_suffixes()

    def _sync_suffixes(self) -> None:
        unit = self._unit()
        top = round(30.0 / self.FACTORS[unit], 2)
        for spin in self.spins:
            spin.setSuffix(f" {unit}")
            spin.setRange(0.0, top)
            spin.setSingleStep(self.STEPS[unit])

    def _show_values(self, values_cm: tuple[float, float, float, float]) -> None:
        factor = self.FACTORS[self._unit()]
        for spin, value in zip(self.spins, values_cm):
            spin.setValue(round(value / factor, 2))

    def _values_cm(self) -> tuple[float, float, float, float]:
        factor = self.FACTORS[self._unit()]
        values = tuple(max(0.0, spin.value()) * factor for spin in self.spins)
        return values  # type: ignore[return-value]

    def accept_values(self) -> None:
        self._cm = self._values_cm()
        self.accept()

    def accept_generate(self) -> None:
        self._cm = self._values_cm()
        self._generate = True
        self.accept()

    def margin_cm(self) -> tuple[float, float, float, float]:
        return self._cm

    def wants_generate(self) -> bool:
        return self._generate

    def selected_unit(self) -> str:
        return self._unit()


class PageGrid(QListWidget):
    """Thumbnail grid with reliable drag reordering (multi-selection aware)."""

    moved = Signal()
    ZOOM_MIN = 56
    ZOOM_MAX = 260
    ZOOM_STEP = 14
    DEFAULT_THUMB = 132

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._thumb_side = self.DEFAULT_THUMB
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setSpacing(2)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self._apply_thumb_size()

    def selected_rows(self) -> list[int]:
        return sorted({self.row(item) for item in self.selectedItems()})

    def _apply_thumb_size(self) -> None:
        side = self._thumb_side
        self.setIconSize(QSize(side, int(side * 4 / 3)))
        cell = int(side * 1.18)
        self.setGridSize(QSize(cell, int(cell * 4 / 3)))

    def zoom_by(self, step: int) -> None:
        side = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self._thumb_side + step))
        if side == self._thumb_side:
            return
        self._thumb_side = side
        self._apply_thumb_size()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_by(self.ZOOM_STEP if delta > 0 else -self.ZOOM_STEP)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_by(self.ZOOM_STEP)
                return
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_by(-self.ZOOM_STEP)
                return
            if key == Qt.Key.Key_0:
                self._thumb_side = self.DEFAULT_THUMB
                self._apply_thumb_size()
                return
        super().keyPressEvent(event)

    def move_rows(self, rows: list[int], target: int) -> None:
        """Move the given rows together so the block starts at target row."""
        rows = [row for row in sorted(set(rows)) if 0 <= row < self.count()]
        if not rows:
            return
        target = max(0, min(self.count(), target))
        before = sum(1 for row in rows if row < target)
        insert_at = target - before
        if before == len(rows) and insert_at == rows[0]:
            return  # dropping onto itself changes nothing
        items = []
        for row in reversed(rows):
            item = self.takeItem(row)
            if item is not None:
                items.append(item)
        items.reverse()
        if not items:
            return
        for offset, item in enumerate(items):
            self.insertItem(insert_at + offset, item)
        self.clearSelection()
        for offset in range(len(items)):
            self.item(insert_at + offset).setSelected(True)
        self.setCurrentRow(insert_at)
        self.scrollToItem(self.item(insert_at), QAbstractItemView.ScrollHint.EnsureVisible)
        self.moved.emit()

    def move_to_position(self, rows: list[int], dest: int) -> None:
        """Move rows so the block starts exactly at 0-based dest."""
        rows = [row for row in sorted(set(rows)) if 0 <= row < self.count()]
        if not rows:
            return
        dest = max(0, min(self.count() - len(rows), dest))
        offset = sum(1 for row in rows if row < dest)
        self.move_rows(rows, dest + offset)

    def row_near(self, pos: QPoint) -> int:
        """Row under the pointer, falling back to the nearest cell (gaps included)."""
        index = self.indexAt(pos)
        if index.isValid():
            return index.row()
        best, best_dist = -1, None
        for row in range(self.count()):
            rect = self.visualRect(self.model().index(row, 0))
            if rect.width() <= 0 and rect.height() <= 0:
                continue
            dx = max(rect.left() - pos.x(), 0, pos.x() - (rect.right() + 1))
            dy = max(rect.top() - pos.y(), 0, pos.y() - (rect.bottom() + 1))
            dist = dx * dx + dy * dy
            if best_dist is None or dist < best_dist:
                best, best_dist = row, dist
        return best

    def dropEvent(self, event) -> None:
        if event.source() is not self:
            event.ignore()
            return
        rows = self.selected_rows()
        if not rows:
            event.ignore()
            return
        pos = event.position().toPoint()
        row = self.row_near(pos)
        if row >= 0:
            rect = self.visualRect(self.model().index(row, 0))
            target = row
            # Dropping past the middle of a thumbnail means "after this page".
            if rect.width() > 0 and pos.x() > rect.center().x():
                target += 1
        else:
            target = self.count()
        event.accept()
        # Never report MoveAction: QAbstractItemView::startDrag() answers a Move
        # result by clearing the dragged rows itself, which made pages vanish on
        # every drag. We move the rows ourselves a moment later.
        event.setDropAction(Qt.DropAction.IgnoreAction)
        # Reordering inside dropEvent rebuilds items while Qt is still handling
        # the drag, which can crash. Let the drag finish first.
        QTimer.singleShot(0, lambda: self._deferred_move(rows, target))

    def _deferred_move(self, rows: list[int], target: int) -> None:
        try:
            self.move_rows(rows, target)
        except RuntimeError:
            pass  # the dialog was closed before the timer fired


class PageOrganizeDialog(QDialog):
    """Reorder, delete, restore and insert pages; returns the arrangement on accept."""

    def __init__(
        self,
        parent: QWidget,
        entries: list[tuple[int, str]],
        deleted: list[tuple[int, str]],
        tr,
        thumbs: dict[int, QPixmap] | None = None,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self._thumbs = thumbs or {}
        self._requests: list[dict] = []
        self._dropped: list[int] = []
        self.setWindowTitle(tr("organize_title"))
        self.resize(1080, 760)
        layout = QVBoxLayout(self)
        hint = QLabel(tr("organize_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.list = PageGrid()
        self.list._apply_thumb_size()
        for key, note in entries:
            self.list.addItem(self._make_item(key, note))
        self.list.model().rowsInserted.connect(lambda *args: QTimer.singleShot(0, self._renumber))
        self.list.model().rowsRemoved.connect(lambda *args: QTimer.singleShot(0, self._renumber))
        self.list.moved.connect(self._renumber)
        layout.addWidget(self.list, 1)
        row1 = QHBoxLayout()
        for text, handler in (
            (tr("org_move_up"), self._move_up),
            (tr("org_move_down"), self._move_down),
            (tr("org_delete"), self._delete_selected),
            (tr("org_restore"), self._restore_selected),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row1.addWidget(button)
        row1.addSpacing(12)
        row1.addWidget(QLabel(tr("org_move_to")))
        self.move_to_spin = QSpinBox()
        self.move_to_spin.setRange(1, max(1, self.list.count()))
        self.move_to_spin.setMinimumWidth(70)
        row1.addWidget(self.move_to_spin)
        self.move_to_btn = QPushButton(tr("org_move_apply"))
        self.move_to_btn.clicked.connect(self._move_to)
        row1.addWidget(self.move_to_btn)
        self.fullscreen_btn = QPushButton(tr("organize_fullscreen"))
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        row1.addStretch(1)
        row1.addWidget(self.fullscreen_btn)
        layout.addLayout(row1)
        row2 = QHBoxLayout()
        for text, handler in (
            (tr("org_insert_pdf"), self._insert_pdf),
            (tr("org_insert_image"), self._insert_image),
            (tr("org_insert_blank"), self._insert_blank),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row2.addWidget(button)
        layout.addLayout(row2)
        row3 = QHBoxLayout()
        for text, handler in (
            (tr("org_duplicate"), self._duplicate),
            (tr("org_reset"), self._reset_order),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row3.addWidget(button)
        row3.addStretch(1)
        layout.addLayout(row3)
        self.deleted_label = QLabel(tr("organize_deleted_label"))
        self.deleted_list = PageGrid()
        self.deleted_list._thumb_side = 64
        self.deleted_list._apply_thumb_size()
        self.deleted_list.setDragEnabled(False)
        self.deleted_list.setAcceptDrops(False)
        self.deleted_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.deleted_list.setMaximumHeight(140)
        has_deleted = bool(deleted)
        self.deleted_label.setVisible(has_deleted)
        self.deleted_list.setVisible(has_deleted)
        for key, note in deleted:
            self.deleted_list.addItem(self._make_item(key, note, deleted=True))
        self.deleted_list.model().rowsInserted.connect(lambda *args: QTimer.singleShot(0, self._renumber))
        self.deleted_list.model().rowsRemoved.connect(lambda *args: QTimer.singleShot(0, self._renumber))
        self._renumber()
        layout.addWidget(self.deleted_label)
        layout.addWidget(self.deleted_list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _make_grid(view: QListWidget, icon_size: QSize, cell_size: QSize) -> None:
        """Thumbnail grid: several pages per row, wrapping, drag to reorder."""
        view.setViewMode(QListView.ViewMode.IconMode)
        view.setFlow(QListView.Flow.LeftToRight)
        view.setWrapping(True)
        view.setResizeMode(QListView.ResizeMode.Adjust)
        view.setMovement(QListView.Movement.Static)
        view.setUniformItemSizes(True)
        view.setWordWrap(True)
        view.setIconSize(icon_size)
        view.setGridSize(cell_size)
        view.setSpacing(2)
        view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def _make_item(self, key: int, note: str = "", deleted: bool = False) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, int(key))
        item.setData(Qt.ItemDataRole.UserRole + 1, note)
        icon = self._thumbs.get(key)
        if icon is not None:
            item.setIcon(QIcon(icon))
        return item

    def _renumber(self) -> None:
        """Page numbers follow the current arrangement, exactly like the output PDF."""
        for row in range(self.list.count()):
            item = self.list.item(row)
            note = item.data(Qt.ItemDataRole.UserRole + 1) or ""
            text = self._tr("page_label", page=row + 1)
            item.setText(f"{text} · {note}" if note else text)
        if hasattr(self, "move_to_spin"):
            self.move_to_spin.setRange(1, max(1, self.list.count()))
        for row in range(self.deleted_list.count()):
            item = self.deleted_list.item(row)
            key = int(item.data(Qt.ItemDataRole.UserRole))
            note = item.data(Qt.ItemDataRole.UserRole + 1) or ""
            text = self._tr("page_label_orig", page=key)
            item.setText(f"{text} · {note}" if note else text)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText(self._tr("organize_fullscreen"))
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText(self._tr("organize_windowed"))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
            return
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self._toggle_fullscreen()
            return
        super().keyPressEvent(event)

    def _insert_index(self) -> int:
        row = self.list.currentRow()
        return row + 1 if row >= 0 else self.list.count()

    def _move_to(self) -> None:
        """Send the selection (or the current page) straight to a page number."""
        rows = self.list.selected_rows()
        if not rows:
            row = self.list.currentRow()
            if row < 0:
                return
            rows = [row]
        self.list.move_to_position(rows, self.move_to_spin.value() - 1)
        self._renumber()

    def _move_up(self) -> None:
        rows = self.list.selected_rows() or ([self.list.currentRow()] if self.list.currentRow() >= 0 else [])
        if not rows or rows[0] <= 0:
            return
        self.list.move_rows(rows, rows[0] - 1)
        self._renumber()

    def _move_down(self) -> None:
        rows = self.list.selected_rows() or ([self.list.currentRow()] if self.list.currentRow() >= 0 else [])
        if not rows or rows[-1] >= self.list.count() - 1:
            return
        self.list.move_rows(rows, rows[-1] + 2)
        self._renumber()

    def _delete_selected(self) -> None:
        for item in list(self.list.selectedItems()):
            key = int(item.data(Qt.ItemDataRole.UserRole))
            self.list.takeItem(self.list.row(item))
            if key < crop.IMPORT_PAGE_BASE:
                self.deleted_list.addItem(item)
                self.deleted_label.setVisible(True)
                self.deleted_list.setVisible(True)
            else:
                # Inserted pages cannot be restored, so deleting one removes it
                # for good - record the intent explicitly.
                self._dropped.append(key)
        self._renumber()

    def _restore_selected(self) -> None:
        for item in list(self.deleted_list.selectedItems()):
            self.deleted_list.takeItem(self.deleted_list.row(item))
            self.list.addItem(item)
        if self.deleted_list.count() == 0:
            self.deleted_label.setVisible(False)
            self.deleted_list.setVisible(False)
        self._renumber()

    def _reset_order(self) -> None:
        keys = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        keys += [self.deleted_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.deleted_list.count())]
        notes = {int(self.list.item(i).data(Qt.ItemDataRole.UserRole)): self.list.item(i).data(Qt.ItemDataRole.UserRole + 1) for i in range(self.list.count())}
        notes.update({int(self.deleted_list.item(i).data(Qt.ItemDataRole.UserRole)): self.deleted_list.item(i).data(Qt.ItemDataRole.UserRole + 1) for i in range(self.deleted_list.count())})
        for key in sorted(keys):
            self.list.addItem(self._make_item(key, notes.get(key) or ""))
        while self.list.count() > len(keys):
            self.list.takeItem(0)
        self.deleted_list.clear()
        self.deleted_label.setVisible(False)
        self.deleted_list.setVisible(False)
        self._renumber()

    def _label_for(self, key: int) -> str:
        for row in range(self.list.count()):
            item = self.list.item(row)
            if int(item.data(Qt.ItemDataRole.UserRole)) == key:
                return item.text()
        for row in range(self.deleted_list.count()):
            item = self.deleted_list.item(row)
            if int(item.data(Qt.ItemDataRole.UserRole)) == key:
                return item.text()
        return str(key)

    def _insert_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._tr("ins_pdf_title"), "", self._tr("pdf_filter"))
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            thumbs = pdf_page_thumbs(Path(path))
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, self._tr("organize_title"), str(exc))
            return
        QApplication.restoreOverrideCursor()
        if not thumbs:
            return
        picker = PageSelectDialog(
            self,
            sorted(thumbs),
            set(),
            self._tr,
            thumbs,
            title=self._tr("ins_select_title"),
            hint=self._tr("ins_select_hint"),
            spec_field=True,
        )
        if picker.exec() != QDialog.DialogCode.Accepted:
            return
        pages = picker.selected_positions()
        if not pages:
            return
        self._requests.append({"type": "pdf", "path": path, "pages": pages, "index": self._insert_index()})

    def _insert_image(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, self._tr("ins_image_title"), "", self._tr("ins_image_filter"))
        if not files:
            return
        box = QMessageBox(self)
        box.setWindowTitle(self._tr("ins_enhance_title"))
        box.setText(self._tr("ins_enhance_q"))
        check = QCheckBox(self._tr("ins_enhance_check"))
        check.setChecked(True)
        box.setCheckBox(check)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        enhanced = box.exec() == QMessageBox.StandardButton.Yes and check.isChecked()
        self._requests.append({"type": "image", "files": list(files), "enhanced": enhanced, "index": self._insert_index()})

    def _insert_blank(self) -> None:
        self._requests.append({"type": "blank", "index": self._insert_index()})

    def _duplicate(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        key = int(self.list.item(row).data(Qt.ItemDataRole.UserRole))
        self._requests.append({"type": "dup", "key": key, "index": row + 1})

    def result(self) -> tuple[list[int], list[int], list[dict], list[int]]:
        order = [int(self.list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.list.count())]
        deleted = [int(self.deleted_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.deleted_list.count())]
        return order, deleted, self._requests, list(self._dropped)


class PageSelectDialog(QDialog):
    """Tick thumbnails to choose which pages the export keeps."""

    def __init__(
        self,
        parent: QWidget,
        keys: list[int],
        selected: set[int],
        tr,
        thumbs: dict[int, QPixmap] | None = None,
        title: str | None = None,
        hint: str | None = None,
        spec_field: bool = False,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self._thumbs = thumbs or {}
        self.setWindowTitle(title or tr("select_pages_title"))
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        hint = QLabel(hint or tr("select_pages_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.spec_edit = None
        if spec_field:
            spec_row = QHBoxLayout()
            spec_row.addWidget(QLabel(tr("ins_pages_label")))
            self.spec_edit = QLineEdit()
            spec_row.addWidget(self.spec_edit, 1)
            apply_btn = QPushButton(tr("select_spec_apply"))
            apply_btn.clicked.connect(self._apply_spec)
            spec_row.addWidget(apply_btn)
            self.spec_edit.returnPressed.connect(self._apply_spec)
            layout.addLayout(spec_row)
        self.list = PageGrid()
        self.list.setDragEnabled(False)
        self.list.setAcceptDrops(False)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.list._apply_thumb_size()
        for position, key in enumerate(keys, start=1):
            item = QListWidgetItem(tr("page_label", page=position))
            item.setData(Qt.ItemDataRole.UserRole, position)
            icon = self._thumbs.get(key)
            if icon is not None:
                item.setIcon(QIcon(icon))
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked if position in selected else Qt.CheckState.Unchecked
            )
            self.list.addItem(item)
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, handler in (
            (tr("select_all"), lambda: self._set_all(Qt.CheckState.Checked)),
            (tr("select_none"), lambda: self._set_all(Qt.CheckState.Unchecked)),
            (tr("select_invert"), self._invert),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row.addWidget(button)
        self.count_label = QLabel()
        row.addStretch(1)
        row.addWidget(self.count_label)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.list.itemChanged.connect(self._update_count)
        self._update_count()

    def _apply_spec(self) -> None:
        if self.spec_edit is None:
            return
        text = self.spec_edit.text().strip()
        try:
            pages = crop.parse_page_spec(text)
        except ValueError as exc:
            QMessageBox.warning(self, self._tr("select_pages_title"), str(exc))
            return
        wanted = set(pages)
        for row in range(self.list.count()):
            item = self.list.item(row)
            position = int(item.data(Qt.ItemDataRole.UserRole))
            item.setCheckState(
                Qt.CheckState.Checked if position in wanted else Qt.CheckState.Unchecked
            )
        self._update_count()

    def _set_all(self, state) -> None:
        for row in range(self.list.count()):
            self.list.item(row).setCheckState(state)

    def _invert(self) -> None:
        for row in range(self.list.count()):
            item = self.list.item(row)
            checked = item.checkState() == Qt.CheckState.Checked
            item.setCheckState(Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)

    def _update_count(self, *_args) -> None:
        self.count_label.setText(self._tr("select_pages_count", n=len(self.selected_positions())))

    def selected_positions(self) -> list[int]:
        return sorted(
            int(self.list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.list.count())
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        )


class PdfCropWindow(QMainWindow):
    SETTING_BOXES = ("reuse_box", "open_after_box", "tight_box", "auto_rotate_box", "ocr_box", "ocr_txt_box")

    def __init__(self) -> None:
        super().__init__()
        self.lang = load_ui_lang()
        self.setWindowTitle(self.t("app_title"))
        self.resize(1280, 860)
        self.setMinimumSize(720, 480)
        self._left_compact = False
        self._fs_active = False
        self._normal_geom = None
        self.setAcceptDrops(True)
        self.events: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.worker: threading.Thread | None = None
        self.busy = False
        self.plans: dict[int, crop.PagePlan] = {}
        self.page_list: list[int] = []
        self.current_page = 1
        self.pdf_pages = 0
        self.src: Path | None = None
        self.last_output: Path | None = None
        self._updating = False
        self._rotate_busy = False
        self._rotate_pending: float | None = None
        self._preview_cache: dict[str, QPixmap] = {}
        self._stored_crops: dict[int, tuple[int, int, int, int]] = {}
        self._stored_rotates: dict[int, float] = {}
        self._uniform: tuple[float, float, float, float] | None = None
        self._uniform_base: dict[int, tuple[tuple[int, int, int, int], str]] = {}
        self._uniform_unit = "cm"
        self._page_order: list[int] | None = None
        self._deleted: set[int] = set()
        self._imports: dict[int, dict] = {}
        self._import_counter = 0
        self._pending_requests: list[dict] = []
        self._thumb_cache: dict[tuple[int, str], QPixmap] = {}
        self._last_dir = ""
        self._ocr_ok = crop.ocr_available()
        self._build_ui()
        self._load_settings()
        self.apply_language()
        if not self._ocr_ok:
            self.ocr_box.setChecked(False)
            self.ocr_box.setEnabled(False)
            self.ocr_txt_box.setEnabled(False)
            self.ocr_page_btn.setEnabled(False)
            self.ocr_book_btn.setEnabled(False)
            self.ocr_box.setToolTip(self._ocr_missing())
        QGuiApplication.instance().installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._drain_events)
        self.timer.start(80)

    def _setting_values(self) -> tuple[tuple[str, object], ...]:
        return (
            ("jobs", self.jobs_spin),
            ("dpi", self.dpi_spin),
            ("min_full", self.min_full[1]),
            ("min_page", self.min_page[1]),
        )

    def _load_settings(self) -> None:
        settings = app_settings()
        for name in self.SETTING_BOXES:
            if settings.contains(name):
                box = getattr(self, name)
                box.setChecked(settings.value(name, box.isChecked(), type=bool))
        for key, widget in self._setting_values():
            if settings.contains(key):
                widget.setValue(settings.value(key, widget.value(), type=int))
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self._last_dir = str(settings.value("last_dir", "") or "")

    def _save_settings(self) -> None:
        settings = app_settings()
        for name in self.SETTING_BOXES:
            settings.setValue(name, getattr(self, name).isChecked())
        for key, widget in self._setting_values():
            settings.setValue(key, widget.value())
        geometry = self._normal_geom if self._fs_active and self._normal_geom is not None else self.saveGeometry()
        settings.setValue("geometry", geometry)
        settings.setValue("last_dir", self._last_dir)
        settings.sync()

    def t(self, key: str, **kwargs: object) -> str:
        table = STRINGS.get(self.lang) or STRINGS["zh"]
        text = table.get(key) or STRINGS["zh"].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def _ocr_missing(self) -> str:
        reason = crop.ocr_missing_reason()
        if not reason:
            return ""
        if "Tesseract" in reason and "字库" not in reason:
            return self.t("no_tess")
        if "字库" in reason or "traineddata" in reason.lower():
            return self.t("no_tessdata")
        return reason if self.lang == "zh" else reason

    def _on_lang_changed(self, index: int) -> None:
        lang = "en" if index == 1 else "zh"
        if lang == self.lang:
            return
        self.lang = lang
        save_ui_lang(lang)
        install_qt_translator(QApplication.instance(), lang)
        self.apply_language()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setStyleSheet("background-color: #0B1F33; color: #FFFFFF;")
        header_l = QVBoxLayout(self.header)
        header_l.setContentsMargins(18, 12, 18, 12)
        title_row = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("title")
        self.title_label.setStyleSheet("background-color: #0B1F33; color: #FFFFFF; font-size: 20px; font-weight: 700;")
        self.lang_label = QLabel()
        self.lang_label.setStyleSheet("background-color: #0B1F33; color: #E2E8F0;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setFixedWidth(120)
        self.lang_combo.setCurrentIndex(1 if self.lang == "en" else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        title_row.addWidget(self.title_label, 1)
        title_row.addWidget(self.lang_label)
        title_row.addWidget(self.lang_combo)
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitle")
        self.subtitle_label.setStyleSheet("background-color: #0B1F33; color: #E2E8F0;")
        header_l.addLayout(title_row)
        header_l.addWidget(self.subtitle_label)
        outer.addWidget(self.header)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self.main_splitter, 1)
        self.left_panel = self._build_left()
        self.left_panel.setMinimumWidth(0)
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self._build_right())
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([380, 900])
        self.main_splitter.setCollapsible(0, True)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.splitterMoved.connect(self._on_main_split)

        self.footer = QFrame()
        self.footer.setObjectName("footer")
        foot = QVBoxLayout(self.footer)
        foot.setContentsMargins(12, 6, 12, 8)
        foot.setSpacing(4)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status = QLabel()
        foot.addWidget(self.progress)
        foot.addWidget(self.status)
        outer.addWidget(self.footer)

    def _build_left(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        self.file_section = self._section("")
        layout.addWidget(self.file_section)
        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.input_browse = QPushButton()
        self.output_browse = QPushButton()
        layout.addLayout(self._path_row(self.input_edit, self.input_browse, self.browse_input))
        layout.addLayout(self._path_row(self.output_edit, self.output_browse, self.browse_output))
        self.reuse_box = QCheckBox()
        self.reuse_box.setChecked(True)
        self.open_after_box = QCheckBox()
        self.open_after_box.setChecked(True)
        layout.addWidget(self.reuse_box)
        layout.addWidget(self.open_after_box)

        self.crop_section = self._section("")
        layout.addWidget(self.crop_section)
        self.tight_box = QCheckBox()
        self.tight_box.setChecked(False)
        self.auto_rotate_box = QCheckBox()
        self.auto_rotate_box.setChecked(True)
        self.ocr_box = QCheckBox()
        self.ocr_box.setChecked(False)
        self.ocr_txt_box = QCheckBox()
        self.ocr_txt_box.setChecked(False)
        self.ocr_box.toggled.connect(self.ocr_txt_box.setEnabled)
        self.ocr_txt_box.setEnabled(self.ocr_box.isChecked())
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.tight_box)
        layout.addWidget(self.auto_rotate_box)
        layout.addWidget(self.ocr_box)
        layout.addWidget(self.ocr_txt_box)
        layout.addWidget(self.hint_label)
        self.min_full = self._ratio_row(0.90)
        self.min_page = self._ratio_row(0.86)

        self.pages_section = self._section("")
        layout.addWidget(self.pages_section)
        self.pages_edit = QLineEdit()
        self.pages_edit.editingFinished.connect(self._pages_filter_changed)
        self.inspect_edit = QLineEdit()
        self.pages_only_label = QLabel()
        self.inspect_label = QLabel()
        layout.addWidget(self.pages_only_label)
        pages_row = QHBoxLayout()
        pages_row.setSpacing(4)
        pages_row.addWidget(self.pages_edit, 1)
        self.pick_pages_btn = QPushButton()
        self.pick_pages_btn.clicked.connect(self.open_pages_picker)
        pages_row.addWidget(self.pick_pages_btn)
        layout.addLayout(pages_row)
        layout.addWidget(self.inspect_label)
        layout.addWidget(self.inspect_edit)

        self.advanced = QGroupBox()
        self.advanced_form = QFormLayout(self.advanced)
        self.jobs_spin = QSpinBox()
        self.jobs_spin.setRange(1, 256)
        self.jobs_spin.setValue(crop.default_jobs())
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 2400)
        self.dpi_spin.setValue(crop.DEFAULT_RENDER_DPI)
        self.work_edit = QLineEdit()
        self.jobs_label = QLabel()
        self.dpi_label = QLabel()
        self.work_label = QLabel()
        self.advanced_form.addRow(self.jobs_label, self.jobs_spin)
        self.advanced_form.addRow(self.dpi_label, self.dpi_spin)
        self.advanced_form.addRow(self.work_label, self.work_edit)
        self.advanced_form.addRow(self.min_full[0])
        self.advanced_form.addRow(self.min_page[0])
        self.clear_cache_btn = QPushButton()
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        self.forget_edits_btn = QPushButton()
        self.forget_edits_btn.clicked.connect(self.forget_edits)
        maintenance = QHBoxLayout()
        maintenance.addWidget(self.clear_cache_btn)
        maintenance.addWidget(self.forget_edits_btn)
        self.advanced_form.addRow(maintenance)
        layout.addWidget(self.advanced)

        self.analyze_btn = QPushButton()
        self.analyze_btn.setObjectName("primary")
        self.generate_btn = QPushButton()
        self.ocr_page_btn = QPushButton()
        self.ocr_book_btn = QPushButton()
        self.cancel_btn = QPushButton()
        self.cancel_btn.setEnabled(False)
        self.open_btn = QPushButton()
        self.folder_btn = QPushButton()
        self.keep_all_btn = QPushButton()
        self.uniform_btn = QPushButton()
        self.organize_btn = QPushButton()
        self.rotate_all_ccw_btn = QPushButton()
        self.rotate_all_cw_btn = QPushButton()
        self.analyze_btn.clicked.connect(self.start_analyze)
        self.keep_all_btn.clicked.connect(self.keep_all_full)
        self.uniform_btn.clicked.connect(self.open_uniform_dialog)
        self.organize_btn.clicked.connect(self.open_organizer)
        self.rotate_all_ccw_btn.clicked.connect(lambda: self.rotate_all_pages(90.0))
        self.rotate_all_cw_btn.clicked.connect(lambda: self.rotate_all_pages(-90.0))
        self.generate_btn.clicked.connect(self.start_generate)
        self.ocr_page_btn.clicked.connect(self.ocr_current_page)
        self.ocr_book_btn.clicked.connect(self.start_ocr_book)
        self.cancel_btn.clicked.connect(self.request_cancel)
        self.open_btn.clicked.connect(self.open_output)
        self.folder_btn.clicked.connect(self.open_folder)
        layout.addWidget(self.analyze_btn)
        layout.addWidget(self.keep_all_btn)
        layout.addWidget(self.uniform_btn)
        layout.addWidget(self.organize_btn)
        rotate_all_row = QHBoxLayout()
        rotate_all_row.addWidget(self.rotate_all_ccw_btn)
        rotate_all_row.addWidget(self.rotate_all_cw_btn)
        layout.addLayout(rotate_all_row)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.ocr_page_btn)
        layout.addWidget(self.ocr_book_btn)
        layout.addWidget(self.cancel_btn)
        row = QHBoxLayout()
        row.addWidget(self.open_btn)
        row.addWidget(self.folder_btn)
        layout.addLayout(row)

        self.log_section = self._section("")
        layout.addWidget(self.log_section)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        layout.addWidget(self.log, 1)
        return panel

    def _build_right(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(4)
        self.nav_bar = QWidget()
        nav = QHBoxLayout(self.nav_bar)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(6)
        self.hide_left_btn = QPushButton()
        self.hide_left_btn.clicked.connect(self._toggle_left)
        self.prev_btn = QPushButton()
        self.next_btn = QPushButton()
        self.prev_btn.clicked.connect(lambda: self.step_page(-1))
        self.next_btn.clicked.connect(lambda: self.step_page(1))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.valueChanged.connect(self.goto_page)
        self.page_info = QLabel()
        self.zoom_out_btn = QPushButton()
        self.zoom_in_btn = QPushButton()
        self.zoom_fit_btn = QPushButton()
        self.zoom_label = QLabel("100%")
        self.fullscreen_btn = QPushButton()
        self.zoom_out_btn.clicked.connect(lambda: self.view.zoom_out())
        self.zoom_in_btn.clicked.connect(lambda: self.view.zoom_in())
        self.zoom_fit_btn.clicked.connect(lambda: self.view.reset_view())
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen_crop)
        self.reset_btn = QPushButton()
        self.reset_btn.clicked.connect(self.reset_current_auto)
        self.del_page_btn = QPushButton()
        self.del_page_btn.clicked.connect(self.delete_current_page)
        self.keep_page_btn = QPushButton()
        self.keep_page_btn.clicked.connect(self.keep_current_full)
        nav.addWidget(self.hide_left_btn)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.page_spin)
        nav.addWidget(self.page_info, 1)
        nav.addWidget(self.zoom_out_btn)
        nav.addWidget(self.zoom_label)
        nav.addWidget(self.zoom_in_btn)
        nav.addWidget(self.zoom_fit_btn)
        nav.addWidget(self.fullscreen_btn)
        nav.addWidget(self.keep_page_btn)
        nav.addWidget(self.reset_btn)
        nav.addWidget(self.del_page_btn)
        layout.addWidget(self.nav_bar)

        self.view = CropView()
        self.view.on_change = self._on_canvas_crop
        self.view.on_zoom = self._on_zoom_changed
        self.view.setMinimumHeight(80)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view_host = QWidget()
        view_host_l = QVBoxLayout(self.view_host)
        view_host_l.setContentsMargins(0, 0, 0, 0)
        view_host_l.setSpacing(0)
        view_host_l.addWidget(self.view)
        self.view_host.setMinimumHeight(80)
        self._build_fullscreen_overlay()
        self.rot_hint = QLabel()
        self.rot_hint.setWordWrap(True)

        self.crop_label = QLabel()
        self.note_label = QLabel("")

        coords = QHBoxLayout()
        self.left_spin = self._coord_spin()
        self.top_spin = self._coord_spin()
        self.right_spin = self._coord_spin()
        self.bottom_spin = self._coord_spin()
        self.rotate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotate_slider.setRange(-180, 180)
        self.rotate_slider.setValue(0)
        self.rotate_slider.setSingleStep(1)
        self.rotate_slider.setPageStep(15)
        self.rotate_slider.setMinimumWidth(220)
        self.rotate_spin = QDoubleSpinBox()
        self.rotate_spin.setRange(-ROTATE_LIMIT, ROTATE_LIMIT)
        self.rotate_spin.setSingleStep(0.1)
        self.rotate_spin.setDecimals(1)
        self.rotate_spin.setSuffix(" °")
        self.rotate_slider.valueChanged.connect(self._rotate_live_from_slider)
        self.rotate_slider.sliderReleased.connect(lambda: self._rotate_commit())
        self.rotate_spin.valueChanged.connect(self._rotate_live_from_spin)
        self.rotate_apply_btn = QPushButton()
        self.rotate_apply_btn.clicked.connect(lambda: self._rotate_commit())
        self._rotate_busy = False
        self._rotate_pending: float | None = None
        self.coord_labels: list[QLabel] = []
        for widget in (self.left_spin, self.top_spin, self.right_spin, self.bottom_spin):
            lab = QLabel()
            self.coord_labels.append(lab)
            coords.addWidget(lab)
            coords.addWidget(widget)
            widget.editingFinished.connect(self._coords_changed)
        self.page_ccw_btn = QPushButton()
        self.page_cw_btn = QPushButton()
        self.page_ccw_btn.clicked.connect(lambda: self._nudge_rotate(90.0))
        self.page_cw_btn.clicked.connect(lambda: self._nudge_rotate(-90.0))
        self.rotate_name_label = QLabel()
        coords.addWidget(self.page_ccw_btn)
        coords.addWidget(self.page_cw_btn)
        coords.addWidget(self.rotate_name_label)
        coords.addWidget(self.rotate_slider, 1)
        coords.addWidget(self.rotate_spin)
        coords.addWidget(self.rotate_apply_btn)

        below_wrap = QWidget()
        below_layout = QVBoxLayout(below_wrap)
        below_layout.setContentsMargins(0, 8, 0, 0)
        below_layout.setSpacing(6)
        below_layout.addWidget(self.rot_hint)
        below_layout.addWidget(self.crop_label)
        below_layout.addWidget(self.note_label)
        below_layout.addLayout(coords)

        self.results_section = self._section("")
        below_layout.addWidget(self.results_section)
        self.table = ResultsTable(self._on_table_reorder)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["", "", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_table_select)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context)
        self.table.setMinimumHeight(0)
        self.table.setMaximumHeight(220)
        below_layout.addWidget(self.table, 1)
        below_wrap.setMinimumHeight(0)
        below_wrap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        self.below_wrap = below_wrap

        self.preview_splitter = QSplitter(Qt.Orientation.Vertical)
        self.preview_splitter.setObjectName("previewSplit")
        self.preview_splitter.addWidget(self.view_host)
        self.preview_splitter.addWidget(below_wrap)
        self.preview_splitter.setStretchFactor(0, 8)
        self.preview_splitter.setStretchFactor(1, 1)
        self.preview_splitter.setSizes([820, 180])
        self.preview_splitter.setChildrenCollapsible(True)
        self.preview_splitter.setCollapsible(0, False)
        self.preview_splitter.setCollapsible(1, True)
        self.preview_splitter.setHandleWidth(14)
        handle = self.preview_splitter.handle(1)
        handle.setCursor(Qt.CursorShape.SizeVerCursor)
        handle.setMinimumHeight(14)
        self.preview_splitter.splitterMoved.connect(self._on_preview_split)
        layout.addWidget(self.preview_splitter, 1)
        return panel

    def _build_fullscreen_overlay(self) -> None:
        self.fs_bar = QWidget()
        self.fs_bar.setObjectName("fsBar")
        self.fs_bar.setVisible(False)
        bar = QHBoxLayout(self.fs_bar)
        bar.setContentsMargins(10, 6, 10, 6)
        bar.setSpacing(8)
        self.fs_exit_btn = QPushButton()
        self.fs_exit_btn.clicked.connect(self._exit_fullscreen_crop)
        self.fs_prev_btn = QPushButton()
        self.fs_next_btn = QPushButton()
        self.fs_prev_btn.clicked.connect(lambda: self.step_page(-1))
        self.fs_next_btn.clicked.connect(lambda: self.step_page(1))
        self.fs_page_info = QLabel()
        self.fs_zoom_out_btn = QPushButton()
        self.fs_zoom_in_btn = QPushButton()
        self.fs_zoom_fit_btn = QPushButton()
        self.fs_zoom_label = QLabel("100%")
        self.fs_zoom_out_btn.clicked.connect(lambda: self.view.zoom_out())
        self.fs_zoom_in_btn.clicked.connect(lambda: self.view.zoom_in())
        self.fs_zoom_fit_btn.clicked.connect(lambda: self.view.reset_view())
        self.fs_keep_page_btn = QPushButton()
        self.fs_keep_page_btn.clicked.connect(self.keep_current_full)
        self.fs_reset_btn = QPushButton()
        self.fs_reset_btn.clicked.connect(self.reset_current_auto)
        bar.addWidget(self.fs_exit_btn)
        bar.addWidget(self.fs_prev_btn)
        bar.addWidget(self.fs_next_btn)
        bar.addWidget(self.fs_page_info, 1)
        bar.addWidget(self.fs_zoom_out_btn)
        bar.addWidget(self.fs_zoom_label)
        bar.addWidget(self.fs_zoom_in_btn)
        bar.addWidget(self.fs_zoom_fit_btn)
        bar.addWidget(self.fs_keep_page_btn)
        bar.addWidget(self.fs_reset_btn)

        self.fs_rotate_bar = QWidget()
        self.fs_rotate_bar.setObjectName("fsBar")
        self.fs_rotate_bar.setVisible(False)
        rot = QHBoxLayout(self.fs_rotate_bar)
        rot.setContentsMargins(10, 4, 10, 8)
        rot.setSpacing(8)
        self.fs_hint = QLabel()
        self.fs_hint.setWordWrap(False)
        self.fs_rotate_label = QLabel()
        self.fs_ccw_btn = QPushButton()
        self.fs_cw_btn = QPushButton()
        self.fs_ccw_btn.clicked.connect(lambda: self._nudge_rotate(90.0))
        self.fs_cw_btn.clicked.connect(lambda: self._nudge_rotate(-90.0))
        self.fs_rotate_slider = QSlider(Qt.Orientation.Horizontal)
        self.fs_rotate_slider.setRange(-180, 180)
        self.fs_rotate_slider.setValue(0)
        self.fs_rotate_slider.setSingleStep(1)
        self.fs_rotate_slider.setPageStep(15)
        self.fs_rotate_spin = QDoubleSpinBox()
        self.fs_rotate_spin.setRange(-ROTATE_LIMIT, ROTATE_LIMIT)
        self.fs_rotate_spin.setSingleStep(0.1)
        self.fs_rotate_spin.setDecimals(1)
        self.fs_rotate_spin.setSuffix(" °")
        self.fs_rotate_slider.valueChanged.connect(self._rotate_live_from_slider)
        self.fs_rotate_slider.sliderReleased.connect(lambda: self._rotate_commit())
        self.fs_rotate_spin.valueChanged.connect(self._rotate_live_from_spin)
        self.fs_rotate_apply_btn = QPushButton()
        self.fs_rotate_apply_btn.clicked.connect(lambda: self._rotate_commit())
        rot.addWidget(self.fs_hint, 1)
        rot.addWidget(self.fs_ccw_btn)
        rot.addWidget(self.fs_cw_btn)
        rot.addWidget(self.fs_rotate_label)
        rot.addWidget(self.fs_rotate_slider, 2)
        rot.addWidget(self.fs_rotate_spin)
        rot.addWidget(self.fs_rotate_apply_btn)

        host = self.view_host.layout()
        host.insertWidget(0, self.fs_bar)
        host.addWidget(self.fs_rotate_bar)

    def _left_is_hidden(self) -> bool:
        if not self.left_panel.isVisible():
            return True
        sizes = self.main_splitter.sizes()
        return bool(sizes) and sizes[0] < 24

    def _sync_left_toggle_text(self) -> None:
        hidden = self._left_is_hidden()
        self.hide_left_btn.setText(self.t("show_left") if hidden else self.t("hide_left"))

    def _apply_left_compact(self, compact: bool) -> None:
        if compact == getattr(self, "_left_compact", False):
            if hasattr(self, "hide_left_btn"):
                self._sync_left_toggle_text()
            return
        self._left_compact = compact
        self.footer.setVisible(not compact)
        total = sum(self.preview_splitter.sizes()) or max(200, self.view.height())
        if compact:
            self.preview_splitter.setSizes([total, 0])
        elif self.preview_splitter.sizes()[1] < 40:
            self.preview_splitter.setSizes([max(120, total - 180), 180])
        self._sync_left_toggle_text()

    def _toggle_left(self) -> None:
        hide = not self._left_is_hidden()
        self.left_panel.setVisible(not hide)
        if hide:
            self.main_splitter.setSizes([0, max(400, self.width())])
        else:
            self.main_splitter.setSizes([380, max(400, self.width() - 380)])
        self._apply_left_compact(hide)

    def _on_main_split(self, *_args) -> None:
        if self._fs_active:
            return
        self._apply_left_compact(self._left_is_hidden())

    def _on_preview_split(self, *_args) -> None:
        if self._left_is_hidden() and not self._fs_active:
            collapsed = self.preview_splitter.sizes()[1] <= 2
            self.footer.setVisible(not collapsed)

    def _nudge_rotate(self, delta: float) -> None:
        angle = wrap_angle(float(self.rotate_spin.value()) + delta)
        self._rotate_live(angle)
        self._rotate_commit(angle)

    def _toggle_fullscreen_crop(self) -> None:
        if self._fs_active:
            self._exit_fullscreen_crop()
        else:
            self._enter_fullscreen_crop()

    def _enter_fullscreen_crop(self) -> None:
        if self._fs_active:
            return
        self._fs_active = True
        self._normal_geom = self.saveGeometry()
        self.header.setVisible(False)
        self.left_panel.setVisible(False)
        self.footer.setVisible(False)
        self.nav_bar.setVisible(False)
        self.below_wrap.setVisible(False)
        self.fs_bar.setVisible(True)
        self.fs_rotate_bar.setVisible(True)
        self.preview_splitter.setSizes([max(200, sum(self.preview_splitter.sizes())), 0])
        self._set_rotate_controls(float(self.rotate_spin.value()))
        self.showFullScreen()
        self._sync_fullscreen_chrome()
        self.view.setFocus(Qt.FocusReason.OtherFocusReason)

    def _exit_fullscreen_crop(self) -> None:
        if not self._fs_active:
            return
        self._fs_active = False
        self.fs_bar.setVisible(False)
        self.fs_rotate_bar.setVisible(False)
        self.header.setVisible(True)
        self.nav_bar.setVisible(True)
        self.below_wrap.setVisible(True)
        self.showNormal()
        if self._normal_geom is not None:
            self.restoreGeometry(self._normal_geom)
        hide_left = self._left_compact
        self.left_panel.setVisible(not hide_left)
        if hide_left:
            self.main_splitter.setSizes([0, max(400, self.width())])
            self.footer.setVisible(False)
            total = sum(self.preview_splitter.sizes()) or max(200, self.view.height())
            self.preview_splitter.setSizes([total, 0])
        else:
            self.main_splitter.setSizes([380, max(400, self.width() - 380)])
            self.footer.setVisible(True)
            total = sum(self.preview_splitter.sizes()) or max(200, self.view.height())
            if self.preview_splitter.sizes()[1] < 40:
                self.preview_splitter.setSizes([max(120, total - 180), 180])
        self._sync_left_toggle_text()
        self._sync_fullscreen_chrome()

    def _sync_fullscreen_chrome(self) -> None:
        self.fullscreen_btn.setText(self.t("exit_fullscreen") if self._fs_active else self.t("fullscreen"))
        if hasattr(self, "fs_page_info"):
            self.fs_page_info.setText(self.page_info.text())
            self.fs_zoom_label.setText(self.zoom_label.text())
            self.fs_exit_btn.setText(self.t("exit_fullscreen"))
            self.fs_prev_btn.setText(self.t("prev"))
            self.fs_next_btn.setText(self.t("next"))
            self.fs_zoom_out_btn.setText(self.t("zoom_out"))
            self.fs_zoom_in_btn.setText(self.t("zoom_in"))
            self.fs_zoom_fit_btn.setText(self.t("zoom_fit"))
            self.fs_keep_page_btn.setText(self.t("keep_full_page"))
            self.fs_reset_btn.setText(self.t("reset_page"))
            self.fs_hint.setText(self.t("fs_hint"))
            self.fs_rotate_label.setText(self.t("rotate"))
            self.fs_ccw_btn.setText(self.t("rotate_ccw"))
            self.fs_cw_btn.setText(self.t("rotate_cw"))
            self.fs_rotate_apply_btn.setText(self.t("apply_rotate"))

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _path_row(self, edit: QLineEdit, button: QPushButton, handler) -> QHBoxLayout:
        row = QHBoxLayout()
        button.clicked.connect(handler)
        row.addWidget(edit, 1)
        row.addWidget(button)
        return row

    def _ratio_row(self, value: float) -> tuple[QHBoxLayout, QSlider]:
        row = QHBoxLayout()
        text = QLabel()
        text.setMinimumWidth(120)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(70, 100)
        slider.setValue(int(round(value * 100)))
        number = QLabel(f"{value:.2f}")
        slider.valueChanged.connect(lambda v, lab=number: lab.setText(f"{v / 100:.2f}"))
        row.addWidget(text)
        row.addWidget(slider, 1)
        row.addWidget(number)
        return row, slider, text

    def _coord_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 30000)
        return spin

    def _ratio(self, slider: QSlider) -> float:
        return slider.value() / 100.0

    def apply_language(self) -> None:
        self.setWindowTitle(self.t("app_title"))
        self.title_label.setText(self.t("app_title"))
        self.subtitle_label.setText(self.t("subtitle"))
        self.lang_label.setText(self.t("language"))
        self.file_section.setText(self.t("file"))
        self.input_edit.setPlaceholderText(self.t("src_pdf"))
        self.output_edit.setPlaceholderText(self.t("out_pdf"))
        self.input_browse.setText(self.t("browse"))
        self.output_browse.setText(self.t("browse"))
        self.reuse_box.setText(self.t("reuse"))
        self.open_after_box.setText(self.t("open_after"))
        self.crop_section.setText(self.t("crop_mode"))
        self.tight_box.setText(self.t("tight"))
        self.auto_rotate_box.setText(self.t("auto_rotate"))
        self.ocr_box.setText(self.t("ocr"))
        self.ocr_txt_box.setText(self.t("ocr_txt"))
        self.hint_label.setText(self.t("hint"))
        self.min_full[2].setText(self.t("min_full"))
        self.min_page[2].setText(self.t("min_page"))
        self.pages_section.setText(self.t("pages_section"))
        self.pages_only_label.setText(self.t("pages_only"))
        if hasattr(self, "pick_pages_btn"):
            self.pick_pages_btn.setText(self.t("select_pages_btn"))
        self.pages_edit.setPlaceholderText(self.t("pages_ph"))
        self.inspect_label.setText(self.t("inspect_pages"))
        self.inspect_edit.setPlaceholderText(self.t("inspect_ph"))
        self.advanced.setTitle(self.t("advanced"))
        self.jobs_label.setText(self.t("jobs"))
        self.dpi_label.setText(self.t("dpi"))
        self.work_label.setText(self.t("work_dir"))
        self.clear_cache_btn.setText(self.t("clear_cache"))
        self.clear_cache_btn.setToolTip(self.t("clear_cache_tip"))
        self.forget_edits_btn.setText(self.t("forget_edits"))
        self.analyze_btn.setText(self.t("analyze"))
        self.keep_all_btn.setText(self.t("keep_full_all"))
        self.uniform_btn.setText(self.t("uniform_btn"))
        self.organize_btn.setText(self.t("organize_btn"))
        self.rotate_all_ccw_btn.setText(self.t("rotate_all_ccw"))
        self.rotate_all_cw_btn.setText(self.t("rotate_all_cw"))
        self.generate_btn.setText(self.t("generate"))
        self.ocr_page_btn.setText(self.t("ocr_page"))
        self.ocr_book_btn.setText(self.t("ocr_book"))
        self.cancel_btn.setText(self.t("cancel"))
        self.open_btn.setText(self.t("open_result"))
        self.folder_btn.setText(self.t("open_folder"))
        self.log_section.setText(self.t("log"))
        self.prev_btn.setText(self.t("prev"))
        self.next_btn.setText(self.t("next"))
        self.zoom_out_btn.setText(self.t("zoom_out"))
        self.zoom_in_btn.setText(self.t("zoom_in"))
        self.zoom_fit_btn.setText(self.t("zoom_fit"))
        self.keep_page_btn.setText(self.t("keep_full_page"))
        self.reset_btn.setText(self.t("reset_page"))
        self.del_page_btn.setText(self.t("del_page"))
        self.del_page_btn.setToolTip(self.t("del_page_tip"))
        self.page_ccw_btn.setText(self.t("rotate_ccw"))
        self.page_cw_btn.setText(self.t("rotate_cw"))
        self._sync_left_toggle_text()
        self._sync_fullscreen_chrome()
        self.rot_hint.setText(f"{self.t('zoom_hint')} {self.t('rotate_hint')}")
        for label, key in zip(self.coord_labels, ("left", "top", "right", "bottom")):
            label.setText(self.t(key))
        self.rotate_name_label.setText(self.t("rotate"))
        self.rotate_apply_btn.setText(self.t("apply_rotate"))
        self.results_section.setText(self.t("page_results"))
        self.table.setHorizontalHeaderLabels([self.t("col_page"), self.t("col_note"), self.t("col_box")])
        self.view.set_placeholder(self.t("placeholder"))
        if not crop.ocr_available():
            self.ocr_box.setToolTip(self._ocr_missing())
        if self.src is None and not self.plans:
            self.status.setText(self.t("status_idle"))
            self.page_info.setText(self.t("no_pdf"))
            if hasattr(self, "fs_page_info"):
                self.fs_page_info.setText(self.page_info.text())
            self.crop_label.setText(f"{self.t('crop_box')}：-")
        elif self._current_key() in self.plans:
            self.show_plan(self._current_key())
        elif self.src is not None:
            self.page_info.setText(self.t("pages_total", pages=self.pdf_pages))
            if hasattr(self, "fs_page_info"):
                self.fs_page_info.setText(self.page_info.text())
            self.crop_label.setText(self.t("crop_unanalyzed"))
            self.note_label.setText(self.t("preview_note"))

    def localize_engine(self, message: str) -> str:
        if self.lang != "en":
            return message
        rules = (
            (r"^抽出第 (\d+) 页$", r"Extracting page \1"),
            (r"^分析第 (\d+) 页$", r"Analyzing page \1"),
            (r"^写入第 (\d+) 页$", r"Writing page \1"),
            (r"^OCR 第 (\d+) 页$", r"OCR page \1"),
            (r"^读取对照文本 (.+)$", r"Reading companion text \1"),
            (r"^已写入 (\d+) 页可复制文字$", r"Wrote copyable text on \1 pages"),
            (r"^共 (\d+) 页，准备抽图$", r"\1 pages, extracting images"),
            (r"^缓存与当前 PDF 不匹配，重新抽图$", "Cache does not match this PDF; extracting again"),
            (r"^使用 Poppler 抽出页面图$", "Extracting pages with Poppler"),
            (r"^写入可复制文字层$", "Writing copyable text layer"),
            (r"^读取页数$", "Reading page count"),
            (r"^开始分析裁切框$", "Analyzing crop boxes"),
            (r"^统一裁边每页$", "Cropping every page with uniform margins"),
            (r"^裁边第 (\d+) 页$", r"Cropping page \1"),
            (r"^写入裁边 PDF$", "Writing cropped PDF"),
            (r"^开始 OCR$", "Starting OCR"),
            (r"^OCR 判断文种$", "OCR: detecting the book's script"),
            (r"^OCR 使用 (.+)$", r"OCR using \1"),
            (r"^渲染检查图$", "Rendering inspection images"),
            (r"^完成$", "Done"),
        )
        for pattern, repl in rules:
            updated = re.sub(pattern, repl, message)
            if updated != message:
                return updated
        return message

    def append_log(self, text: str) -> None:
        text = text.rstrip()
        self.log.appendPlainText(text)
        self._write_log_file(text)

    def _write_log_file(self, text: str) -> None:
        """Keep a rotating log next to the caches so failures stay diagnosable."""
        try:
            path = crop.app_data_dir("运行日志.log")
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file() and path.stat().st_size > 2 * 1024 * 1024:
                path.replace(path.with_name(path.name + ".old"))
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{stamp}] {text}\n")
        except Exception:
            pass

    def browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("pick_src"), self._last_dir, self.t("pdf_filter"))
        if path:
            self.set_input(Path(path))

    def browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, self.t("save_out"), self.output_edit.text(), self.t("pdf_filter_save"))
        if path:
            output = Path(path)
            self.output_edit.setText(str(output))

    def set_input(self, src: Path) -> None:
        self.src = src
        self._last_dir = str(src.parent)
        self.input_edit.setText(str(src))
        self.output_edit.setText(str(crop.default_output_for(src)))
        self.work_edit.setText(str(crop.default_work_dir_for(src)))
        self.plans.clear()
        self.page_list = []
        self.last_output = None
        self._preview_cache.clear()
        self._uniform = None
        self._uniform_base = {}
        self._pending_requests = []
        edits = crop.load_book_edits(src)
        self._stored_crops = edits["crops"]
        self._stored_rotates = edits["rotates"]
        self._page_order = list(edits["order"]) or None
        self._deleted = set(edits["deleted"])
        self._imports = dict(edits["imports"])
        self._import_counter = max([key - crop.IMPORT_PAGE_BASE for key in self._imports] + [0])
        self.view.reset_view()
        try:
            self.pdf_pages = crop.page_count(src, src.parent)
        except Exception as exc:
            QMessageBox.critical(self, self.t("app_title"), self.t("read_pages_fail", exc=exc))
            return
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, max(1, self.pdf_pages))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.current_page = 1
        self.page_info.setText(self.t("pages_total", pages=self.pdf_pages))
        if hasattr(self, "fs_page_info"):
            self.fs_page_info.setText(self.page_info.text())
        self.status.setText(self.t("opened", name=src.name, pages=self.pdf_pages))
        self.append_log(self.t("opened_log", src=src, pages=self.pdf_pages))
        if self._stored_crops or self._stored_rotates:
            self.append_log(
                self.t("edits_found", crops=len(self._stored_crops), rotates=len(self._stored_rotates))
            )
        self._rebuild_imports()
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        self.show_pdf_preview(1)

    def show_pdf_preview(self, page: int) -> None:
        if self.src is None:
            return
        try:
            image = render_pdf_page(self.src, page, dpi=90)
        except Exception as exc:
            self.append_log(self.t("preview_fail", exc=exc))
            return
        self.current_page = self._pos_of(page) or self.current_page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page)
        self.page_spin.blockSignals(False)
        angle = float(self._stored_rotates.get(page, 0.0) or 0.0)
        if abs(angle) > 1e-6:
            image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        box = None
        if self._uniform:
            width, height = image.size
            box = crop.apply_uniform_to_box((0, 0, width, height), width, height, self._uniform)
        self.view.set_image(image, box, box is not None)
        if box is not None:
            self.crop_label.setText(
                self.t("crop_fmt", l=box[0], t=box[1], r=box[2], b=box[3], w=image.width, h=image.height)
            )
            self.note_label.setText(self.t("uniform_preview_note"))
        else:
            self.crop_label.setText(self.t("crop_unanalyzed"))
            self.note_label.setText(self.t("preview_note"))
        if hasattr(self, "fs_page_info"):
            self.fs_page_info.setText(self.t("pages_total", pages=self.pdf_pages))

    def goto_page(self, page: int) -> None:
        """Go to a 1-based position in the arranged output (inserted pages included)."""
        if self.pdf_pages <= 0:
            return
        if self.page_list:
            page = max(1, min(len(self.page_list), page))
        else:
            page = max(1, min(self.pdf_pages, page))
        self.current_page = page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page)
        self.page_spin.blockSignals(False)
        key = self._current_key()
        if key is not None and key in self.plans:
            self.show_plan(key)
        elif self.src is not None:
            self.show_pdf_preview(key if key is not None else page)
        if not getattr(self, "_table_driven", False):
            self._sync_table_selection()

    def step_page(self, delta: int) -> None:
        """Move through the arranged output, one page at a time."""
        self.goto_page(self.current_page + delta)

    def _current_key(self) -> int | None:
        """Internal key of the page at the current position (inserts included)."""
        if self.page_list and 1 <= self.current_page <= len(self.page_list):
            return self.page_list[self.current_page - 1]
        return None

    def _pos_of(self, key: int) -> int:
        """1-based position of an internal key in the output; 0 when absent."""
        try:
            return self.page_list.index(key) + 1
        except ValueError:
            return 0

    def _sync_page_spin_range(self) -> None:
        top = len(self.page_list) if self.page_list else self.pdf_pages
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, max(1, top))
        self.page_spin.setValue(self.current_page)
        self.page_spin.blockSignals(False)

    def _pages_filter(self) -> set[int] | None:
        """Selected output positions from the pages field; None means every page."""
        text = self.pages_edit.text().strip()
        if not text or self.src is None:
            return None
        try:
            pages = crop.parse_page_spec(text)
        except ValueError:
            return None
        total = len(self.page_list) or self.pdf_pages
        return {pos for pos in pages if 1 <= pos <= total}

    def _source_page_keys(self) -> set[int]:
        """Every source page of the book (deleted and filtered ones included)."""
        if self.pdf_pages <= 0:
            return set()
        return set(range(1, self.pdf_pages + 1))

    def _ordered_output_keys(self) -> list[int]:
        """Keys written by 生成 PDF: the arrangement narrowed by the page selection."""
        keys = self._ordered_keys()
        selected = self._pages_filter()
        if selected is None:
            return keys
        return [keys[pos - 1] for pos in sorted(selected) if 1 <= pos <= len(keys)]

    def _selected_source_pages(self) -> set[int] | None:
        """Source pages needed for the selected positions; None means all of them."""
        selected = self._pages_filter()
        if selected is None:
            return None
        keys = self._ordered_keys()
        return {
            keys[pos - 1]
            for pos in selected
            if 1 <= pos <= len(keys) and keys[pos - 1] < crop.IMPORT_PAGE_BASE
        }

    def open_pages_picker(self) -> None:
        if self.src is None:
            QMessageBox.information(self, self.t("app_title"), self.t("need_src"))
            return
        if self.busy or self._rotate_busy:
            return
        keys = self._ordered_keys()
        if not keys:
            return
        current = self._pages_filter()
        if current is None:
            current = set(range(1, len(keys) + 1))
        dialog = PageSelectDialog(self, keys, current, self.t, self._thumb_pixmaps(keys))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_positions()
        self.pages_edit.setText(crop.spec_from_positions(chosen))
        self._pages_filter_changed()
        self.status.setText(self.t("select_pages_applied", n=len(chosen)))

    def _pages_filter_changed(self) -> None:
        text = self.pages_edit.text().strip()
        if text:
            try:
                pages = crop.parse_page_spec(text)
            except ValueError as exc:
                self.status.setText(self.t("pages_filter_bad", text=exc))
                return
            if not pages or not self.page_list:
                self.status.setText(self.t("pages_filter_empty"))
                return
            if max(pages) > len(self.page_list):
                self.status.setText(self.t("pages_filter_range", n=len(self.page_list)))
                return
            self.status.setText(self.t("pages_filter_hint", text=text, n=len(self.page_list)))
        self._refresh_table()
        if self.page_list and self.current_page > len(self.page_list):
            self.goto_page(len(self.page_list))

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape and self._fs_active:
                self._exit_fullscreen_crop()
                return True
            if key == Qt.Key.Key_F11:
                self._toggle_fullscreen_crop()
                return True
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                focus = QApplication.focusWidget()
                if isinstance(focus, (QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox)):
                    return False
                if self.plans or self.pdf_pages:
                    self.step_page(-1 if key == Qt.Key.Key_Left else 1)
                    return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._fs_active:
            self._exit_fullscreen_crop()
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen_crop()
        elif event.key() == Qt.Key.Key_Left:
            self.goto_page(self.current_page - 1)
        elif event.key() == Qt.Key.Key_Right:
            self.goto_page(self.current_page + 1)
        else:
            super().keyPressEvent(event)

    def _preview_pixmap(self, path: Path) -> QPixmap:
        key = str(path)
        cached = self._preview_cache.get(key)
        if cached is not None:
            return cached
        pix = pil_to_pixmap(load_preview_image(path))
        self._preview_cache[key] = pix
        return pix

    def _on_table_select(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self._table_driven = True
        try:
            self.goto_page(rows[0].row() + 1)
        finally:
            self._table_driven = False

    def show_plan(self, page: int) -> None:
        plan = self.plans[page]
        try:
            display_pix = self._preview_pixmap(plan.path)
            original_pix = display_pix
            if plan.source_path != plan.path and plan.source_path.exists():
                original_pix = self._preview_pixmap(plan.source_path)
        except Exception as exc:
            self.append_log(self.t("open_page_fail", page=page, exc=exc))
            return
        self.current_page = self._pos_of(page) or self.current_page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page)
        self.page_spin.blockSignals(False)
        self.view.full_size = (plan.width, plan.height)
        self.view.pixmap = display_pix
        self.view.original_pixmap = original_pix
        self.view.crop = plan.crop
        self.view.enabled = True
        self.view.rotate_deg = float(plan.rotate_deg or 0.0)
        self.view.live_angle = self.view.rotate_deg
        self.view._rotating = False
        self.view._cached_dest = None
        self.view.update()
        self._sync_crop_vars(plan.crop)
        self._set_rotate_controls(plan.rotate_deg)
        self.crop_label.setText(
            self.t(
                "crop_fmt",
                l=plan.crop[0],
                t=plan.crop[1],
                r=plan.crop[2],
                b=plan.crop[3],
                w=plan.width,
                h=plan.height,
            )
        )
        self.note_label.setText(self.t("page_note", page=self._page_label(page), note=plan.note))
        self.page_info.setText(self.t("page_analyzed", page=self._page_label(page), n=len(self.plans)))
        if hasattr(self, "fs_page_info"):
            self.fs_page_info.setText(self.page_info.text())

    def _sync_crop_vars(self, box: tuple[int, int, int, int]) -> None:
        self._updating = True
        self.left_spin.setValue(box[0])
        self.top_spin.setValue(box[1])
        self.right_spin.setValue(box[2])
        self.bottom_spin.setValue(box[3])
        self._updating = False

    def _on_zoom_changed(self, zoom: float) -> None:
        text = f"{int(round(zoom * 100))}%"
        self.zoom_label.setText(text)
        if hasattr(self, "fs_zoom_label"):
            self.fs_zoom_label.setText(text)

    def _on_canvas_crop(self, box: tuple[int, int, int, int]) -> None:
        self._sync_crop_vars(box)
        self._apply_manual_crop(box)

    def _coords_changed(self) -> None:
        key = self._current_key()
        if self._updating or key not in self.plans:
            return
        plan = self.plans[key]
        box = crop.clamp_crop(
            (self.left_spin.value(), self.top_spin.value(), self.right_spin.value(), self.bottom_spin.value()),
            plan.width,
            plan.height,
        )
        self.view.set_crop(box)
        self._apply_manual_crop(box)

    def _apply_manual_crop(self, box: tuple[int, int, int, int]) -> None:
        plan = self.plans.get(self._current_key())
        if plan is None:
            return
        plan.crop = box
        if not plan.note.startswith("manual-override"):
            plan.note = f"manual-override+auto-{plan.note}"
        self.crop_label.setText(
            self.t("crop_fmt", l=box[0], t=box[1], r=box[2], b=box[3], w=plan.width, h=plan.height)
        )
        self.note_label.setText(self.t("page_note", page=self._page_label(plan.page), note=plan.note))
        self._update_table_row(plan.page)
        self._save_edits()

    def _current_edits(self) -> tuple[dict[int, tuple[int, int, int, int]], dict[int, float]]:
        """Saved edits updated with the analyzed pages: manual crops, and angles that are not auto-deskew."""
        crops = dict(self._stored_crops)
        rotates = dict(self._stored_rotates)
        for plan in self.plans.values():
            if plan.page >= crop.IMPORT_PAGE_BASE:
                continue
            manual_crop = plan.note.startswith("manual-override")
            if manual_crop:
                crops[plan.page] = tuple(plan.crop)
            else:
                crops.pop(plan.page, None)
            # A manual crop box only fits the rotation it was drawn on, so keep that angle too.
            if abs(plan.rotate_deg) > 1e-6 and ("auto-rotate" not in plan.note or manual_crop):
                rotates[plan.page] = float(plan.rotate_deg)
            else:
                rotates.pop(plan.page, None)
        return crops, rotates

    def _save_edits(self) -> None:
        """Persist manual crops, rotations, the arranged order and inserted pages."""
        if self.src is None:
            return
        self._stored_crops, self._stored_rotates = self._current_edits()
        for key, entry in self._imports.items():
            plan = self.plans.get(key)
            if plan is not None:
                entry["crop"] = [int(value) for value in plan.crop]
                entry["rotate"] = float(plan.rotate_deg or 0.0)
                entry["note"] = plan.note
        order = self._ordered_keys() if self._page_order is not None else None
        try:
            crop.save_book_edits(
                self.src,
                self._stored_crops,
                self._stored_rotates,
                order,
                sorted(self._deleted),
                self._imports,
            )
        except OSError as exc:
            self.append_log(str(exc))

    def _drop_analysis(self) -> None:
        """Forget the current analysis and go back to the plain PDF preview."""
        self.plans.clear()
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        if self.page_list:
            self.goto_page(min(self.current_page, len(self.page_list)))

    def forget_edits(self) -> None:
        if self.src is None or self.busy or self._rotate_busy:
            return
        answer = QMessageBox.question(self, self.t("app_title"), self.t("forget_edits_confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._stored_crops, self._stored_rotates = {}, {}
        self._uniform = None
        self._uniform_base = {}
        self._page_order = None
        self._deleted = set()
        self._imports = {}
        self._import_counter = 0
        self._pending_requests = []
        crop.save_book_edits(self.src, {}, {}, [], [], {})
        self._wipe_imports_dir()
        self._drop_analysis()
        self.status.setText(self.t("edits_forgotten"))
        self.append_log(self.t("edits_forgotten"))

    def clear_cache(self) -> None:
        if self.busy or self._rotate_busy:
            return
        files, size = crop.cache_usage()
        if not files:
            QMessageBox.information(self, self.t("app_title"), self.t("cache_empty"))
            return
        answer = QMessageBox.question(
            self, self.t("app_title"), self.t("clear_cache_confirm", n=files, mb=size / 1048576)
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        root = crop.app_data_dir("cache")
        work_text = self.work_edit.text().strip()
        if self.plans and work_text and crop.is_relative_to(Path(work_text).resolve(), root.resolve()):
            self._drop_analysis()
        files, size = crop.clear_cache_root(root)
        self._preview_cache.clear()
        message = self.t("cache_cleared", n=files, mb=size / 1048576)
        self.status.setText(message)
        self.append_log(message)

    def _crop_mode(self) -> str:
        return "content" if self.tight_box.isChecked() else "edges"

    def _analyze_kwargs(self) -> dict:
        return {
            "min_width_ratio": self._ratio(self.min_page[1]),
            "min_height_ratio": self._ratio(self.min_page[1]),
            "min_full_width_ratio": self._ratio(self.min_full[1]),
            "min_full_height_ratio": self._ratio(self.min_full[1]),
            "crop_mode": self._crop_mode(),
        }

    def _set_rotate_controls(self, angle: float) -> None:
        self._updating = True
        self.rotate_spin.setValue(angle)
        self.rotate_slider.setValue(int(round(angle)))
        if hasattr(self, "fs_rotate_spin"):
            self.fs_rotate_spin.setValue(angle)
            self.fs_rotate_slider.setValue(int(round(angle)))
        self._updating = False

    def _rotate_live(self, angle: float) -> None:
        if self._updating:
            return
        self._set_rotate_controls(angle)
        self.view.set_live_angle(angle)

    def _rotate_live_from_spin(self, value: float) -> None:
        if self._updating:
            return
        angle = float(value)
        self.rotate_slider.blockSignals(True)
        self.rotate_slider.setValue(int(round(angle)))
        self.rotate_slider.blockSignals(False)
        if hasattr(self, "fs_rotate_slider"):
            self.fs_rotate_slider.blockSignals(True)
            self.fs_rotate_slider.setValue(int(round(angle)))
            self.fs_rotate_slider.blockSignals(False)
            if self.sender() is not self.fs_rotate_spin:
                self.fs_rotate_spin.blockSignals(True)
                self.fs_rotate_spin.setValue(angle)
                self.fs_rotate_spin.blockSignals(False)
            if self.sender() is not self.rotate_spin:
                self.rotate_spin.blockSignals(True)
                self.rotate_spin.setValue(angle)
                self.rotate_spin.blockSignals(False)
        self.view.set_live_angle(angle)

    def _rotate_live_from_slider(self, value: int) -> None:
        if self._updating:
            return
        angle = float(value)
        self.rotate_spin.blockSignals(True)
        self.rotate_spin.setValue(angle)
        self.rotate_spin.blockSignals(False)
        if hasattr(self, "fs_rotate_spin"):
            self.fs_rotate_spin.blockSignals(True)
            self.fs_rotate_spin.setValue(angle)
            self.fs_rotate_spin.blockSignals(False)
            if self.sender() is not self.fs_rotate_slider:
                self.fs_rotate_slider.blockSignals(True)
                self.fs_rotate_slider.setValue(int(round(angle)))
                self.fs_rotate_slider.blockSignals(False)
            if self.sender() is not self.rotate_slider:
                self.rotate_slider.blockSignals(True)
                self.rotate_slider.setValue(int(round(angle)))
                self.rotate_slider.blockSignals(False)
        self.view.set_live_angle(angle)

    def _rotate_commit(self, angle: float | None = None) -> None:
        key = self._current_key()
        if self._updating or key not in self.plans:
            return
        plan = self.plans[key]
        if angle is None:
            angle = float(self.rotate_spin.value())
        angle = clamp_angle(float(angle))
        self._set_rotate_controls(angle)
        if abs(angle - plan.rotate_deg) < 1e-3:
            self.view.set_live_angle(plan.rotate_deg)
            return
        if self._rotate_busy:
            self._rotate_pending = angle
            return
        self._start_rotate_job(plan, angle)

    def _start_rotate_job(
        self, plan: crop.PagePlan, angle: float, auto_rotate: bool = False, reset: bool = False
    ) -> None:
        """Re-analyze one page in the background (rotation change or 恢复本页自动裁切)."""
        self._rotate_busy = True
        self._rotate_pending = None
        if reset:
            self.status.setText(self.t("resetting", page=self._page_label(plan.page)))
        else:
            self.status.setText(self.t("rotating", page=self._page_label(plan.page), angle=angle))
        kwargs = self._analyze_kwargs()

        def work() -> None:
            try:
                updated = crop.analyze_one_page(
                    plan.source_path,
                    plan.page,
                    kwargs["min_width_ratio"],
                    kwargs["min_height_ratio"],
                    kwargs["min_full_width_ratio"],
                    kwargs["min_full_height_ratio"],
                    None,
                    angle,
                    kwargs["crop_mode"],
                    auto_rotate,
                )
                self.events.put(("rotated", updated, reset))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        threading.Thread(target=work, daemon=True).start()

    def reset_current_auto(self) -> None:
        key = self._current_key()
        if key not in self.plans or self._rotate_busy:
            return
        plan = self.plans[key]
        # Keep a hand-set angle; an auto-deskewed page is simply deskewed again.
        manual_angle = abs(plan.rotate_deg) > 1e-6 and "auto-rotate" not in plan.note
        self._start_rotate_job(
            plan,
            plan.rotate_deg if manual_angle else 0.0,
            auto_rotate=self.auto_rotate_box.isChecked() and not manual_angle,
            reset=True,
        )

    def _full_page_box(self, plan: crop.PagePlan) -> tuple[int, int, int, int]:
        return crop.clamp_crop((0, 0, plan.width, plan.height), plan.width, plan.height)

    def keep_current_full(self) -> None:
        key = self._current_key()
        if key not in self.plans:
            QMessageBox.information(self, self.t("app_title"), self.t("need_analyze_keep"))
            return
        plan = self.plans[key]
        self._apply_manual_crop(self._full_page_box(plan))
        if "keep-full" not in plan.note:
            plan.note = f"{plan.note}+keep-full"
        self.view.set_crop(plan.crop)
        self.show_plan(plan.page)
        self._update_table_row(plan.page)
        self.status.setText(self.t("kept_full_page", page=self._page_label(plan.page)))

    def keep_all_full(self) -> None:
        if not self.plans:
            QMessageBox.information(self, self.t("app_title"), self.t("need_analyze_keep"))
            return
        self._uniform = None
        self._uniform_base = {}
        for plan in self.plans.values():
            plan.crop = self._full_page_box(plan)
            if not plan.note.startswith("manual-override"):
                plan.note = "manual-override+keep-full"
            elif "keep-full" not in plan.note:
                plan.note = f"{plan.note}+keep-full"
        key = self._current_key()
        if key in self.plans:
            self.view.set_crop(self.plans[key].crop)
            self.show_plan(key)
        self._refresh_table()
        self._save_edits()
        self.status.setText(self.t("kept_full_all", n=len(self.plans)))
        self.append_log(self.t("kept_full_all", n=len(self.plans)))

    # ------------------------------------------------------------------ helpers

    def _page_label(self, key: int) -> str:
        pos = self._pos_of(key)
        if pos:
            return self.t("page_label", page=pos)
        if key < crop.IMPORT_PAGE_BASE:
            return self.t("page_label_orig", page=key)
        return self.t("page_label_inserted")

    def _page_item(self, page: int) -> QTableWidgetItem:
        item = QTableWidgetItem(self._page_label(page))
        item.setData(Qt.ItemDataRole.UserRole, int(page))
        return item

    @staticmethod
    def _order_keys(keys, order, deleted) -> list[int]:
        available = set(keys)
        if order is None:
            return sorted(key for key in keys if key not in deleted)
        seen = set(order)
        ordered = [key for key in order if key in available and key not in deleted]
        ordered += [key for key in sorted(available) if key not in seen and key not in deleted]
        return ordered

    def _ordered_keys(self) -> list[int]:
        source = self._source_page_keys()
        # Source-page plans outside the pages filter stay out of the output;
        # inserted pages always belong.
        available = {key for key in self.plans if key >= crop.IMPORT_PAGE_BASE or key in source}
        available |= source
        return self._order_keys(available, self._page_order, self._deleted)

    def _materialize_order(self) -> list[int]:
        if self._page_order is None:
            self._page_order = self._ordered_keys()
        return list(self._page_order)

    def _wipe_imports_dir(self) -> None:
        if self.src is None:
            return
        root = crop.imports_dir_for(self.src)
        if not root.is_dir():
            return
        for entry in root.iterdir():
            if entry.is_file():
                entry.unlink(missing_ok=True)
        try:
            root.rmdir()
        except OSError:
            pass

    # ---------------------------------------------------------- uniform margins

    def open_uniform_dialog(self) -> None:
        if self.src is None:
            QMessageBox.information(self, self.t("app_title"), self.t("need_src"))
            return
        if self.busy or self._rotate_busy:
            return
        dialog = UniformCropDialog(self, self._uniform, self._uniform_unit, self.t)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        margins = dialog.margin_cm()
        self._uniform_unit = dialog.selected_unit()
        generate = dialog.wants_generate()
        self.apply_uniform(margins)
        if generate and not self.busy:
            self.start_generate()

    def _uniform_text(self, margins: tuple[float, float, float, float]) -> str:
        left, top, right, bottom = margins
        return self.t("uniform_margins_fmt", l=left, t=top, r=right, b=bottom)

    def apply_uniform(self, margins: tuple[float, float, float, float] | None) -> None:
        """Set book-wide margins (cm from each original page edge); zeros restore."""
        if margins is not None:
            margins = tuple(float(value) for value in margins)
            if not any(value > 1e-9 for value in margins):
                margins = None
        else:
            margins = None
        self._uniform = margins
        restored_bases: dict[int, tuple[tuple[int, int, int, int], str]] = {}
        if margins is None:
            restored_bases, self._uniform_base = self._uniform_base, {}
        if not self.plans:
            if self.page_list:
                self.goto_page(min(self.current_page, len(self.page_list)))
            if margins is not None:
                message = self.t("uniform_set_no_plans", margins=self._uniform_text(margins))
                self.status.setText(message)
                self.append_log(message)
            return
        for plan in self.plans.values():
            if margins is not None:
                base = self._uniform_base.setdefault(plan.page, (tuple(plan.crop), plan.note))
                plan.crop = crop.apply_uniform_to_box(base[0], plan.width, plan.height, margins)
                if "uniform" not in plan.note:
                    if plan.note.startswith("manual-override"):
                        plan.note += "+uniform"
                    else:
                        plan.note = f"manual-override+uniform+{plan.note}"
            else:
                base = restored_bases.pop(plan.page, None)
                if base is not None:
                    plan.crop, plan.note = base
        key = self._current_key()
        if key in self.plans:
            self.view.set_crop(self.plans[key].crop)
            self.show_plan(key)
        self._refresh_table()
        self._save_edits()
        if margins is not None:
            message = self.t("uniform_applied", n=len(self.plans), margins=self._uniform_text(margins))
        else:
            message = self.t("uniform_restored", n=len(self.plans))
        self.status.setText(message)
        self.append_log(message)

    # ------------------------------------------------------------- rotate all

    def rotate_all_pages(self, delta: float) -> None:
        if self.src is None or self.busy or self._rotate_busy or self.pdf_pages <= 0:
            return
        direction = self.t("rotate_dir_ccw" if delta > 0 else "rotate_dir_cw")
        answer = QMessageBox.question(
            self, self.t("app_title"), self.t("rotate_all_confirm", n=self.pdf_pages, dir=direction)
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        # Make sure every inserted page has a workable base image before rotating it.
        for key in list(self._imports):
            if self.plans.get(key) is None:
                try:
                    self.plans[key] = self._build_import_plan(key, self._imports[key])
                except Exception:
                    pass
        self._stored_crops = {}
        self._uniform_base = {}
        for page in range(1, self.pdf_pages + 1):
            plan = self.plans.get(page)
            base_angle = (
                float(plan.rotate_deg)
                if plan is not None
                else float(self._stored_rotates.get(page, 0.0) or 0.0)
            )
            angle = wrap_angle(base_angle + delta)
            if abs(angle) > 1e-6:
                self._stored_rotates[page] = angle
            else:
                self._stored_rotates.pop(page, None)
        had_source_plans = any(key < crop.IMPORT_PAGE_BASE for key in self.plans)
        # Source plans are stale (wrong orientation); the re-analysis rebuilds them.
        self.plans = {key: plan for key, plan in self.plans.items() if key >= crop.IMPORT_PAGE_BASE}
        self.page_list = self._ordered_keys()
        self._refresh_table()
        try:
            job = self._read_job(write_pdf=False) if had_source_plans else None
        except Exception as exc:
            QMessageBox.critical(self, self.t("app_title"), str(exc))
            return
        imports = [(key, dict(entry)) for key, entry in sorted(self._imports.items())]
        kwargs = self._analyze_kwargs()
        self._set_busy(True)
        self.cancel.clear()
        message = self.t("rotate_all_done", dir=direction)
        self.status.setText(message)
        self.append_log(message)
        src = self.src

        def work() -> None:
            try:
                updated: list[tuple[crop.PagePlan, dict]] = []
                for key, entry in imports:
                    base = crop.imports_dir_for(src) / f"import-{key}.jpg"
                    if not base.is_file():
                        continue
                    angle = wrap_angle(float(entry.get("rotate", 0.0) or 0.0) + delta)
                    plan = crop.analyze_one_page(
                        base,
                        key,
                        kwargs["min_width_ratio"],
                        kwargs["min_height_ratio"],
                        kwargs["min_full_width_ratio"],
                        kwargs["min_full_height_ratio"],
                        None,
                        angle,
                        kwargs["crop_mode"],
                        False,
                    )
                    plan.note = f"import+{plan.note}"
                    entry["rotate"] = float(plan.rotate_deg or 0.0)
                    entry["crop"] = [int(value) for value in plan.crop]
                    entry["note"] = plan.note
                    updated.append((plan, entry))
                    self.events.put(("progress", self.t("ins_progress", i=len(updated), n=len(imports)), len(updated), len(imports)))
                self.events.put(("rotate-all-imports", updated))
                if job is not None:
                    def progress(message: str, current: int, total: int) -> None:
                        crop.check_cancelled(self.cancel)
                        self.events.put(("progress", message, current, total))

                    plans = crop.execute_job(job, progress=progress, cancel=self.cancel)
                    self.events.put(("done", plans, job, False))
                else:
                    self.events.put(("rotate-all-finished", direction))
            except crop.CancelledError:
                self.events.put(("cancelled",))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    # ---------------------------------------------------------- page organizer

    def open_organizer(self) -> None:
        if self.src is None:
            QMessageBox.information(self, self.t("app_title"), self.t("need_src"))
            return
        if self.busy or self._rotate_busy:
            return
        keys = self._ordered_keys()
        entries = [(key, self._page_note(key)) for key in keys]
        deleted_keys = sorted(key for key in self._deleted if key < crop.IMPORT_PAGE_BASE)
        deleted = [(key, self._page_note(key)) for key in deleted_keys]
        thumbs = self._thumb_pixmaps(keys + deleted_keys)
        dialog = PageOrganizeDialog(self, entries, deleted, self.t, thumbs)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        order, deleted_now, requests, dropped = dialog.result()
        self._apply_order(order, deleted_now, dropped)
        for request in requests:
            self._start_insert_request(request)

    def _page_note(self, key: int) -> str:
        plan = self.plans.get(key)
        return plan.note if plan is not None else self.t("not_analyzed")

    def _thumb_pixmaps(self, keys) -> dict[int, QPixmap]:
        """Small page images for the organizer; cached per page and source file."""
        thumbs: dict[int, QPixmap] = {}
        for key in keys:
            plan = self.plans.get(key)
            if plan is not None:
                ident = str(plan.path)
            elif self.src is not None and 1 <= key <= self.pdf_pages:
                ident = f"pdf:{key}"
            else:
                continue
            cache_key = (key, ident)
            cached = self._thumb_cache.get(cache_key)
            if cached is not None:
                thumbs[key] = cached
                continue
            try:
                if plan is not None:
                    image = load_preview_image(plan.path, max_side=512)
                else:
                    image = render_pdf_page(self.src, key, dpi=16)
                image.thumbnail((120, 168))
                pix = pil_to_pixmap(image)
            except Exception:
                continue
            self._thumb_cache[cache_key] = pix
            thumbs[key] = pix
        return thumbs

    def _reshow(self, key: int | None, fallback: int | None = None) -> None:
        """Re-show the page the user was looking at after the order changed."""
        if not self.page_list:
            return
        pos = self._pos_of(key) if key is not None else 0
        if pos:
            self.goto_page(pos)
        else:
            self.goto_page(max(1, min(fallback or self.current_page, len(self.page_list))))

    def _apply_order(
        self, order: list[int], deleted: list[int], dropped: list[int] | None = None
    ) -> None:
        shown = self._current_key()
        # The incoming order may bring deleted pages back (restore) and drop
        # others (delete), so validate against every page that can exist -
        # including restorable source pages - not just the visible ones.
        universe = self._source_page_keys() | set(self.plans) | set(self._imports)
        self._page_order = [key for key in order if key in universe]
        self._deleted = {key for key in deleted if key < crop.IMPORT_PAGE_BASE}
        # Only pages the user explicitly deleted disappear. An inserted page that
        # merely fell out of the handed-in order stays, appended at the end -
        # losing a page because the dialog missed it would be far worse.
        for key in dict.fromkeys(list(dropped or []) + [k for k in deleted if k >= crop.IMPORT_PAGE_BASE]):
            self._imports.pop(key, None)
            self.plans.pop(key, None)
        ordered_now = set(self._page_order)
        for key in sorted(self._imports):
            if key not in ordered_now:
                self._page_order.append(key)
                ordered_now.add(key)
        if dropped or any(k >= crop.IMPORT_PAGE_BASE for k in deleted):
            self.append_log(self.t("insert_removed", n=len(dropped or [])))
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        self._save_edits()
        self.status.setText(self.t("pages_reordered", n=len(self.page_list)))
        self.append_log(self.t("pages_reordered_log", n=len(self.page_list)))
        self._reshow(shown)

    def _on_table_reorder(self, rows: list[int], target: int) -> None:
        """Rows dragged in the results table land as one block before target."""
        keys = self._ordered_keys()
        rows = [row for row in sorted(set(rows)) if 0 <= row < len(keys)]
        if not rows:
            return
        target = max(0, min(len(keys), target))
        before = sum(1 for row in rows if row < target)
        insert_at = target - before
        if before == len(rows) and insert_at == rows[0]:
            return
        block = [keys[row] for row in rows]
        for row in reversed(rows):
            keys.pop(row)
        for offset, key in enumerate(block):
            keys.insert(insert_at + offset, key)
        self._page_order = keys
        self.page_list = list(keys)
        self._refresh_table()
        self._save_edits()
        self.append_log(self.t("pages_reordered_log", n=len(self.page_list)))
        self.goto_page(insert_at + 1)
        self.status.setText(self.t("pages_reordered", n=len(keys)))

    def _on_table_context(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= self.table.rowCount():
            return
        self.table.selectRow(row)
        keys = self._ordered_keys()
        if not 0 <= row < len(keys):
            return
        key = keys[row]
        menu = QMenu(self.table)
        menu.addAction(self.t("ctx_move_up"), lambda: self._move_page(row, -1))
        menu.addAction(self.t("ctx_move_down"), lambda: self._move_page(row, 1))
        menu.addSeparator()
        menu.addAction(self.t("ctx_duplicate"), lambda: self._start_insert_request({"type": "dup", "key": key, "index": row + 1}))
        menu.addAction(self.t("ctx_delete_page"), lambda: self._delete_pages([key]))
        if key in self._deleted:
            menu.addAction(self.t("ctx_restore_page"), lambda: self._restore_pages([key]))
        insert = menu.addMenu(self.t("ctx_insert_after"))
        insert.addAction(self.t("ctx_ins_pdf"), lambda: self._quick_insert_pdf(row + 1))
        insert.addAction(self.t("ctx_ins_image"), lambda: self._quick_insert_image(row + 1))
        insert.addAction(self.t("ctx_ins_blank"), lambda: self._start_insert_request({"type": "blank", "index": row + 1}))
        menu.addSeparator()
        menu.addAction(self.t("ctx_organize"), self.open_organizer)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _move_page(self, row: int, delta: int) -> None:
        keys = self._materialize_order()
        target = row + delta
        if not 0 <= row < len(keys) or not 0 <= target < len(keys):
            return
        moved = keys[row]
        keys[row], keys[target] = keys[target], keys[row]
        self._page_order = keys
        self.page_list = self._ordered_keys()
        self._refresh_table()
        self.table.selectRow(target)
        self._save_edits()
        self.append_log(self.t("pages_reordered_log", n=len(self.page_list)))
        self._reshow(moved)

    def _delete_pages(self, keys: list[int]) -> None:
        if not keys or self.src is None or self.busy or self._rotate_busy:
            return
        shown = self._current_key()
        order = self._materialize_order()
        for key in keys:
            if key >= crop.IMPORT_PAGE_BASE:
                self._imports.pop(key, None)
                self.plans.pop(key, None)
            else:
                self._deleted.add(key)
            if key in order:
                order.remove(key)
        self._page_order = order
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        self._save_edits()
        if len(keys) == 1:
            self.status.setText(self.t("page_deleted", label=self._page_label(keys[0]), n=len(self.page_list)))
        else:
            self.status.setText(self.t("pages_deleted", n=len(keys), m=len(self.page_list)))
        self.append_log(self.status.text())
        self._reshow(shown)

    def _restore_pages(self, keys: list[int]) -> None:
        shown = self._current_key()
        order = self._materialize_order()
        for key in keys:
            self._deleted.discard(key)
            if key in self.plans and key not in order:
                order.append(key)
        self._page_order = order
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        self._save_edits()
        self.status.setText(self.t("pages_restored", n=len(keys)))
        self.append_log(self.status.text())
        self._reshow(shown)

    def delete_current_page(self) -> None:
        if self.src is None or self.busy or self._rotate_busy:
            return
        key = self._current_key()
        if key is None:
            return
        self._delete_pages([key])

    # ------------------------------------------------------------ page inserts

    def _next_import_key(self) -> int:
        self._import_counter += 1
        return crop.IMPORT_PAGE_BASE + self._import_counter

    def _blank_size(self) -> tuple[int, int]:
        for key in self._ordered_keys():
            plan = self.plans.get(key)
            if plan is not None:
                return (plan.width, plan.height)
        return (2480, 3507)

    def _quick_insert_pdf(self, index: int) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("ins_pdf_title"), self._last_dir, self.t("pdf_filter"))
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            thumbs = pdf_page_thumbs(Path(path))
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, self.t("app_title"), str(exc))
            return
        QApplication.restoreOverrideCursor()
        if not thumbs:
            return
        picker = PageSelectDialog(
            self,
            sorted(thumbs),
            set(),
            self.t,
            thumbs,
            title=self.t("ins_select_title"),
            hint=self.t("ins_select_hint"),
            spec_field=True,
        )
        if picker.exec() != QDialog.DialogCode.Accepted:
            return
        pages = picker.selected_positions()
        if not pages:
            return
        self._start_insert_request({"type": "pdf", "path": path, "pages": pages, "index": index})

    def _quick_insert_image(self, index: int) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, self.t("ins_image_title"), self._last_dir, self.t("ins_image_filter"))
        if not files:
            return
        box = QMessageBox(self)
        box.setWindowTitle(self.t("ins_enhance_title"))
        box.setText(self.t("ins_enhance_q"))
        check = QCheckBox(self.t("ins_enhance_check"))
        check.setChecked(True)
        box.setCheckBox(check)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        enhanced = box.exec() == QMessageBox.StandardButton.Yes and check.isChecked()
        self._start_insert_request({"type": "image", "files": list(files), "enhanced": enhanced, "index": index})

    def _start_insert_request(self, request: dict) -> None:
        if self.src is None:
            return
        self._pending_requests.append(request)
        self._pump_requests()

    def _pump_requests(self) -> None:
        if self.busy or self._rotate_busy or not self._pending_requests or self.src is None:
            return
        request = self._pending_requests.pop(0)
        if request["type"] == "pdf":
            request["keys"] = [self._next_import_key() for _ in request["pages"]]
        elif request["type"] == "image":
            request["keys"] = [self._next_import_key() for _ in request["files"]]
        elif request["type"] == "dup":
            source = self.plans.get(request["key"])
            if source is None:
                self._pump_requests()
                return
            request["dup_plan"] = replace(source, page=0)
            if request["key"] >= crop.IMPORT_PAGE_BASE:
                request["entry"] = dict(self._imports.get(request["key"]) or {})
            else:
                request["entry"] = {"pdf": str(self.src), "page": int(request["key"])}
            request["keys"] = [self._next_import_key()]
        else:
            request["keys"] = [self._next_import_key()]
            request["size"] = self._blank_size()
        self._set_busy(True, cancellable=False)
        self.status.setText(self.t("ins_progress", i=0, n=len(request["keys"])))
        kwargs = self._analyze_kwargs()
        imports_root = crop.imports_dir_for(self.src)
        render_dpi = int(self.dpi_spin.value())

        def work() -> None:
            try:
                results: list[tuple[crop.PagePlan, dict]] = []
                total = len(request["keys"])
                if request["type"] == "pdf":
                    failures: list[tuple[int, str]] = []
                    for key, page_num in zip(request["keys"], request["pages"]):
                        base = imports_root / f"import-{key}.jpg"
                        try:
                            crop.extract_single_page(Path(request["path"]), int(page_num), base, render_dpi)
                            plan = crop.analyze_one_page(
                                base, key,
                                kwargs["min_width_ratio"], kwargs["min_height_ratio"],
                                kwargs["min_full_width_ratio"], kwargs["min_full_height_ratio"],
                                None, 0.0, kwargs["crop_mode"], True,
                            )
                            plan.note = f"import+{plan.note}"
                            results.append((plan, {"pdf": request["path"], "page": int(page_num)}))
                            self.events.put(("progress", self.t("ins_progress", i=len(results), n=total), len(results), total))
                        except Exception as exc:
                            # One bad page number must not discard the pages that worked.
                            failures.append((int(page_num), str(exc)))
                    if failures:
                        request["failures"] = failures
                        if not results:
                            raise RuntimeError(failures[0][1])
                elif request["type"] == "image":
                    for key, file in zip(request["keys"], request["files"]):
                        base = imports_root / f"import-{key}.jpg"
                        with Image.open(file) as im:
                            rgb = im if im.mode == "RGB" else im.convert("RGB")
                            if request.get("enhanced"):
                                rgb = crop.enhance_scan_image(rgb)
                            base.parent.mkdir(parents=True, exist_ok=True)
                            rgb.save(base, format="JPEG", quality=92, subsampling=0)
                        plan = crop.analyze_one_page(
                            base, key,
                            kwargs["min_width_ratio"], kwargs["min_height_ratio"],
                            kwargs["min_full_width_ratio"], kwargs["min_full_height_ratio"],
                            None, 0.0, kwargs["crop_mode"], True,
                        )
                        plan.note = f"import+{plan.note}"
                        results.append((plan, {"image": str(file), "enhanced": bool(request.get("enhanced"))}))
                        self.events.put(("progress", self.t("ins_progress", i=len(results), n=total), len(results), total))
                elif request["type"] == "blank":
                    key = request["keys"][0]
                    width, height = request["size"]
                    base = imports_root / f"import-{key}.jpg"
                    base.parent.mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", (width, height), (255, 255, 255)).save(base, format="JPEG", quality=92, subsampling=0)
                    box = crop.clamp_crop((0, 0, width, height), width, height)
                    plan = crop.PagePlan(
                        page=key, path=base, source_path=base, width=width, height=height,
                        mode="RGB", crop=box, safe=box, note="import+blank", rotate_deg=0.0,
                    )
                    results.append((plan, {"blank": [width, height]}))
                    self.events.put(("progress", self.t("ins_progress", i=1, n=1), 1, 1))
                else:  # duplicate: give the copy its own base image so it can be
                    # rotated and re-analyzed independently of the original page.
                    key = request["keys"][0]
                    source_plan = request["dup_plan"]
                    base = imports_root / f"import-{key}.jpg"
                    base.parent.mkdir(parents=True, exist_ok=True)
                    base.write_bytes(Path(source_plan.source_path).read_bytes())
                    plan = replace(source_plan, page=key, path=base, source_path=base)
                    plan.note = (plan.note or "") + "+duplicate"
                    results.append((plan, dict(request["entry"])))
                    self.events.put(("progress", self.t("ins_progress", i=1, n=1), 1, 1))
                self.events.put(("import-done", results, request))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _on_import_done(self, results: list, request: dict) -> None:
        try:
            self._apply_import_results(results, request)
        except Exception:
            self.append_log(traceback.format_exc())
            QMessageBox.critical(self, self.t("app_title"), self.t("import_failed", exc="—"))

    def _apply_import_results(self, results: list, request: dict) -> None:
        self._set_busy(False)
        for plan, entry in results:
            self.plans[plan.page] = plan
            self._imports[plan.page] = entry
        if self._uniform is not None:
            self.apply_uniform(self._uniform)
        new_keys = set(request["keys"])
        # A fresh natural order already contains the new keys at their sorted spot;
        # drop them so the requested index is the only place they appear.
        order = [key for key in self._materialize_order() if key not in new_keys]
        index = max(0, min(int(request.get("index", len(order))), len(order)))
        order[index:index] = list(request["keys"])
        self._page_order = order
        self.page_list = self._ordered_keys()
        self._sync_page_spin_range()
        self._refresh_table()
        self._save_edits()
        kind = request["type"]
        if kind == "pdf":
            source = Path(request["path"]).name
        elif kind == "image":
            source = self.t("import_src_image", n=len(request["files"]))
        elif kind == "blank":
            source = self.t("import_src_blank")
        else:
            source = self.t("import_src_dup")
        message = self.t("import_done", n=len(results), src=source)
        failures = request.get("failures") or []
        if failures:
            pages_text = ", ".join(str(page) for page, _exc in failures)
            message = self.t("import_done_partial", n=len(results), src=source, pages=pages_text)
        self.status.setText(message)
        self.append_log(message)
        self.append_log(self.t("list_updated", n=len(self.page_list), page=self._page_label(request["keys"][0])))
        self.table.viewport().update()
        for page, exc in failures:
            self.append_log(self.t("import_page_failed", page=page, exc=exc))
        if request["keys"]:
            pos = self._pos_of(request["keys"][0])
            if pos:
                self.goto_page(pos)
        self._pump_requests()

    # ------------------------------------------------------- import persistence

    def _build_import_plan(self, key: int, entry: dict) -> crop.PagePlan:
        root = crop.imports_dir_for(self.src)
        base = root / f"import-{key}.jpg"
        if "blank" in entry:
            width, height = (int(value) for value in entry["blank"])
            if not base.is_file():
                base.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (width, height), (255, 255, 255)).save(base, format="JPEG", quality=92, subsampling=0)
            note = str(entry.get("note") or "import+blank")
        else:
            if not base.is_file():
                base.parent.mkdir(parents=True, exist_ok=True)
                if entry.get("image"):
                    with Image.open(entry["image"]) as im:
                        rgb = im if im.mode == "RGB" else im.convert("RGB")
                        if entry.get("enhanced"):
                            rgb = crop.enhance_scan_image(rgb)
                        rgb.save(base, format="JPEG", quality=92, subsampling=0)
                elif entry.get("pdf"):
                    crop.extract_single_page(Path(entry["pdf"]), int(entry.get("page", 1)), base, int(self.dpi_spin.value()))
                else:
                    raise FileNotFoundError(str(base))
            note = str(entry.get("note") or "import")
        angle = float(entry.get("rotate", 0.0) or 0.0)
        path = base
        if abs(angle) > 1e-6:
            path = crop.rotate_image_file(base, base.with_name(f"{base.stem}_rot.jpg"), angle)
        with Image.open(path) as im:
            width, height = im.size
            mode = im.mode
        box = tuple(int(value) for value in entry.get("crop", (0, 0, width, height)))
        box = crop.clamp_crop(box, width, height)
        return crop.PagePlan(
            page=key, path=path, source_path=base, width=width, height=height, mode=mode,
            crop=box, safe=box, note=note, rotate_deg=angle,
        )

    def _rebuild_imports(self) -> None:
        for key in sorted(self._imports):
            try:
                self.plans[key] = self._build_import_plan(key, self._imports[key])
            except Exception as exc:
                # Never drop the record: a locked or moved source must not wipe
                # the user's inserted pages. Keep a visible placeholder instead.
                self.append_log(self.t("import_missing", label=self._page_label(key), exc=exc))
                self.append_log(traceback.format_exc())
                self.plans[key] = self._missing_import_plan(key)
        self._log_orphan_imports()

    def _missing_import_plan(self, key: int) -> crop.PagePlan:
        root = crop.imports_dir_for(self.src)
        root.mkdir(parents=True, exist_ok=True)
        base = root / f"import-{key}.jpg"
        if not base.is_file():
            Image.new("RGB", (1240, 1754), "white").save(base, format="JPEG", quality=90)
        with Image.open(base) as im:
            width, height = im.size
        return crop.PagePlan(
            page=key, path=base, source_path=base, width=width, height=height, mode="RGB",
            crop=(0, 0, width, height), safe=(0, 0, width, height),
            note="import+missing", rotate_deg=0.0,
        )

    def _log_orphan_imports(self) -> None:
        if self.src is None:
            return
        root = crop.imports_dir_for(self.src)
        if not root.is_dir():
            return
        known = {f"import-{key}.jpg" for key in self._imports}
        orphans = sorted(
            path.name for path in root.glob("import-*.jpg")
            if path.name not in known and not path.stem.endswith("_rot")
        )
        if orphans:
            self.append_log(self.t("import_orphans", n=len(orphans), names=", ".join(orphans[:6])))

    # ------------------------------------------------------------ merged export

    def _start_merge_export(self, job: crop.CropJob) -> None:
        if self.busy:
            return
        if job.src.resolve() == job.output.resolve():
            QMessageBox.critical(self, self.t("app_title"), self.t("same_path"))
            return
        job.write_pdf = False
        output_order = self._ordered_output_keys()
        analyze_pages = sorted(
            key for key in output_order if key < crop.IMPORT_PAGE_BASE
        )
        self._set_busy(True)
        self.cancel.clear()
        self.append_log(self.t("write_preview", name=job.output.name))

        def work() -> None:
            try:
                def progress(message: str, current: int, total: int) -> None:
                    crop.check_cancelled(self.cancel)
                    self.events.put(("progress", message, current, total))

                # Only the pages that survive the arrangement and the selection
                # need analysis; with inserts alone there is nothing to render.
                if analyze_pages:
                    job.pages = analyze_pages
                    source_plans = crop.execute_job(job, progress=progress, cancel=self.cancel)
                else:
                    source_plans = []
                fresh = {plan.page: plan for plan in source_plans}
                by_key = {
                    key: plan for key, plan in self.plans.items() if key >= crop.IMPORT_PAGE_BASE
                }
                by_key.update(fresh)
                plans = [by_key[key] for key in output_order if key in by_key]
                crop.write_pdf_from_plans(plans, job.output, progress, self.cancel, source=job.src)
                if job.ocr:
                    crop.apply_ocr_to_pdf(
                        job.output,
                        plans,
                        job.ocr_lang,
                        progress,
                        self.cancel,
                        job.jobs,
                        write_txt=job.ocr_txt,
                        ref_pdf=job.ocr_ref or crop.find_text_companion(job.src),
                    )
                if job.inspect_pages and job.inspect_dir is not None:
                    output_index = {plan.page: i + 1 for i, plan in enumerate(plans)}
                    pdf_pages = [output_index[page] for page in job.inspect_pages if page in output_index]
                    labels = [page for page in job.inspect_pages if page in output_index]
                    crop.render_inspection_pages(
                        job.output, pdf_pages, job.inspect_dir, job.src.parent, job.inspect_dpi, labels
                    )
                self.events.put(("done", plans, job, True))
            except crop.CancelledError:
                self.events.put(("cancelled",))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".pdf" and path.is_file():
                self.set_input(path)
                break

    def _sync_table_selection(self) -> None:
        """Keep the results table on the page the crop view is showing."""
        if not hasattr(self, "table") or not self.page_list or self.table.rowCount() == 0:
            return
        row = self.current_page - 1
        if not 0 <= row < self.table.rowCount():
            return
        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)
        item = self.table.item(row, 0)
        if item is not None:
            self.table.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)

    def _refresh_table(self) -> None:
        pages = self.page_list or sorted(self.plans)
        self.table.blockSignals(True)
        self.table.setRowCount(len(pages))
        for row, page in enumerate(pages):
            plan = self.plans.get(page)
            if plan is None:
                self.table.setItem(row, 0, self._page_item(page))
                self.table.setItem(row, 1, QTableWidgetItem(self.t("not_analyzed")))
                self.table.setItem(row, 2, QTableWidgetItem("-"))
                continue
            box = f"{plan.crop[0]},{plan.crop[1]},{plan.crop[2]},{plan.crop[3]}"
            self.table.setItem(row, 0, self._page_item(page))
            self.table.setItem(row, 1, QTableWidgetItem(plan.note))
            self.table.setItem(row, 2, QTableWidgetItem(box))
        self.table.blockSignals(False)
        self._sync_table_selection()

    def _update_table_row(self, page: int) -> None:
        plan = self.plans.get(page)
        if plan is None:
            return
        pages = self.page_list or self._ordered_keys()
        try:
            row = pages.index(page)
        except ValueError:
            self._refresh_table()
            return
        box = f"{plan.crop[0]},{plan.crop[1]},{plan.crop[2]},{plan.crop[3]}"
        self.table.blockSignals(True)
        if self.table.rowCount() != len(pages):
            self.table.blockSignals(False)
            self._refresh_table()
            return
        self.table.setItem(row, 0, self._page_item(page))
        self.table.setItem(row, 1, QTableWidgetItem(plan.note))
        self.table.setItem(row, 2, QTableWidgetItem(box))
        self.table.blockSignals(False)

    def _read_job(self, write_pdf: bool) -> crop.CropJob:
        if not self.input_edit.text().strip():
            raise RuntimeError(self.t("need_src"))
        src = Path(self.input_edit.text().strip())
        output = Path(self.output_edit.text().strip() or crop.default_output_for(src))
        work = Path(self.work_edit.text().strip() or crop.default_work_dir_for(src))
        selected = self._selected_source_pages()
        pages = sorted(selected) if selected else None
        inspect_spec = crop.parse_page_spec(self.inspect_edit.text())
        inspect_keys = self._ordered_output_keys()
        inspect_pages = [
            inspect_keys[pos - 1]
            for pos in inspect_spec
            if 1 <= pos <= len(inspect_keys) and inspect_keys[pos - 1] < crop.IMPORT_PAGE_BASE
        ]
        inspect_dir = output.with_name(output.stem + "_检查图") if inspect_pages else None
        # Saved edits plus the current page states; auto-deskew angles are re-estimated, not pinned.
        manual, rotates = self._current_edits()
        return crop.CropJob(
            src=src,
            output=output,
            work=work,
            report=None,
            reuse=self.reuse_box.isChecked(),
            min_width_ratio=self._ratio(self.min_page[1]),
            min_height_ratio=self._ratio(self.min_page[1]),
            min_full_width_ratio=self._ratio(self.min_full[1]),
            min_full_height_ratio=self._ratio(self.min_full[1]),
            manual_crops=manual,
            page_rotates=rotates,
            uniform_margins=self._uniform,
            pages=pages,
            inspect_pages=inspect_pages,
            inspect_dir=inspect_dir,
            inspect_dpi=140,
            jobs=int(self.jobs_spin.value()),
            render_dpi=int(self.dpi_spin.value()),
            write_pdf=write_pdf,
            crop_mode=self._crop_mode(),
            auto_rotate=self.auto_rotate_box.isChecked(),
            ocr=self.ocr_box.isChecked(),
            ocr_txt=self.ocr_box.isChecked() and self.ocr_txt_box.isChecked(),
            ocr_ref=crop.find_text_companion(src),
        )

    def ocr_current_page(self) -> None:
        if self.busy:
            return
        key = self._current_key()
        if key not in self.plans:
            QMessageBox.information(self, self.t("app_title"), self.t("need_analyze_ocr"))
            return
        if not crop.ocr_available():
            QMessageBox.warning(self, self.t("app_title"), self._ocr_missing())
            return
        plan = self.plans[key]
        ref = crop.find_text_companion(self.src) if self.src is not None else None
        if ref is not None:
            self.append_log(self.t("used_ref", name=ref.name))
        self._set_busy(True, cancellable=False)
        self.status.setText(self.t("ocr_page_running", page=self._page_label(plan.page)))

        def work() -> None:
            # Several Tesseract runs take seconds; keep them off the UI thread.
            tmp = plan.path.with_name(f"{plan.path.stem}_ocr_preview.jpg")
            try:
                words_path = None
                if ref is not None:
                    words_path = crop.build_user_words(ref, plan.path.with_name("_ocr_user_words.txt"))
                text, _image, _tsv = crop.ocr_plan_image(plan, tmp, user_words=words_path)
                self.events.put(("ocr-page-done", plan.page, text))
            except Exception as exc:
                self.events.put(("ocr-page-failed", str(exc)))
            finally:
                tmp.unlink(missing_ok=True)

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _show_ocr_page(self, page: int, text: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("ocr_page_title", page=self._page_label(page)))
        dialog.resize(640, 520)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text or self.t("ocr_empty"))
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def start_ocr_book(self) -> None:
        if not crop.ocr_available():
            QMessageBox.warning(self, self.t("app_title"), self._ocr_missing())
            return
        output_text = self.output_edit.text().strip()
        output = Path(output_text) if output_text else None
        if self.plans:
            try:
                job = self._read_job(write_pdf=True)
            except Exception as exc:
                QMessageBox.critical(self, self.t("app_title"), str(exc))
                return
            job.ocr = True
            job.ocr_ref = crop.find_text_companion(job.src)
            if job.ocr_ref is not None:
                self.append_log(self.t("ocr_book_ref", name=job.ocr_ref.name))
            self._start_write_only(job)
            return
        if output is not None and output.is_file():
            self._start_ocr_existing(output)
            return
        QMessageBox.information(
            self,
            self.t("app_title"),
            self.t("need_analyze_or_out"),
        )

    def _start_ocr_existing(self, output: Path) -> None:
        if self.busy:
            return
        if not crop.ocr_available():
            QMessageBox.warning(self, self.t("app_title"), self._ocr_missing())
            return
        self._set_busy(True)
        self.cancel.clear()
        ref = crop.find_text_companion(output)
        if ref is not None:
            self.append_log(self.t("ocr_existing_ref", name=ref.name))
        else:
            self.append_log(self.t("ocr_existing", name=output.name))

        def work() -> None:
            try:
                def progress(message: str, current: int, total: int) -> None:
                    crop.check_cancelled(self.cancel)
                    self.events.put(("progress", message, current, total))

                crop.apply_ocr_to_existing_pdf(
                    output,
                    progress=progress,
                    cancel=self.cancel,
                    jobs=self.jobs_spin.value(),
                    write_txt=self.ocr_txt_box.isChecked(),
                    ref_pdf=ref,
                )
                self.events.put(("ocr-existing-done", output))
            except crop.CancelledError:
                self.events.put(("cancelled",))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def start_analyze(self) -> None:
        selected = self._selected_source_pages()
        if selected is not None and not selected:
            self.status.setText(self.t("pages_filter_empty"))
            return
        self._start_job(write_pdf=False, title=self.t("analyze"))

    def start_generate(self) -> None:
        output_keys = self._ordered_output_keys()
        if self.src is not None and not output_keys:
            QMessageBox.information(self, self.t("app_title"), self.t("no_output_pages"))
            return
        missing = [key for key in output_keys if key not in self.plans]
        if self.plans and not missing:
            # Every page in the arranged output already has a plan: write directly.
            try:
                job = self._read_job(write_pdf=True)
            except Exception as exc:
                QMessageBox.critical(self, self.t("app_title"), str(exc))
                return
            self._start_write_only(job)
            return
        arranged = bool(
            self._page_order is not None
            or self._deleted
            or self._imports
            or missing
            or self._pages_filter() is not None
        )
        if self.plans or arranged:
            # Some output pages are not analyzed yet (or only inserts exist):
            # process the source, then merge everything in the arranged order.
            try:
                job = self._read_job(write_pdf=True)
            except Exception as exc:
                QMessageBox.critical(self, self.t("app_title"), str(exc))
                return
            self._start_merge_export(job)
            return
        self._start_job(write_pdf=True, title=self.t("generate"))

    def _start_write_only(self, job: crop.CropJob) -> None:
        if self.busy:
            return
        if job.src.resolve() == job.output.resolve():
            QMessageBox.critical(self, self.t("app_title"), self.t("same_path"))
            return
        plans = [self.plans[page] for page in self._ordered_output_keys()]
        self._set_busy(True)
        self.cancel.clear()
        self.append_log(self.t("write_preview", name=job.output.name))

        def work() -> None:
            try:
                def progress(message: str, current: int, total: int) -> None:
                    crop.check_cancelled(self.cancel)
                    self.events.put(("progress", message, current, total))

                crop.write_pdf_from_plans(plans, job.output, progress, self.cancel, source=job.src)
                if job.ocr:
                    crop.apply_ocr_to_pdf(
                        job.output,
                        plans,
                        job.ocr_lang,
                        progress,
                        self.cancel,
                        job.jobs,
                        write_txt=job.ocr_txt,
                        ref_pdf=job.ocr_ref or crop.find_text_companion(job.src),
                    )
                if job.inspect_pages and job.inspect_dir is not None:
                    output_index = {plan.page: i + 1 for i, plan in enumerate(plans)}
                    pdf_pages = [output_index[page] for page in job.inspect_pages if page in output_index]
                    labels = [page for page in job.inspect_pages if page in output_index]
                    crop.render_inspection_pages(
                        job.output, pdf_pages, job.inspect_dir, job.src.parent, job.inspect_dpi, labels
                    )
                self.events.put(("done", plans, job, True))
            except crop.CancelledError:
                self.events.put(("cancelled",))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _start_job(self, write_pdf: bool, title: str) -> None:
        if self.busy:
            return
        try:
            job = self._read_job(write_pdf)
        except Exception as exc:
            QMessageBox.critical(self, self.t("app_title"), str(exc))
            return
        if not job.src.is_file():
            QMessageBox.critical(self, self.t("app_title"), self.t("missing_src"))
            return
        if job.src.resolve() == job.output.resolve():
            QMessageBox.critical(self, self.t("app_title"), self.t("same_path"))
            return
        self._set_busy(True)
        self.cancel.clear()
        self._preview_cache.clear()
        self.append_log(self.t("start_job", title=title, name=job.src.name))

        def work() -> None:
            try:
                def progress(message: str, current: int, total: int) -> None:
                    crop.check_cancelled(self.cancel)
                    self.events.put(("progress", message, current, total))

                plans = crop.execute_job(job, progress=progress, cancel=self.cancel)
                self.events.put(("done", plans, job, write_pdf))
            except crop.CancelledError:
                self.events.put(("cancelled",))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def request_cancel(self) -> None:
        if self.busy:
            self.cancel.set()
            self.status.setText(self.t("cancelling"))
            self.append_log(self.t("cancel_log"))

    def _set_busy(self, busy: bool, cancellable: bool = True) -> None:
        self.busy = busy
        for button in (
            self.analyze_btn,
            self.keep_all_btn,
            self.uniform_btn,
            self.organize_btn,
            self.rotate_all_ccw_btn,
            self.rotate_all_cw_btn,
            self.generate_btn,
            self.keep_page_btn,
            self.reset_btn,
            self.del_page_btn,
            self.page_ccw_btn,
            self.page_cw_btn,
            self.clear_cache_btn,
            self.forget_edits_btn,
        ):
            button.setEnabled(not busy)
        for button in (self.ocr_page_btn, self.ocr_book_btn):
            button.setEnabled(not busy and self._ocr_ok)
        if hasattr(self, "fs_keep_page_btn"):
            self.fs_keep_page_btn.setEnabled(not busy)
            self.fs_reset_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy and cancellable)

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, message, current, total = event
                    shown = self.localize_engine(message)
                    self.status.setText(shown)
                    if total > 0:
                        self.progress.setMaximum(total)
                        self.progress.setValue(current)
                    self.append_log(shown)
                elif kind == "done":
                    _, plans, job, wrote = event
                    self._on_done(plans, job, wrote)
                elif kind == "ocr-existing-done":
                    output = event[1]
                    self._set_busy(False)
                    self.last_output = output
                    self.status.setText(self.t("ocr_layer_done", name=output.name))
                    self.append_log(self.t("ocr_layer_log", path=output))
                    if self.open_after_box.isChecked():
                        try:
                            open_path(output)
                        except Exception as exc:
                            self.append_log(self.t("open_fail", exc=exc))
                elif kind == "rotated":
                    self._on_rotated(event[1], event[2])
                elif kind == "rotate-all-imports":
                    for plan, entry in event[1]:
                        self.plans[plan.page] = plan
                        self._imports[plan.page] = entry
                elif kind == "rotate-all-finished":
                    _, direction = event
                    self._set_busy(False)
                    self._refresh_table()
                    self._save_edits()
                    if self.page_list:
                        self.goto_page(min(self.current_page, len(self.page_list)))
                    message = self.t("rotate_all_done_no_plans", dir=direction)
                    self.status.setText(message)
                    self.append_log(message)
                elif kind == "import-done":
                    self._on_import_done(event[1], event[2])
                elif kind == "ocr-page-done":
                    _, page, text = event
                    self._set_busy(False)
                    label = self._page_label(page)
                    self.status.setText(self.t("ocr_page_done", page=label, n=len(text)))
                    self.append_log(self.t("ocr_page_done", page=label, n=len(text)))
                    # Open the dialog after this drain pass so its event loop does not nest in it.
                    QTimer.singleShot(0, lambda page=page, text=text: self._show_ocr_page(page, text))
                elif kind == "ocr-page-failed":
                    self._set_busy(False)
                    self.status.setText(self.t("failed"))
                    QMessageBox.critical(self, self.t("app_title"), self.t("ocr_fail", exc=event[1]))
                elif kind == "error":
                    self._set_busy(False)
                    self._rotate_busy = False
                    self.status.setText(self.t("failed"))
                    self.append_log(event[1])
                    QMessageBox.critical(self, self.t("app_title"), self.t("job_failed"))
                elif kind == "cancelled":
                    self._set_busy(False)
                    self.status.setText(self.t("cancelled"))
                    self.append_log(self.t("cancelled"))
        except queue.Empty:
            return

    def _on_rotated(self, updated: crop.PagePlan, reset: bool = False) -> None:
        self._rotate_busy = False
        self.plans[updated.page] = updated
        self._preview_cache.pop(str(updated.path), None)
        if updated.source_path != updated.path:
            self._preview_cache.pop(str(updated.source_path), None)
        if self._current_key() == updated.page:
            self.show_plan(updated.page)
        self._refresh_table()
        self._save_edits()
        if reset:
            label = self._page_label(updated.page)
            self.status.setText(self.t("reset_done", page=label))
            self.append_log(self.t("reset_done", page=label))
        else:
            label = self._page_label(updated.page)
            self.status.setText(self.t("rotated", page=label, angle=updated.rotate_deg))
            self.append_log(
                self.t("rotated_log", page=label, angle=updated.rotate_deg, note=updated.note)
            )
        if self._rotate_pending is not None:
            pending = self._rotate_pending
            self._rotate_pending = None
            self._rotate_commit(pending)

    def _on_done(self, plans: list[crop.PagePlan], job: crop.CropJob, wrote: bool) -> None:
        self._set_busy(False)
        fresh = {plan.page: plan for plan in plans}
        # Keep pages the finished job did not touch: inserted pages, deleted-but-restorable
        # pages, and pages outside an analyze subset all survive here.
        kept = {key: plan for key, plan in self.plans.items() if key not in fresh}
        self.plans = {**kept, **fresh}
        self.page_list = self._ordered_keys()
        self.pdf_pages = max(
            self.pdf_pages, max((key for key in self.page_list if key < crop.IMPORT_PAGE_BASE), default=1)
        )
        self._sync_page_spin_range()
        self._refresh_table()
        if self._uniform is not None:
            if any("uniform" not in plan.note for plan in self.plans.values()):
                self.apply_uniform(self._uniform)
            else:
                # Fast path: the engine already applied the margins; a full page is the
                # pre-uniform base for pages without hand-drawn boxes.
                for plan in self.plans.values():
                    if plan.page in self._uniform_base:
                        continue
                    if "+manual" in plan.note:
                        base_box = tuple(plan.crop)
                    else:
                        base_box = (0, 0, plan.width, plan.height)
                    self._uniform_base[plan.page] = (base_box, plan.note)
        self._save_edits()
        if self.page_list:
            self.goto_page(min(self.current_page, len(self.page_list)))
        if wrote:
            self.last_output = job.output
            self.status.setText(self.t("generated", name=job.output.name, n=len(plans)))
            if job.ocr:
                self.append_log(self.t("generated_ocr", path=job.output))
            else:
                self.append_log(self.t("generated_no_ocr", path=job.output))
            if self.open_after_box.isChecked():
                try:
                    open_path(job.output)
                except Exception as exc:
                    self.append_log(self.t("open_fail", exc=exc))
        else:
            self.status.setText(self.t("analyzed", n=len(plans)))
            self.append_log(self.t("analyzed_log", n=len(plans)))

    def open_output(self) -> None:
        target = self.last_output or (Path(self.output_edit.text()) if self.output_edit.text() else None)
        if target is None or not Path(target).exists():
            QMessageBox.information(self, self.t("app_title"), self.t("no_result"))
            return
        open_path(Path(target))

    def open_folder(self) -> None:
        target = self.last_output or (Path(self.output_edit.text()) if self.output_edit.text() else None)
        if target is None:
            if self.src is not None:
                open_path(self.src.parent)
            return
        path = Path(target)
        open_path(path.parent if path.is_file() else path)

    def closeEvent(self, event) -> None:
        if self.busy:
            answer = QMessageBox.question(self, self.t("app_title"), self.t("busy_quit"))
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.cancel.set()
        self._save_settings()
        event.accept()


def apply_style(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    ink = QColor("#1E293B")
    paper = QColor("#FFFFFF")
    page = QColor("#E8EDF3")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, page)
    palette.setColor(QPalette.ColorRole.WindowText, ink)
    palette.setColor(QPalette.ColorRole.Base, paper)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Text, ink)
    palette.setColor(QPalette.ColorRole.Button, QColor("#F1F5F9"))
    palette.setColor(QPalette.ColorRole.ButtonText, ink)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#64748B"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1D4E89"))
    palette.setColor(QPalette.ColorRole.HighlightedText, paper)
    palette.setColor(QPalette.ColorRole.ToolTipBase, paper)
    palette.setColor(QPalette.ColorRole.ToolTipText, ink)
    app.setPalette(palette)
    app.setStyleSheet(
        """
        QMainWindow { background: #E8EDF3; color: #1E293B; }
        QLabel, QCheckBox, QGroupBox, QRadioButton { color: #1E293B; }
        QFrame#header { background-color: #0B1F33; }
        QFrame#header QLabel { background-color: #0B1F33; color: #FFFFFF; }
        QLabel#title { color: #FFFFFF; background-color: #0B1F33; font-size: 20px; font-weight: 700; }
        QLabel#subtitle { color: #E2E8F0; background-color: #0B1F33; }
        QFrame#card { background: #FFFFFF; color: #1E293B; }
        QFrame#card QLabel, QFrame#card QCheckBox, QFrame#card QGroupBox { color: #1E293B; background: transparent; }
        QFrame#footer { background: #E8EDF3; padding: 8px 12px; color: #1E293B; }
        QFrame#footer QLabel { color: #1E293B; background: transparent; }
        QLabel#section { color: #0B1F33; font-weight: 700; margin-top: 8px; }
        QPushButton { padding: 6px 10px; color: #1E293B; }
        QPushButton#primary { background: #0B1F33; color: #FFFFFF; font-weight: 700; padding: 8px; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTableWidget {
            background: #FFFFFF; color: #1E293B; }
        QProgressBar { border: 1px solid #CBD5E1; height: 16px; text-align: center; color: #1E293B; }
        QProgressBar::chunk { background: #1D4E89; }
        QSplitter#previewSplit::handle:vertical {
            background: #94A3B8;
            margin: 4px 80px;
            border-radius: 3px;
            height: 6px;
        }
        QSplitter#previewSplit::handle:vertical:hover { background: #1D4E89; }
        QWidget#fsBar { background: #0B1F33; }
        QWidget#fsBar QLabel { color: #E2E8F0; background: transparent; }
        QWidget#fsBar QPushButton { color: #FFFFFF; background: #1D4E89; padding: 6px 10px; }
        QWidget#fsBar QDoubleSpinBox { background: #FFFFFF; color: #1E293B; min-width: 88px; }
        """
    )


def run_self_test(report: Path) -> int:
    """Headless check of a packaged build: Qt window, PyMuPDF, crop engine, OCR and font subsetting."""
    import tempfile

    from PIL import ImageDraw, ImageFont

    lines: list[str] = []
    passed = True

    def step(name: str, func) -> None:
        nonlocal passed
        try:
            detail = func()
            lines.append(f"PASS {name} {detail}".rstrip())
        except Exception:
            passed = False
            lines.append(f"FAIL {name}\n{traceback.format_exc()}")

    with tempfile.TemporaryDirectory(prefix="pdfcrop_selftest_") as tmp:
        base = Path(tmp)
        src = base / "sample.pdf"
        out = base / "sample_裁边.pdf"

        def make_sample() -> str:
            image = Image.new("RGB", (1240, 1754), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 36, 1754), fill=(25, 25, 25))
            font_file = Path(r"C:\Windows\Fonts\msyh.ttc")
            font = ImageFont.truetype(str(font_file), 40) if font_file.is_file() else ImageFont.load_default()
            for row in range(12):
                draw.text((150, 200 + row * 90), f"扫描裁边自检 PDF crop self-test 第 {row + 1} 行", font=font, fill="black")
            jpeg = base / "page.jpg"
            image.save(jpeg, quality=90)
            doc = crop.fitz.open()
            doc.new_page(width=595, height=842).insert_image(crop.fitz.Rect(0, 0, 595, 842), filename=str(jpeg))
            doc.set_toc([[1, "自检", 1]])
            doc.save(src)
            doc.close()
            return ""

        def open_window() -> str:
            # Never closed: closing would save this throwaway window's settings over the user's.
            window = PdfCropWindow()
            window.set_input(src)
            return f"pages={window.pdf_pages}"

        def export() -> str:
            job = crop.CropJob(
                src=src, output=out, work=base / "work", reuse=False, jobs=2, render_dpi=150, ocr=crop.ocr_available()
            )
            plans = crop.execute_job(job)
            with crop.fitz.open(out) as doc:
                text = doc[0].get_text().strip()
                fonts = [entry[3] for entry in doc.get_page_fonts(0)]
                toc = doc.get_toc()
            return (
                f"crop={plans[0].crop} note={plans[0].note} toc={toc} ocr={crop.ocr_available()} "
                f"text_chars={len(text)} fonts={fonts} bytes={out.stat().st_size}"
            )

        def uniform_fast_path() -> str:
            # No-analysis fast path: uniform margins + a pinned 90-degree rotation.
            out2 = base / "sample_统一.pdf"
            job = crop.CropJob(
                src=src, output=out2, work=base / "work2", reuse=False, jobs=2, render_dpi=150,
                uniform_margins=(0.0, 0.0, 0.0, 2.0), page_rotates={1: 90.0},
            )
            plans = crop.execute_job(job)
            plan = plans[0]
            assert plan.rotate_deg == 90.0 and plan.width > plan.height, (plan.rotate_deg, plan.width, plan.height)
            expect_bottom = plan.height - round(2.0 * plan.height / crop.CM_PER_PAGE_HEIGHT)
            assert abs(plan.crop[3] - expect_bottom) <= 1, (plan.crop, expect_bottom)
            assert "uniform" in plan.note, plan.note
            with crop.fitz.open(out2) as doc:
                out_height = doc[0].rect.height
            expected_pt = 841.89 * (plan.height - round(2.0 * plan.height / crop.CM_PER_PAGE_HEIGHT)) / plan.height
            assert abs(out_height - expected_pt) < 1.5, (out_height, expected_pt)
            # Inserting a page from another PDF and scanner-style enhancement.
            marker = base / "uni_p.jpg"
            Image.new("RGB", (1200, 1600), "white").save(marker, quality=90)
            other = base / "other.pdf"
            doc2 = crop.fitz.open()
            doc2.new_page(width=595, height=842).insert_image(crop.fitz.Rect(0, 0, 595, 842), filename=str(marker))
            doc2.save(other)
            doc2.close()
            dest = base / "import-1000001.jpg"
            crop.extract_single_page(other, 1, dest, 150)
            plan2 = crop.analyze_one_page(dest, 1000001, 0.86, 0.86, 0.90, 0.90, None, 0.0, "edges", True)
            assert plan2.width > 0 and 0 <= plan2.crop[3] <= plan2.height, (plan2.width, plan2.crop)
            paper = Image.new("RGB", (300, 300), (205, 206, 204))
            boosted = crop.enhance_scan_image(paper)
            assert boosted.getpixel((10, 10))[0] >= 245, boosted.getpixel((10, 10))
            dark = Image.new("RGB", (300, 300), (40, 41, 39))
            untouched = crop.enhance_scan_image(dark)
            assert untouched.getpixel((10, 10))[0] <= 45, untouched.getpixel((10, 10))
            return f"crop={plan.crop} expect_bottom={expect_bottom} out_h={out_height:.1f} import_crop={plan2.crop}"

        def organize_without_analysis() -> str:
            # The organizer, thumbnails, the pages filter and order navigation
            # must all work before any analysis has run.
            import time as _time

            three = base / "three.pdf"
            doc3 = crop.fitz.open()
            for i in range(3):
                page_img = Image.new("RGB", (900, 1272), (250, 250, 250))
                draw3 = ImageDraw.Draw(page_img)
                draw3.rectangle((60 + i * 40, 60, 200 + i * 40, 300), fill=(30, 30, 30))
                peg = base / ("three_%d.jpg" % i)
                page_img.save(peg, quality=90)
                doc3.new_page(width=595, height=842).insert_image(crop.fitz.Rect(0, 0, 595, 842), filename=str(peg))
            doc3.save(three)
            doc3.close()
            window = PdfCropWindow()
            window.set_input(three)
            assert window.page_list == [1, 2, 3] and not window.plans, window.page_list
            thumbs = window._thumb_pixmaps([1, 2, 3])
            assert len(thumbs) == 3 and all(p.width() > 0 for p in thumbs.values()), len(thumbs)
            window._apply_order([3, 1], [2])
            assert window.page_list == [3, 1] and 2 in window._deleted, (window.page_list, window._deleted)
            window._apply_order([1, 2, 3], [])
            assert window.page_list == [1, 2, 3] and not window._deleted, window.page_list
            window.pages_edit.setText("2")
            window._pages_filter_changed()
            window.pages_edit.setText("2-3")
            window._pages_filter_changed()
            assert len(window._ordered_output_keys()) == 2, window._ordered_output_keys()
            window.pages_edit.clear()
            window._pages_filter_changed()
            assert len(window._ordered_output_keys()) == 3, window._ordered_output_keys()
            window._start_insert_request({"type": "blank", "index": 3})
            deadline = _time.time() + 30
            while _time.time() < deadline and (window.busy or window._pending_requests):
                QApplication.processEvents()
                _time.sleep(0.02)
            QApplication.processEvents()
            assert window.page_list == [1, 2, 3, crop.IMPORT_PAGE_BASE + 1], window.page_list
            assert window.page_spin.maximum() == 4, window.page_spin.maximum()
            expected = window.t("page_label", page=4)
            assert window._page_label(crop.IMPORT_PAGE_BASE + 1) == expected, window._page_label(crop.IMPORT_PAGE_BASE + 1)
            window.goto_page(4)
            assert window.current_page == 4, window.current_page
            window.step_page(-1)
            assert window.current_page == 3, window.current_page
            window.step_page(1)
            assert window.current_page == 4, window.current_page
            window._delete_pages([crop.IMPORT_PAGE_BASE + 1])
            assert window.page_list == [1, 2, 3], window.page_list
            # Drag reordering: a moved block lands exactly where it was dropped.
            grid = PageGrid()
            for key in (1, 2, 3):
                grid.addItem(QListWidgetItem(str(key)))
            grid.move_to_position([2], 0)
            order_now = [grid.item(i).text() for i in range(grid.count())]
            assert order_now == ["3", "1", "2"], order_now
            grid.move_rows([0, 1], 3)
            order_now = [grid.item(i).text() for i in range(grid.count())]
            assert order_now == ["2", "3", "1"], order_now
            return f"list={window.page_list} thumbs={len(thumbs)} spin_max={window.page_spin.maximum()}"

        step("sample PDF", make_sample)
        step("Qt window and preview", open_window)
        step("analyze, export, OCR", export)
        step("uniform margins fast path, rotation, imports", uniform_fast_path)
        step("organizer, thumbnails, filter and navigation without analysis", organize_without_analysis)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if passed else 1


def _install_crash_log() -> None:
    """Uncaught exceptions in slots are invisible in a windowed build."""

    def hook(exc_type, exc, tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            path = crop.app_data_dir("运行日志.log")
            path.parent.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{stamp}] 未捕获异常：")
                handle.write(text)
                handle.write("")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def main() -> int:
    _install_crash_log()
    if str(app_dir()) not in sys.path:
        sys.path.insert(0, str(app_dir()))
    args = sys.argv[1:]
    self_test = args[:1] == ["--self-test"]
    if self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(resource_path("pdf_crop.ico"))))
    apply_style(app)
    if self_test:
        return run_self_test(Path(args[1]) if len(args) > 1 else app_dir() / "self-test.txt")
    install_qt_translator(app, load_ui_lang())
    window = PdfCropWindow()
    window.show()
    # A PDF dropped on the exe or its shortcut arrives as a command-line argument.
    for arg in args:
        path = Path(arg)
        if path.suffix.lower() == ".pdf" and path.is_file():
            window.set_input(path)
            break
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
