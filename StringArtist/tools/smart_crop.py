import math
import typing

from StringArtist.gui.placements import Placement
from PIL import Image, ImageDraw

if typing.TYPE_CHECKING:
    from StringArtist.gui import GUI


def distance_between_two_points(x1: int, y1: int, x2: int, y2: int):
    return math.sqrt(pow(x2 - x1, 2) + pow(y2 - y1, 2))


class SmartCropper:
    def __init__(self, gui: "GUI"):
        self.gui = gui
        self.order: list[tuple[int, int]] = []

    @property
    def placements(self):
        return self.gui.placements

    @staticmethod
    def calculate_distances(
        parent: Placement, placements: list[Placement], include_self: bool = False
    ):
        for placement in placements:
            if placement.cropper_scanned:
                continue

            distance = distance_between_two_points(
                parent.x, parent.y, placement.x, placement.y
            )
            yield distance, placement

    def get_closest_placement_to(self, placement: Placement):
        self.placements[self.gui.priority_nail].cropper_scanned = True
        distances = list(self.calculate_distances(placement, self.placements))

        if len(distances) == 0:
            return

        dist, closest = min(distances, key=lambda x: x[0])

        self.gui.priority_nail = self.placements.index(closest)
        self.order.append((closest.x, closest.y))

    def get_order(self):
        for _ in self.placements:
            seed_nail = self.placements[self.gui.priority_nail]
            self.get_closest_placement_to(seed_nail)

    def connect(self):
        print("connecting")
        p1 = self.order.pop(0)
        p2 = self.order[1]
        self.gui.workspace_canvas.create_line(*p1, *p2, fill="#FF0000")

    def crop(self):
        im = Image.open(self.gui.im_path).convert("RGBA")

        mask = Image.new("L", im.size, 0)

        draw = ImageDraw.Draw(mask)
        draw.polygon(self.order, fill=255)

        result = Image.new("RGBA", im.size, (0, 0, 0, 0))
        result.paste(im, mask=mask)
        result.show()

    def run(self):

        for placement in self.placements:
            placement.cropper_scanned = False

        self.get_order()

        self.crop()
