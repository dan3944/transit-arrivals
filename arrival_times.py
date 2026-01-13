import aiohttp
import argparse
import asyncio
import csv
import datetime as dt
import logging
from google.transit import gtfs_realtime_pb2
from inky.auto import auto

from data import Arrival, Route
from draw import draw


async def fetch_feed(url: str, session) -> gtfs_realtime_pb2.FeedMessage:
    async with session.get(url=url) as response:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(await response.read())
        return feed


async def main(stop_id: str, refresh_rate: int):
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

    inky_display = auto()
    img = None

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

    while True:
        logging.info('Fetching data...')
        async with aiohttp.ClientSession() as session:
            feeds = await asyncio.gather(*(fetch_feed(url, session) for url in urls))

        arrivals = [
            Arrival(stop, route=routes[entity.trip_update.trip.route_id])
            for feed in feeds
            for entity in feed.entity
            for stop in entity.trip_update.stop_time_update
            if stop.arrival.time
        ]
        prev_img = img
        img = draw(stop_name,
                dt.datetime.now(),
                [a for a in arrivals if a.stop_id == stop_id])
        if prev_img is None:
            logging.info('Setting full image')
            inky_display.set_image(img)
        else:
            new_pixels = img.load()
            old_pixels = prev_img.load()
            diff_count = 0
            for x in range(img.width):
                for y in range(img.height):
                    if new_pixels[x, y] != old_pixels[x, y]:
                        inky_display.set_pixel(x, y, new_pixels[x, y])
                        diff_count += 1
            logging.info(f'Incrementally updating {diff_count} pixels')

        inky_display.show()
        logging.info('Updated image')
        await asyncio.sleep(refresh_rate)


'''
Example stop IDs:
    86th/Broadway: 121
    96th/Broadway: 120
    86th/Central Park West: A20
    Columbus Circle: A24
    Pelham Parkway: 504
    E 180th St: 213
'''

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--stop_id', required=True, help='The stop ID to display (from stops.txt)')
    parser.add_argument('-r', '--refresh_rate', type=int, default=10, help='The refresh rate in seconds')
    args = parser.parse_args()
    asyncio.run(main(args.stop_id, args.refresh_rate))
