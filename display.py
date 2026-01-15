import datetime as dt
from PIL import Image, ImageDraw, ImageFont
from font_source_sans_pro import SourceSansPro
from typing import Iterable
from inky.auto import auto

from data import Arrival


class Display:
    def __init__(self, stop_name: str):
        self.inky_display = auto()
        self.stop_name = stop_name
        self.ROUTE_TO_COLOR = {
            'A': self.inky_display.BLUE,
            'B': self.inky_display.RED,
            'C': self.inky_display.BLUE,
            'D': self.inky_display.RED,
            'E': self.inky_display.BLUE,
            'F': self.inky_display.RED,
            'G': self.inky_display.GREEN,
            'J': self.inky_display.RED,
            'L': self.inky_display.WHITE,
            'M': self.inky_display.RED,
            'N': self.inky_display.YELLOW,
            'Q': self.inky_display.YELLOW,
            'R': self.inky_display.YELLOW,
            'S': self.inky_display.BLACK,
            'W': self.inky_display.YELLOW,
            'J': self.inky_display.RED,
            '1': self.inky_display.RED,
            '2': self.inky_display.RED,
            '3': self.inky_display.RED,
            '4': self.inky_display.GREEN,
            '5': self.inky_display.GREEN,
            '6': self.inky_display.GREEN,
            '7': self.inky_display.BLUE,
        }

    def refresh(self, arrivals: Iterable[Arrival]) -> Image:
        now = dt.datetime.now()
        arrivals = [a for a in arrivals if a.when >= now]
        arrivals.sort(key=lambda arrival: arrival.when)
        uptown = [a for a in arrivals if a.direction == 'N']
        downtown = [a for a in arrivals if a.direction == 'S']

        IMG_WIDTH = 800
        IMG_HEIGHT = 480
        CIRCLE_RADIUS = 24
        CIRCLE_PADDING = 8
        CELL_HEIGHT = (CIRCLE_RADIUS + CIRCLE_PADDING) * 2

        img = Image.new("P", (IMG_WIDTH, IMG_HEIGHT), self.inky_display.BLACK)
        draw = ImageDraw.Draw(img)

        def write(text: str, *, x: float, y: float, color=self.inky_display.WHITE, size=CELL_HEIGHT * 0.6, **kwargs):
            draw.text((x, y), text, color, ImageFont.truetype(SourceSansPro, size=size), **kwargs)

        def draw_arrival(arrival: Arrival, *, x: float, i: int):
            route_color = self.ROUTE_TO_COLOR.get(arrival.route.id, self.inky_display.BLACK)
            route_text_color = self.inky_display.WHITE
            if route_color in (self.inky_display.WHITE, self.inky_display.YELLOW):
                route_text_color = self.inky_display.BLACK
            draw.line([(x, (i + 2) * CELL_HEIGHT),
                    (x + IMG_WIDTH / 2, (i + 2) * CELL_HEIGHT)],
                    self.inky_display.WHITE)
            draw.circle((x + CIRCLE_RADIUS + CIRCLE_PADDING, (i + 2.5) * CELL_HEIGHT),
                        CIRCLE_RADIUS,
                        route_color)
            write(arrival.route.id,
                x=x + CIRCLE_RADIUS + CIRCLE_PADDING,
                y=(i + 2.5) * CELL_HEIGHT,
                anchor='mm',
                color=route_text_color)
            minutes = arrival.wait_minutes(now)
            write('1 minute' if minutes == 1 else f'{minutes} minutes',
                x=x + (CIRCLE_RADIUS + CIRCLE_PADDING) * 2,
                y=(i + 2.5) * CELL_HEIGHT,
                color=self.inky_display.YELLOW if minutes == 0 else self.inky_display.WHITE,
                anchor='lm')

        write(self.stop_name, x=IMG_WIDTH / 2, y=CELL_HEIGHT / 2, anchor='mm')
        write('Uptown', x=CIRCLE_PADDING, y=CELL_HEIGHT * 1.5, anchor='lm')
        write('Downtown', x=IMG_WIDTH / 2 + CIRCLE_PADDING, y=CELL_HEIGHT * 1.5, anchor='lm')

        for i, arrival in enumerate(uptown):
            draw_arrival(arrival, x=0, i=i)

        for i, arrival in enumerate(downtown):
            draw_arrival(arrival, x=IMG_WIDTH / 2, i=i)

        write(f'Updated at {now:%-I:%M %p}',
              x=IMG_WIDTH / 2,
              y=CELL_HEIGHT,
              color=self.inky_display.YELLOW,
              size=18,
              anchor='mm')

        img.transpose(Image.ROTATE_180)
        self.inky_display.set_image(img)
        self.inky_display.show()
