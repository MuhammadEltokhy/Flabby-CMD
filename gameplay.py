from __future__ import annotations
import math
import random
from dataclasses import dataclass

BIRD = 3
PIPE = 7
GRAVITY=50.0
VELOCITY=-14.0
FALL=22.0
GAP=5
LEVEL=5
FLOOD_LVL=7
FLOOD_PIPES=8
CALM_PIPES=12
RAMP_COLS=20
LEAD_COLS=10
COR_FRAC=0.40
COR_EX=4
BANNER_T=2.0
BANNER="bold #ffffff on #0d47a1"
SURFACE="bold #e3f2fd on #0288d1"
BODY="#4fc3f7 on #0d47a1"
FIRE_LVL=2
RAMP_START=15
RAMP_END=35
BALL_W=6
BALL_H=2
T_START=9.0
T_END = 1.3
S_START=14.0
S_END=28.0
MAX_START=1
MAX_END=5
WARN_T=0.8
AVOID=False
ARRIVAL_MARGIN=6
BALL=["#d50000", "#ff6d00", "#ffd600", "#ffd600", "#ff6d00", "#d50000"]
WARN="bold #ffffff on #d50000"

@dataclass
class Pipe:
    x: float
    base: float
    gap: int
    amp: float
    t: float = 0.0
    scored: bool = False
    def rows(self)->tuple[int, int]:
        centre=self.base+self.amp*math.sin(self.t)
        top=round(centre-self.gap/2)
        return top,top+self.gap-1

@dataclass
class Flood:
    xl: float
    xr: float | None
    c_top: int
    c_bot: int
    d_top: int
    d_bot: int
    amp_max: float
    born: float

def _put(grid, row: int, col: int, text: str, style: str) -> None:
    if not 0<= row< len(grid):
        return
    for i, ch in enumerate(text):
        if 0<= col+i <len(grid[row]):
            grid[row][col+i] =(ch, style)

