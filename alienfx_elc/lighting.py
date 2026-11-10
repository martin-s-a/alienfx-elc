"""Which look is on the controller, given the chosen preset and keyboard activity."""


class Lighting:
    def __init__(self, elc, presets):
        self.elc = elc
        self.presets = presets
        self.preset = None
        self.step = 0
        self.lit = False
        self.last_activity = 0.0
        self._shown = None

    def _show(self, groups):
        if groups != self._shown:
            self.elc.play(groups)
            self._shown = groups

    def select(self, name, now):
        preset = self.presets[name]
        if preset.kind == "steps" and self.preset is preset:
            self.step = (self.step + 1) % len(preset.frames)
        else:
            self.step = 0
        self.preset = preset
        self.lit = True
        self.last_activity = now
        self._show(self._current())

    def activity(self, now):
        self.last_activity = now
        if self.preset and self.preset.kind == "auto" and not self.lit:
            self.lit = True
            self._show(self._current())

    def deadline(self):
        if self.preset and self.preset.kind == "auto" and self.lit:
            return self.last_activity + self.preset.timeout
        return None

    def tick(self, now):
        deadline = self.deadline()
        if deadline is not None and now >= deadline:
            self.lit = False
            self._show(self._current())

    def reapply(self, presets):
        """Push the current look again, e.g. after resume or a config reload."""
        name = self.preset.name if self.preset else None
        self.presets = presets
        self._shown = None
        if name in presets:
            self.preset = presets[name]
            self.step %= len(self.preset.frames)
            self._show(self._current())
        else:
            self.preset = None

    def _current(self):
        if not self.lit:
            return self.preset.off_frame
        return self.preset.frames[self.step]
