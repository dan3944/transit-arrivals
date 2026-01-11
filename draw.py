import datetime as dt
from PIL import Image, ImageDraw, ImageColor, ImageFont
from font_source_sans_pro import SourceSansPro ##
from typing import List

from data import Arrival



def draw(stop_name: str, now: dt.datetime, arrivals: List[Arrival]) -> Image:
    arrivals = [a for a in arrivals if a.when >= now]
    arrivals.sort(key=lambda arrival: arrival.when)
    uptown = [a for a in arrivals if a.direction == 'N']
    downtown = [a for a in arrivals if a.direction == 'S']

    IMG_WIDTH = 800
    IMG_HEIGHT = 480
    CIRCLE_RADIUS = 24
    CIRCLE_PADDING = 8
    CELL_HEIGHT = (CIRCLE_RADIUS + CIRCLE_PADDING) * 2

    img = Image.new("P", (IMG_WIDTH, IMG_HEIGHT), ImageColor.colormap['black'])
    draw = ImageDraw.Draw(img)

    def write(text: str, *, x: float, y: float, anchor=None, color=ImageColor.colormap['white'], size=CELL_HEIGHT * 0.6):
        # _, _, w, h = FONT.getbbox(text)
        # # if center_x:
        # #     x -= w / 2
        # # if center_y:
        # #     y -= h / 2
        draw.text((x, y), text, color, ImageFont.truetype(SourceSansPro, size=size), anchor=anchor)

    def draw_arrival(arrival: Arrival, *, x: float, i: int):
        draw.line([(x, (i + 2) * CELL_HEIGHT),
                   (x + IMG_WIDTH / 2, (i + 2) * CELL_HEIGHT)],
                  '#ffffff')
        draw.circle((x + CIRCLE_RADIUS + CIRCLE_PADDING, (i + 2.5) * CELL_HEIGHT),
                    CIRCLE_RADIUS,
                    arrival.route.color)
        write(arrival.route.id,
              x=x + CIRCLE_RADIUS + CIRCLE_PADDING,
              y=(i + 2.5) * CELL_HEIGHT,
              anchor='mm',
              color=arrival.route.text_color)
        minutes = arrival.wait_minutes(now)
        write('1 minute' if minutes == 1 else f'{minutes} minutes',
              x=x + (CIRCLE_RADIUS + CIRCLE_PADDING) * 2,
              y=(i + 2.5) * CELL_HEIGHT,
              color=ImageColor.colormap['yellow' if minutes == 0 else 'white'],
              anchor='lm')

    write(stop_name, x=IMG_WIDTH / 2, y=CELL_HEIGHT / 2, anchor='mm')
    write('Uptown', x=CIRCLE_PADDING, y=CELL_HEIGHT * 1.5, anchor='lm')
    write('Downtown', x=IMG_WIDTH / 2 + CIRCLE_PADDING, y=CELL_HEIGHT * 1.5, anchor='lm')

    for i, arrival in enumerate(uptown):
        draw_arrival(arrival, x=0, i=i)

    for i, arrival in enumerate(downtown):
        draw_arrival(arrival, x=IMG_WIDTH / 2, i=i)

    draw.text((IMG_WIDTH / 2, CELL_HEIGHT),
              f'Updated at {now:%-I:%M %p}',
              fill=ImageColor.colormap['green'],
              font=ImageFont.truetype(SourceSansPro, size=18),
              anchor='mm')

    return img