@dataclass
class FloodSys:
    def __init__(self, Game) ->None:
        self.game=Game
        self.bird_w=BIRD
        self.pipe_w=PIPE
        self.shift=GAP
        self.seg: Flood | None = None
        self.phase="calm"
        self.calm_left=0
        self.floods=0
    def pipe_spawn(self, pipe) ->None:
        g=self.game
        if self.phase=="calm":
            if g.level+1 <FLOOD_LVL:
                return
            if self.calm_left>0:
                self.calm_left-=1
                return
            if self.seg is not None:
                return
            self._start(pipe)
            self._fit(pipe)
            self.phase = "flood"
            self.floods = 0
        elif self.phase=="flood":
            self._fit(pipe)
            self.floods +=1
            if self.floods ==FLOOD_PIPES:
                self.seg.xr = g.width + self.pipe_w + LEAD_COLS + RAMP_COLS
                self.phase = "exit"
        else:
            self._fit(pipe)
            self.phase = "calm"
            self.calm_left = CALM_PIPES
    def _start(self, pipe) ->None:
        g= self.game
        ph= g.play_h
        c_h= min(max(pipe.gap + COR_EX, round(ph*COR_FRAC)), ph-2)
        d_top=(ph-c_h) // 2
        d_bot= ph-c_h-d_top
        xl= pipe.x + g.spacing - LEAD_COLS-RAMP_COLS
        self.seg = Flood(
            xl=xl, xr=None,
            c_top=d_top, c_bot=ph - 1 - d_bot,
            d_top=d_top, d_bot=d_bot,
            amp_max=max(0.0, (c_h-1- pipe.gap -2)/2),
            born=g.time,
        )
    def _fit(self, pipe) ->None:
        g= self.game
        seg= self.seg
        amp= min(pipe.amp, seg.amp_max)
        half= pipe.gap / 2
        lo= seg.c_top +half+0.5+amp
        hi= seg.c_bot +0.5-half-amp
        if lo>hi:
            lo=hi= (lo+hi)/2
        prev= g.pipes[-2].base if len(g.pipes) > 1 else g.play_h / 2
        a, b = max(lo, prev - self.shift), min(hi, prev + self.shift)
        pipe.base = random.uniform(a, b) if a <= b else (lo if prev < lo else hi)
        pipe.amp =amp
    def update(self, dt: float, step: float) ->None:
        seg = self.seg
        if seg is None:
            return
        seg.xl -= step
        if seg.xr is not None:
            seg.xr -= step
            if seg.xr < 0:
                self.seg = None
    def corridor(self):
        seg = self.seg
        return (seg.c_top, seg.c_bot) if seg else None
    def depth(self, x: int):
        seg= self.seg
        if seg is None:
            return 0, 0
        f = (x - seg.xl) /RAMP_COLS
        if seg.xr is not None:
            f= min(f, (seg.xr -x)/RAMP_COLS)
        f= max(0.0, min(1.0, f))
        return round(f*seg.d_top), round(f*seg.d_bot)
    def _hit(self, row: int) -> bool:
        if self.seg is None:
            return False
        g = self.game
        t0, b0 = self.depth(g.bird_x)
        t1, b1 = self.depth(g.bird_x + self.bird_w - 1)
        return row < max(t0, t1) or row > g.play_h - 1 - max(b0, b1)
    def draw(self, grid, w: int, h: int) -> None:
        seg = self.seg
        if seg is None:
            return
        g= self.game
        wave= int(g.time*6)
        rows= len(grid)
        for x in range(w):
            top, bot = self.depth(x)
            for r in range(min(top, rows)):
                grid[r][x] = self._cell(x, wave, surface=(r == top - 1))
            for r in range(g.play_h - bot, min(g.play_h, rows)):
                grid[r][x] = self._cell(x, wave, surface=(r == g.play_h - bot))
        if g.state == "playing" and g.time - seg.born < BANNER_T:
            text=" FLOOD INCOMING "
            _put(grid, 5, (w - len(text))//2, text, BANNER)
    @staticmethod
    def _cell(x: int, wave: int, surface: bool):
        crest = (x + wave) % 4 < 2
        if surface:
            return ("~" if crest else "≈"), SURFACE
        return ("≈" if crest else "~"), BODY

@dataclass
class Fireball:
    x: float
    row: int
    speed: float

@dataclass
class Alert:
    row: int
    left: float

def _lerp(a: float, b: float, t: float) -> float:
    return a+(b-a)*t

def _put(grid, row: int, col: int, text: str, style: str) -> None:
    if not 0<= row< len(grid):
        return
    for i, ch in enumerate(text):
        if 0<= col+i <len(grid[row]):
            grid[row][col+i]=(ch, style)

@dataclass
class FireballManager:
    def __init__(self, Game) ->None:
        self.game = Game
        self.bird_w= BIRD
        self.pipe_w= PIPE
        self.lvl_cycle= LEVEL
        self.balls: list[Fireball] = []
        self.alerts: list[Alert] = []
        self.cooldown: float | None = None
    @property
    def ramp(self) ->float:
        level= 1+ self.game.score / self.lvl_cycle
        return min(1.0, max(0.0, (level-RAMP_START)/(RAMP_END-RAMP_START)))
    @property
    def interval(self) ->float:
        return _lerp(T_START, T_END, self.ramp)
    @property
    def mein_S(self) ->float:
        return _lerp(S_START, S_END, self.ramp)
    @property
    def max_alive(self) -> int:
        return round(_lerp(MAX_START, MAX_END, self.ramp))
    def update(self, dt: float, step: float) -> None:
        g= self.game
        for b in self.balls:
            b.x-= step+b.speed*dt
        self.balls=[b for b in self.balls if b.x+BALL_W >0]
        for a in self.alerts:
            a.left-= dt
        for a in self.alerts:
            if a.left<=0:
                self.balls.append(Fireball(float(g.width), a.row, self.mein_S))
        self.alerts=[a for a in self.alerts if a.left >0]
        if g.level +1 <FIRE_LVL:
            return
        if self.cooldown is None:
            self.cooldown= random.uniform(2.0, 4.0)
        self.cooldown -=dt
        if self.cooldown <=0:
            if len(self.balls) + len(self.alerts) >= self.max_alive:
                self.cooldown = self.interval * random.uniform(0.75, 1.25)
            elif self._clear():
                self._warn()
                self.cooldown = self.interval * random.uniform(0.75, 1.25)
    def _clear(self) -> bool:
        if not AVOID:
            return True
        g= self.game
        bx= g.bird_x
        travel= (g.width - (bx - BALL_W / 2))/(g.speed + self.mein_S)
        t=WARN_T+travel
        xs= [p.x for p in g.pipes]
        if g.pipes:
            xs+= [g.pipes[-1].x + k * g.spacing for k in (1, 2, 3)]
        for x in xs:
            px= x-g.speed*t
            if (px< bx+self.bird_w+ARRIVAL_MARGIN
                    and px+self.pipe_w > bx-BALL_W-ARRIVAL_MARGIN):
                return False
        return True
    def _warn(self) -> None:
        g = self.game
        top, bottom = 0, g.play_h - 1
        flood = getattr(g, "flood", None)
        if flood is not None and flood.corridor() is not None:
            top, bottom = flood.corridor()
        aim = round(g.bird_y) - 1 + random.randint(-2, 2)
        row = min(max(aim, top), bottom - BALL_H + 1)
        self.alerts.append(Alert(row, WARN_T))
    def _hit(self, row: int) -> bool:
        bx= self.game.bird_x
        for b in self.balls:
            x0= round(b.x)
            if (x0< bx+self.bird_w and x0+BALL_W >bx
                    and b.row<= row< b.row+BALL_H):
                return True
        return False
    def draw(self, grid, w: int, h: int) -> None:
        g= self.game
        if int(g.time * 8) % 2 == 0:
            for a in self.alerts:
                for dr in range(BALL_H):
                    _put(grid, a.row + dr, w - 4, " !! ", WARN)
        last= len(BALL)-1
        for b in self.balls:
            x= round(b.x)
            for j in range(BALL_W):
                color = BALL[round(j * last / max(1, BALL_W - 1))]
                for dr in range(BALL_H):
                    _put(grid, b.row + dr, x + j, "█", f"bold {color}")

@dataclass
class Game:
    def __init__(self, width: int = 80, height: int = 24, best: int = 0) -> None:
        self.width = width
        self.height = height
        self.best = best
        self.reset()
    @property
    def play_h(self) -> int:
        return self.height - 1
    @property
    def bird_x(self) -> int:
        return max(6, self.width//5)
    @property
    def level(self) -> int:
        return self.score//LEVEL
    @property
    def speed(self) -> float:
        return min(18+2*self.level,40)
    @property
    def gap(self) -> int:
        return max(3, min(max(6, 10-self.level//2), self.play_h-6))
    @property
    def amp(self) -> float:
        return 0.0 if self.level<3 else min(3.0, 0.5*(self.level-2))
    @property
    def spacing(self) -> float:
        return self.speed*max(1.25, 1.9-0.05*self.level)
    def reset(self) -> None:
        self.state="ready"
        self.score=0
        self.bird_y=self.play_h/2
        self.vy=0.0
        self.pipes:list[Pipe]=[]
        self.distance=0.0
        self.time=0.0
        self.dd_t=0.0
        self.lvl_up_t=-10.0
        self.fire = FireballManager(self)
        self.flood = FloodSys(self) 
    def resize(self, width: int, height: int)->None:
        if (width, height)==(self.width, self.height):
            return
        self.width, self.height = width, height
        self.reset()
    def flap(self)->None:
        if self.state=="ready":
            self.state="playing"
            self.vy=VELOCITY
        elif self.state=="playing":
            self.vy=VELOCITY
        elif self.state=="dead" and self.time-self.dd_t>0.6:
            self.reset()
    def pause(self)->None:
        if self.state=="playing":
            self.state="paused"
        elif self.state=="paused":
            self.state="playing"
    def restart(self)->None:
        self.reset()
    def update(self, dt: float)->None:
        self.time+=dt
        if self.state=="paused":
            return
        if self.state=="ready":
            self.distance+=12*dt
            self.bird_y=self.play_h/2 + math.sin(self.time*4)*0.6
            return
        if self.state == "dead":
            self.vy=min(self.vy+GRAVITY*dt,FALL)
            self.bird_y=min(self.bird_y+self.vy*dt,self.play_h-1)
            return
        self.vy=min(self.vy+GRAVITY*dt,FALL)
        self.bird_y+=self.vy*dt
        if self.bird_y<0:
            self.bird_y=0
            self.vy=max(self.vy, 0.0)
        step=self.speed*dt
        self.distance+=step
        for p in self.pipes:
            p.x-=step
            p.t+=1.3*dt
        self.pipes=[p for p in self.pipes if p.x+PIPE>=0]
        self.flood.update(dt, step)
        self.fire.update(dt, step)
        if not self.pipes or self.pipes[-1].x<=self.width-self.spacing:
            self._spawn()
        for p in self.pipes:
            if not p.scored and round(p.x)+PIPE<self.bird_x:
                p.scored=True
                pre_lvl=self.level
                self.score+=1
                self.best=max(self.best, self.score)
                if self.level!=pre_lvl:
                    self.lvl_up_t=self.time
        if self._collides():
            self.state="dead"
            self.dd_t=self.time
            self.vy=-8.0
    def _spawn(self)->None:
        gap, amp = self.gap, self.amp
        lo=gap/2 +1+amp
        hi = self.play_h-1 - gap/2 - amp
        if lo>hi:
            lo=hi=self.play_h/2
        last=self.pipes[-1].base if self.pipes else self.play_h/2
        a=max(lo, last-GAP)
        b=min(hi, last+GAP)
        base=random.uniform(a, b) if a<=b else min(max(last, lo),hi)
        self.pipes.append(
            Pipe(x=float(self.width), base=base, gap=gap, amp=amp,
                 t=random.uniform(0, 2*math.pi))
        )
        self.flood.pipe_spawn(self.pipes[-1])
    def _collides(self)->bool:
        row=round(self.bird_y)
        if row>=self.play_h:
            return True
        for p in self.pipes:
            px=round(p.x)
            if px<self.bird_x+BIRD and px+PIPE>self.bird_x:
                top, bottom=p.rows()
                if row<top or row>bottom:
                    return True
        if self.flood._hit(row):
            return True
        if self.fire._hit(row):
            return True
        return False
 
