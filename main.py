import math
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QApplication, QMenu, QWidget


WINDOW_WIDTH = 184
WINDOW_HEIGHT = 206
SPRITE_SIZE = 160
ASSET_DIRECTORY = Path(__file__).resolve().parent


class VirtualPet(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setMouseTracking(True)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.sprites = {
            mood: self._load_sprite(mood)
            for mood in ("normal", "angry", "sad", "sleepy")
        }
        self.hunger = 80
        self.happiness = 80
        self.energy = 80
        self.sleeping = False
        self._drag_offset: QPoint | None = None
        self._hovering = False
        self._bubble_pinned = False
        self._direction = 1
        self._walking_until = 0.0
        self._next_walk_at = time.monotonic() + 2.0
        self._animation_started = time.monotonic()

        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._unpin_bubble)

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._decay_stats)
        self._stats_timer.start(30_000)

        self._movement_timer = QTimer(self)
        self._movement_timer.timeout.connect(self._animate)
        self._movement_timer.start(50)

        self._place_at_screen_bottom()

    @staticmethod
    def _load_sprite(mood: str) -> QPixmap:
        path = ASSET_DIRECTORY / f"{mood}.png"
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise FileNotFoundError(f"Could not load pet sprite: {path}")
        return pixmap.scaled(
            SPRITE_SIZE,
            SPRITE_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def _current_mood(self) -> str:
        if self.sleeping or self.energy <= 25:
            return "sleepy"
        if self.hunger <= 25:
            return "angry"
        if self.happiness <= 25:
            return "sad"
        return "normal"

    def _current_screen_geometry(self):
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry()

    def _place_at_screen_bottom(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            area.left() + (area.width() - self.width()) // 2,
            area.bottom() - self.height() + 1,
        )

    def _animate(self) -> None:
        now = time.monotonic()
        if self._drag_offset is None and not self.sleeping:
            if now >= self._walking_until and now >= self._next_walk_at:
                self._walking_until = now + 7.0
                self._next_walk_at = self._walking_until + 2.5
            if now < self._walking_until:
                area = self._current_screen_geometry()
                left = area.left()
                right = area.right() - self.width() + 1
                next_x = self.x() + self._direction
                if next_x < left or next_x > right:
                    self._direction *= -1
                    next_x = max(left, min(right, self.x() + self._direction))
                self.move(next_x, area.bottom() - self.height() + 1)
        self.update()

    def _decay_stats(self) -> None:
        self.hunger = max(0, self.hunger - 1)
        self.happiness = max(0, self.happiness - 1)
        if self.sleeping:
            self.energy = min(100, self.energy + 3)
        else:
            self.energy = max(0, self.energy - 1)
        self.update()

    def _show_bubble(self, pin: bool = False) -> None:
        self._bubble_pinned = pin
        if pin:
            self._bubble_timer.start(5000)
        else:
            self._bubble_timer.stop()
        self.update()

    def _unpin_bubble(self) -> None:
        self._bubble_pinned = False
        if not self._hovering:
            self.update()

    def _feed(self) -> None:
        self.hunger = min(100, self.hunger + 30)
        self.happiness = min(100, self.happiness + 5)
        self.update()

    def _play(self) -> None:
        self.sleeping = False
        self.happiness = min(100, self.happiness + 18)
        self.energy = max(0, self.energy - 15)
        self.hunger = max(0, self.hunger - 5)
        self.update()

    def _toggle_sleep(self) -> None:
        self.sleeping = not self.sleeping
        self._next_walk_at = time.monotonic() + 2.5
        self.update()

    def _show_context_menu(self, position: QPoint) -> None:
        self._show_bubble(pin=True)
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: #fff7ed;
                color: #382b36;
                border: 1px solid #d8a6a8;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item { padding: 7px 24px; border-radius: 5px; }
            QMenu::item:selected { background: #f3c6c5; }
            """
        )
        actions = (
            ("Feed", self._feed),
            ("Play", self._play),
            ("Sleep", self._toggle_sleep),
            ("Status", lambda: self._show_bubble(pin=True)),
            ("Exit", QApplication.quit),
        )
        for label, callback in actions:
            menu.addAction(label, callback)
        menu.exec(position)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        visible = self._hovering or self._bubble_pinned
        if visible:
            self._paint_status_bubble(painter)

        elapsed = time.monotonic() - self._animation_started
        bob = round(1.5 * math.sin(elapsed * 5))
        sprite_x = (self.width() - SPRITE_SIZE) // 2
        sprite_y = 46 + bob
        painter.drawPixmap(sprite_x, sprite_y, self.sprites[self._current_mood()])

    def _paint_status_bubble(self, painter: QPainter) -> None:
        bubble = QRectF(2, 2, self.width() - 4, 48)
        painter.setPen(QPen(QColor("#d8a6a8"), 1))
        painter.setBrush(QColor(255, 247, 237, 242))
        painter.drawRoundedRect(bubble, 9, 9)
        painter.setBrush(QColor(255, 247, 237, 242))
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(self.width() / 2 - 6, 48),
                    QPointF(self.width() / 2 + 6, 48),
                    QPointF(self.width() / 2, 57),
                ]
            )
        )
        painter.setPen(QColor("#382b36"))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        status = "Sleeping" if self.sleeping else self._current_mood().title()
        painter.drawText(
            QRectF(8, 7, self.width() - 16, 18),
            Qt.AlignmentFlag.AlignCenter,
            f"Hunger {self.hunger}   Happy {self.happiness}   Energy {self.energy}",
        )
        painter.drawText(
            QRectF(8, 25, self.width() - 16, 18),
            Qt.AlignmentFlag.AlignCenter,
            f"Mood: {status}",
        )

    def enterEvent(self, event) -> None:
        self._hovering = True
        self._show_bubble()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovering = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._walking_until = 0.0
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self._walking_until = 0.0
            self._next_walk_at = time.monotonic() + 2.5
        super().mouseReleaseEvent(event)

def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = VirtualPet()
    pet.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
