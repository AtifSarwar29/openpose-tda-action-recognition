import cv2
import numpy as np


class PathVisualiser(object):

    def __init__(self):
        self.colors = [(255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]

    def draw_paths(self, people_paths, img, current_frame):
        for i, person_path in enumerate(people_paths):
            self.add_lines_from_path(img, person_path,
                                     self.colors[i % len(self.colors)], current_frame)
            # self.mark_hand(img, person_path, self.colors[i % len(self.colors)])

        cv2.imshow("output", img)
        cv2.waitKey(15)

    def add_lines_from_path(self, img, person_path, color, current_frame):
        # Don't draw old paths
        if person_path.last_frame_update <= current_frame - 10:
            return

        start_index = max(1, len(person_path.path) - 10)
        for i in range(start_index, len(person_path.path)):
            keypoint = person_path[i].get_nonzero_keypoint()
            prev_keypoint = person_path[i - 1].get_nonzero_keypoint()

            # If there are no nonzero keypoints, just move on with your life.
            if any(np.array_equal(k, [0.0, 0.0]) for k in [keypoint, prev_keypoint]):
                continue

            cv2.line(img, tuple(prev_keypoint), tuple(keypoint), color, 3)
