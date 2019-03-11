from time import time

import cv2
import numpy as np
from shapely.geometry import GeometryCollection, LineString
from sklearn.cluster import DBSCAN

from model.Cluster import Cluster
from model.Line import Line
from model.Point import Point
from model.exceptions import IsNan, InvalidLine, TooManyLines, TooManyPoints


class Canny(object):
    def __init__(self):
        self.canny_threshold = 50

        self.theta = 150
        self.theta_modifier = 5

        self.last_frame_count = None
        self.last_time_count = time()

        self.line_max = 100

    def calculate_theta(self, lines):
        if self.last_frame_count is not None:
            modifier = (self.last_frame_count / lines) * 2

            if modifier <= 0:
                modifier = 1
        else:
            modifier = 1

        timestamp = time()

        if timestamp - self.last_time_count > 1 / 10:
            # TODO: Time check, if too long, increase l_theta
            print(f'Too slow, increasing l_theta to {self.theta}')
            self.theta += int(self.theta_modifier * 0.5)
        elif lines < 10 and self.theta > self.theta_modifier:
            self.theta -= int(round(self.theta_modifier * modifier, 0))
            print(f'Not enough data, decreasing l_theta to {self.theta}')
        elif lines > 50:
            print(f'Too much data, increasing l_theta to {self.theta}')
            self.theta += int(round(self.theta_modifier * modifier, 0))

        self.last_frame_count = lines
        self.last_time_count = timestamp

        if self.line_max < lines:
            raise TooManyLines()

    def process_frame(self, frame):
        lines_ = []
        edges = cv2.Canny(frame, self.canny_threshold, self.canny_threshold * 3, apertureSize=3)

        lines = cv2.HoughLines(edges, 2, np.pi / 180, self.theta)
        if lines is not None:
            try:
                self.calculate_theta(len(lines))

                for line_data in lines:
                    try:
                        line = Line(*line_data.T)
                        lines_.append(line)

                    except (IsNan, InvalidLine):
                        pass
            except (TooManyLines, TooManyPoints):
                pass

        return self.clustering(lines_)

    @staticmethod
    def clustering(lines):
        gc = GeometryCollection(lines)

        try:
            intersections = gc.intersection(gc)
            if isinstance(intersections, LineString):
                points = [Point(*intersections.xy)]
            else:
                points = [Point(*point.xy) for point in intersections]

            if points:
                points_ = [(p.x_point, p.y_point) for p in points]
                clustering = DBSCAN(eps=20, min_samples=5).fit(points_)

                clusters = {}

                for idx, kl in enumerate(clustering.labels_):
                    if kl == -1:
                        continue
                    if kl not in clusters:
                        clusters[kl] = Cluster()

                    points[idx].set_cluster(clusters[kl])

                clusters = [c for _, c in clusters.items()]

                if clusters:
                    c = [c for c in clusters if not c.is_dead()]
                    c = sorted(c, key=lambda c_: c_.cluster_size(), reverse=True)

                    cgc = GeometryCollection(c[0].points)

                    return c, Point(*cgc.centroid.xy)
            return [], None
        except TypeError as e:
            print(str(e))
            return [], None
