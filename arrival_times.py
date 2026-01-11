import aiohttp
import asyncio
import csv
import datetime as dt
import tkinter as tk
from google.transit import gtfs_realtime_pb2
from PIL import ImageTk

from data import Arrival, Route
from draw import draw


async def fetch_feed(url: str, session) -> gtfs_realtime_pb2.FeedMessage:
    async with session.get(url=url) as response:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(await response.read())
        return feed


def main(stop_id: str):
    with open('gtfs_subway/routes.txt') as f:
        routes = {
            line['route_id']: Route(
                id=line['route_id'],
                color='#' + line.get('route_color', 'ffffff'),
                text_color='#' + line.get('route_text_color', '000000'),
            )
            for line in csv.DictReader(f)
        }

    with open('gtfs_subway/stops.txt') as f:
        stop_name = next((
            line['stop_name']
            for line in csv.DictReader(f)
            if line['stop_id'] == stop_id
        ), stop_id)

    root = tk.Tk()
    label = tk.Label(root)
    label.pack()

    async def refresh_image():
        urls = [
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
            # Staten Island Railroad:
            # 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'
        ]
        print('fetching data')
        async with aiohttp.ClientSession() as session:
            feeds = await asyncio.gather(*(fetch_feed(url, session) for url in urls))

        arrivals = [
            Arrival(stop, route=routes[entity.trip_update.trip.route_id])
            for feed in feeds
            for entity in feed.entity
            for stop in entity.trip_update.stop_time_update
            if stop.arrival.time
        ]
        photo = ImageTk.PhotoImage(draw(
            stop_name,
            dt.datetime.now(),
            [a for a in arrivals if a.stop_id == stop_id]))
        label.config(image=photo)
        label.image = photo
        print('updated image')
        label.after(10_000, lambda: loop.run_until_complete(refresh_image()))

    loop = asyncio.get_event_loop()
    root.after(1, lambda: loop.run_until_complete(refresh_image()))
    root.mainloop()


if __name__ == '__main__':
    stop_id_86_bway = '121'
    stop_id_96_bway = '120'
    stop_id_86_cpw = 'A20'
    stop_id_columbus_circle = 'A24'
    stop_id_pelham_pkwy = '504'
    main('213')
