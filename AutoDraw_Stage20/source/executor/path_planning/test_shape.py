from __future__ import annotations

from models import DrawingPlan, Point, Stroke


def create_test_shape(width: int, height: int) -> DrawingPlan:
    """Создаёт тестовую фигуру из прямых, диагоналей, ломаных и контуров.

    Координаты относительны к холсту. Геометрия использует проценты размера,
    поэтому подстраивается под любую область, достаточную для теста.
    """
    if width < 460 or height < 250:
        raise ValueError(
            "Для тестовой фигуры нужна область не менее 460 × 250 экранных пикселей."
        )

    def p(x_ratio: float, y_ratio: float) -> Point:
        return Point(round(width * x_ratio, 2), round(height * y_ratio, 2))

    strokes = [
        Stroke("01 Горизонтальная линия", [p(0.06, 0.13), p(0.28, 0.13)], metadata={"type": "line"}),
        Stroke("02 Вертикальная линия", [p(0.06, 0.20), p(0.06, 0.42)], metadata={"type": "line"}),
        Stroke("03 Диагональ вниз", [p(0.34, 0.13), p(0.50, 0.31)], metadata={"type": "diagonal"}),
        Stroke("04 Диагональ вверх", [p(0.57, 0.13), p(0.80, 0.31)], metadata={"type": "diagonal"}),
        Stroke(
            "05 Зигзагообразная ломаная",
            [p(0.06, 0.54), p(0.12, 0.44), p(0.18, 0.54), p(0.24, 0.44), p(0.30, 0.54)],
            metadata={"type": "polyline"},
        ),
        Stroke(
            "06 Ломаная с прямым углом",
            [p(0.37, 0.45), p(0.48, 0.45), p(0.48, 0.57)],
            metadata={"type": "polyline"},
        ),
        Stroke(
            "07 Прямоугольник (замкнутый)",
            [p(0.56, 0.43), p(0.74, 0.43), p(0.74, 0.62), p(0.56, 0.62)],
            closed=True,
            metadata={"type": "closed_contour"},
        ),
        Stroke(
            "08 Треугольник (замкнутый)",
            [p(0.82, 0.43), p(0.95, 0.62), p(0.80, 0.62)],
            closed=True,
            metadata={"type": "closed_contour"},
        ),
        Stroke(
            "09 Ломаная с частыми поворотами",
            [p(0.06, 0.76), p(0.12, 0.68), p(0.18, 0.82), p(0.24, 0.70), p(0.31, 0.82)],
            metadata={"type": "polyline"},
        ),
        Stroke(
            "10 Ромб (замкнутый)",
            [p(0.47, 0.66), p(0.55, 0.74), p(0.47, 0.88), p(0.39, 0.74)],
            closed=True,
            metadata={"type": "closed_contour"},
        ),
        Stroke(
            "11 Квадрат (замкнутый)",
            [p(0.61, 0.68), p(0.73, 0.68), p(0.73, 0.88), p(0.61, 0.88)],
            closed=True,
            metadata={"type": "closed_contour"},
        ),
        Stroke(
            "12 Пятиугольник (замкнутый)",
            [p(0.82, 0.69), p(0.92, 0.74), p(0.90, 0.86), p(0.83, 0.87), p(0.79, 0.77)],
            closed=True,
            metadata={"type": "closed_contour"},
        ),
    ]
    return DrawingPlan(width=width, height=height, strokes=strokes, name="Stage 2 — geometry test")
