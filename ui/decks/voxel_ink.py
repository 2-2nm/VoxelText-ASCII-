from ui.theme import blend

DEPTH_LEVELS = 8
DEPTH_FLOOR = 0.3


def depth_ramp(background, color, fade):
    if not fade:
        return [color] * DEPTH_LEVELS
    return [
        blend(background, color, DEPTH_FLOOR + (1 - DEPTH_FLOOR) * i / (DEPTH_LEVELS - 1))
        for i in range(DEPTH_LEVELS)
    ]


class InkCache:
    def __init__(self):
        self._key = None
        self._ramps = {}

    def ramp(self, background, color, fade):
        key = (background, fade)
        if key != self._key:
            self._key = key
            self._ramps = {}
        ramp = self._ramps.get(color)
        if ramp is None:
            ramp = self._ramps[color] = depth_ramp(background, color, fade)
        return ramp
