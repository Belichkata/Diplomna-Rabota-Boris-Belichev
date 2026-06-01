from config import LEFT_EYE, RIGHT_EYE
from utils.math_utils import eye_aspect_ratio


def shape_to_points(shape):
    return [(shape.part(index).x, shape.part(index).y) for index in range(68)]


__all__ = ["LEFT_EYE", "RIGHT_EYE", "eye_aspect_ratio", "shape_to_points"]
