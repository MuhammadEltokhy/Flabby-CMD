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

@dataclass
class Pipe:
    x: float
    base: float
    gap: int
    amp: float
    t: float = 0.0
    scored: bool = False
    def row(self)->tuple[int, int]:
        centre=self.base+self.amp*math.sin(self.t)
        top=round(centre-self.gap/2)
        return top,top+self.gap-1

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
    def _collides(self)->bool:
        row=round(self.bird_y)
        if row>=self.play_h:
            return True
        for p in self.pipes:
            px=round(p.x)
            if px<self.bird_x+BIRD and px+PIPE>self.bird_x:
                top, bottom=p.row()
                if row<top or row>bottom:
                    return True
        return False

