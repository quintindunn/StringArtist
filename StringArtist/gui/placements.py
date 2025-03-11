import logging

logger = logging.getLogger("placements.py")


class PlacementLoadError(BaseException):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg


class Placement:
    def __init__(self, x: int, y: int, priority: bool):
        self.x: float = x
        self.y: float = y
        self.priority: bool = priority

    def to_scaled(self, scale: float):
        return round(self.x * scale), round(self.y * scale)


def placements_from_json(placements: list) -> list[Placement]:
    def log_and_raise(msg: str):
        logger.warning(msg)
        raise PlacementLoadError(msg)

    if not isinstance(placements, list):
        log_and_raise("Error loading placements, data is not a list!")

    new_placements: list[Placement] = []

    for placement in placements:
        if not isinstance(placement, list):
            log_and_raise("Error loading placements, data[i] is not a list!")

        if len(placement) != 3:
            log_and_raise("Error loading placements, data[i][j] has incorrect length!")

        for value in placement:
            if not isinstance(value, int):
                log_and_raise("Error loading placements, data[i][j] is not an integer!")

        x, y, priority = placement
        new_placements.append(Placement(x=x, y=y, priority=priority))

    if len(new_placements) < 3:
        log_and_raise("Error loading placements, not enough points!")

    return new_placements


def placements_to_json(
    placements: list[Placement], descale_factor: float
) -> list[list]:
    data = []

    for placement in placements:
        data.append([*placement.to_scaled(descale_factor), placement.priority])

    return data
