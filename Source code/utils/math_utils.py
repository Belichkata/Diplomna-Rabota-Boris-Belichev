import math


def euclidean_distance(p1, p2):
    return math.dist(p1, p2)


def eye_aspect_ratio(eye):
    vertical_1 = euclidean_distance(eye[1], eye[5])
    vertical_2 = euclidean_distance(eye[2], eye[4])
    horizontal = euclidean_distance(eye[0], eye[3])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)
