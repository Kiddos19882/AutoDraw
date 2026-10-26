from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from PIL import Image, ImageTk, ImageDraw

CropBox = tuple[int, int, int, int]


class PreviewPane(ttk.LabelFrame):
    """Масштабируемая панель предпросмотра; исходник поддерживает выделение обрезки."""

    def __init__(self, parent, title: str, selectable: bool = False,
                 on_selection: Callable[[CropBox], None] | None = None):
        super().__init__(parent, text=title, padding=4)
        self.selectable = selectable
        self.on_selection = on_selection
        self.image: Image.Image | None = None
        self.selection_box: CropBox | None = None
        self.drag_start: tuple[int, int] | None = None
        self.drag_end: tuple[int, int] | None = None
        self.canvas = tk.Canvas(self, background="#ededed", highlightthickness=1,
                                highlightbackground="#c5c5c5", height=250, cursor="crosshair" if selectable else "arrow")
        self.canvas.pack(fill="both", expand=True)
        self.photo: ImageTk.PhotoImage | None = None
        self.display_rect = (0, 0, 0, 0)  # x, y, width, height
        self.scale_x = 1.0
        self.scale_y = 1.0
        self._selection_id: int | None = None
        self.canvas.bind("<Configure>", lambda _event: self.render())
        if selectable:
            self.canvas.bind("<ButtonPress-1>", self._on_press)
            self.canvas.bind("<B1-Motion>", self._on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.render()

    def set_image(self, image: Image.Image | None, selection_box: CropBox | None = None) -> None:
        self.image = image.copy() if image is not None else None
        self.selection_box = selection_box
        self.drag_start = None
        self.drag_end = None
        self.render()

    def set_selection(self, selection_box: CropBox | None) -> None:
        self.selection_box = selection_box
        self.render()

    def render(self) -> None:
        self.canvas.delete("all")
        self.photo = None
        if self.image is None:
            self.display_rect = (0, 0, 0, 0)
            self.canvas.create_text(15, 15, anchor="nw", fill="#555555",
                                    text="Загрузите изображение" if not self.selectable else "Загрузите изображение\nПеретащите мышью, чтобы выбрать обрезку")
            return

        canvas_width = max(40, self.canvas.winfo_width())
        canvas_height = max(40, self.canvas.winfo_height())
        margin = 8
        scale = min((canvas_width - margin * 2) / self.image.width,
                    (canvas_height - margin * 2) / self.image.height)
        display_width = max(1, int(round(self.image.width * scale)))
        display_height = max(1, int(round(self.image.height * scale)))
        self.scale_x = display_width / self.image.width
        self.scale_y = display_height / self.image.height
        x0 = (canvas_width - display_width) // 2
        y0 = (canvas_height - display_height) // 2
        self.display_rect = (x0, y0, display_width, display_height)
        preview = self.image.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(preview)
        self.canvas.create_image(x0, y0, anchor="nw", image=self.photo)

        if self.selection_box is not None:
            self._draw_selection(self.selection_box, outline="#13a56d", width=2)
        if self.drag_start is not None and self.drag_end is not None:
            box = self._box_from_points(self.drag_start, self.drag_end)
            self._draw_selection(box, outline="#e53935", width=2)

        if self.selectable:
            self.canvas.create_text(6, canvas_height - 5, anchor="sw", fill="#333333",
                                    text="Перетащите мышью по изображению для выделения области обрезки")

    def _draw_selection(self, box: CropBox, outline: str, width: int) -> None:
        x0, y0, _w, _h = self.display_rect
        x1, y1, x2, y2 = box
        self.canvas.create_rectangle(
            x0 + x1 * self.scale_x, y0 + y1 * self.scale_y,
            x0 + x2 * self.scale_x, y0 + y2 * self.scale_y,
            outline=outline, width=width,
        )

    def _event_to_image(self, event) -> tuple[int, int] | None:
        if self.image is None:
            return None
        x0, y0, width, height = self.display_rect
        if width <= 0 or height <= 0 or not (x0 <= event.x <= x0 + width and y0 <= event.y <= y0 + height):
            return None
        x = round((event.x - x0) / self.scale_x)
        y = round((event.y - y0) / self.scale_y)
        return max(0, min(self.image.width, x)), max(0, min(self.image.height, y))

    @staticmethod
    def _box_from_points(start: tuple[int, int], end: tuple[int, int]) -> CropBox:
        return min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1])

    def _on_press(self, event) -> None:
        point = self._event_to_image(event)
        if point is None:
            return
        self.drag_start = point
        self.drag_end = point
        self.render()

    def _on_drag(self, event) -> None:
        if self.drag_start is None:
            return
        point = self._event_to_image(event)
        if point is None:
            # При выходе курсора за изображение ограничиваем выделение её границами.
            if self.image is None:
                return
            x0, y0, width, height = self.display_rect
            px = max(x0, min(x0 + width, event.x))
            py = max(y0, min(y0 + height, event.y))
            point = (max(0, min(self.image.width, round((px - x0) / self.scale_x))),
                     max(0, min(self.image.height, round((py - y0) / self.scale_y))))
        self.drag_end = point
        # Перерисовываем изображение для простоты и корректности временной рамки.
        self.render()

    def _on_release(self, event) -> None:
        if self.drag_start is None or self.image is None:
            return
        point = self._event_to_image(event)
        if point is not None:
            self.drag_end = point
        if self.drag_end is None:
            self.drag_start = None
            self.render()
            return
        box = self._box_from_points(self.drag_start, self.drag_end)
        self.drag_start = None
        self.drag_end = None
        if box[2] - box[0] < 10 or box[3] - box[1] < 10:
            self.render()
            return
        self.selection_box = box
        self.render()
        if self.on_selection is not None:
            self.on_selection(box)
