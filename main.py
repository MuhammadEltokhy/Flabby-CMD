from __future__ import annotations
import time
from pathlib import Path
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual import events
from gameplay import BIRD, PIPE, Game

MIN_W, MIN_H = 40, 14
FPS=30
BEST_SAVE= Path.home() / ".flabby_bird_best"
SKY="on #4ec0ca"
PIPES="#2e7d32 on #4ec0ca"
EDGES="#1b5e20 on #4ec0ca"
CAP="#8bc34a on #4ec0ca"
LIFE="bold #ffeb3b on #4ec0ca"
DEATH="bold #ef5350 on #4ec0ca"
GROUND="#a1887f on #5d4037"
LABEL="bold white on #263238"

def load() -> int:
    try:
        return int(BEST_SAVE.read_text().strip())
    except (OSError, ValueError):
        return 0
def save(value: int) -> None:
    try:
        BEST_SAVE.write_text(str(value))
    except OSError:
        pass

class View(Widget):
    def __init__(self, game: Game)->None:
        super().__init__()
        self.game = game
    def on_click(self)->None:
        self.app.flaps()
    def render(self)->Text:
        g = self.game
        w, h = self.size.width, self.size.height
        if w < MIN_W or h < MIN_H:
            return Text(f"Terminal too small ({w}x{h}). Need at least {MIN_W}x{MIN_H}.")
        grid=[[(" ", SKY) for _ in range(w)] for _ in range(h)]
        def put(row: int, col: int, s: str, style: str)->None:
            if not 0 <= row < h:
                return
            for i, ch in enumerate(s):
                if 0 <= (col + i) < w:
                    grid[row][col + i] = (ch, style)
        def centre(row: int, s: str) -> None:
            put(row, (w-len(s)) // 2, f"{s}", LABEL)
        for p in g.pipes:
            px=round(p.x)
            top, bottom=p.rows()
            for dx in range(PIPE):
                x = px + dx
                if not 0 <= x < w:
                    continue
                edge = dx in (0, PIPE-1)
                for r in range(min(g.play_h, h - 1)):
                    if r< top or r> bottom:
                        if r in (top-1, bottom+1):
                            grid[r][x]=("█", CAP)
                        else:
                            grid[r][x]=("█", EDGES if edge else PIPES)
        shift=int(g.distance)
        for x in range(w):
            grid[h - 1][x]=("▚" if (x+shift)%4 <2 else "▞", GROUND)
        if g.state=="dead":
            put(round(g.bird_y), g.bird_x, "(x>", DEATH)
        else:
            face="(O>" if g.vy <0 else "(o>"
            put(round(g.bird_y), g.bird_x, face, LIFE)
        put(0, 1, f" Score {g.score} ", LABEL)
        put(0, 15, f" Best {g.best} ", LABEL)
        put(0, 27, f" Lv {g.level +1} ", LABEL)
        if g.time - g.lvl_up_t <1.5 and g.state=="playing":
            centre(3, f"LEVEL {g.level +1}")
        mid= (h//2)-3
        if g.state=="ready":
            centre(mid, "FLABBY BIRD")
            centre(mid +2, "SPACE / UP / click to flap")
            centre(mid +3, "P pause   R restart   Q quit")
        elif g.state=="paused":
            centre(mid, "PAUSED")
            centre(mid +2, "press P to resume")
        elif g.state=="dead":
            centre(mid, "GAME OVER")
            centre(mid+2, f"Score {g.score}   Best {g.best}")
            centre(mid+3, "SPACE to try again")
        lines=[]
        for row in grid:
            line= Text()
            run, style ="", None
            for ch, st in row:
                if st==style:
                    run+=ch
                else:
                    if run:
                        line.append(run, style)
                    run, style =ch, st
            if run:
                line.append(run, style)
            lines.append(line)
        return Text("\n").join(lines)

class main(App):
    CSS = """
    View{ 
        width: 100%; 
        height: 100%; 
    }
    """
    def on_key(self, event: events.Key) -> None:
        if event.key in ("space", "up", "w"):
            self.flaps()
        elif event.key == "p":
            self.pauses()
        elif event.key == "r":
            self.restarts() 
    BINDINGS=[
        Binding("space,up,w", "flap", "Flap", show=False),
        Binding("p", "pause", "Pause", show=False),
        Binding("r", "restart", "Restart", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]
    def __init__(self)->None:
        super().__init__()
        self.saved =load()
        self.game= Game(best = self.saved)
        self.view= View(self.game)
        self._last= time.monotonic()
    def compose(self) -> ComposeResult:
        yield self.view
    def on_mount(self)->None:
        self.set_interval(1/FPS, self.tick)
    def tick(self)->None:
        now= time.monotonic()
        dt= min(now- self._last, 0.1)
        self._last= now
        size= self.view.size
        if size.width >0 and size.height >0:
            self.game.resize(size.width, size.height)
        self.game.update(dt)
        if self.game.state=="dead" and self.game.best > self.saved:
            self.saved= self.game.best
            save(self.saved)
        self.view.refresh()
    def flaps(self) -> None:
        self.game.flap()
    def pauses(self) -> None:
        self.game.pause()
    def restarts(self) -> None:
        self.game.restart()

if __name__ == "__main__":
    main().run()


