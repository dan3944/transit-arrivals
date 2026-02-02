import aiohttp
import argparse
import asyncio
import csv
import gpiod
import gpiodevice
import logging
import threading
from gpiod.line import Bias, Direction, Edge
from google.transit import gtfs_realtime_pb2
from typing import List

from data import Arrival
from display import Display


def main(stop_ids: List[str], refresh_rate: int):
    if not (1 <= len(stop_ids) <= 4):
        raise ValueError(f'len(stop_ids) must be between 1 and 4 inclusive (got {len(stop_ids)})')

    with open('gtfs_subway/stops.txt') as f:
        stop_id_to_name = {line['stop_id']: line['stop_name']
                           for line in csv.DictReader(f)}

    chip = gpiodevice.find_chip_by_platform()
    offset_to_stop_id = {
        chip.line_offset_from_id(button): stop_id
        for button, stop_id in zip([5, 6, 16, 24], stop_ids)
    }
    request = chip.request_lines(consumer='spectra6-buttons', config={
        offset: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING)
        for offset in offset_to_stop_id
    })
    thread = DisplayThread(stop_ids[0], stop_id_to_name, refresh_rate)
    thread.start()

    while True:
        for event in request.read_edge_events():
            stop_id = offset_to_stop_id.get(event.line_offset)
            if stop_id == thread.stop_id:
                continue

            if stop_id is None:
                logging.error(f'Offset "{event.line_offset}" not found in {offset_to_stop_id}')
                continue

            logging.info(f'Detected button press for stop_id {stop_id}')
            thread.terminate()
            thread = DisplayThread(stop_id, stop_id_to_name, refresh_rate)
            thread.start()


class DisplayThread:
    def __init__(self, stop_id: str, stop_id_to_name: dict[str, str], refresh_rate: int):
        self.stop_id = stop_id
        self.name = stop_id_to_name.get(stop_id, stop_id)
        self.refresh_rate = refresh_rate
        # We need to run _show_station() in a separate thread because read_edge_events()
        # is blocking, so it will never yield the asyncio loop to other tasks.
        self._thread = threading.Thread(target=self._show_station, name=self.name)
        self._cancel = threading.Event()

    def start(self):
        self._thread.start()

    def terminate(self):
        self._cancel.set()
        self._thread.join()

    def _show_station(self):
        display = Display(self.name)

        while not self._cancel.is_set():
            logging.info('Fetching data...')
            feeds = asyncio.run(_fetch_feeds([
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
                'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
                # Staten Island Railroad:
                # 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'
            ]))

            arrivals = [
                Arrival(stop, entity.trip_update.trip.route_id)
                for feed in feeds
                for entity in feed.entity
                for stop in entity.trip_update.stop_time_update
                if stop.arrival.time
            ]
            if self._cancel.is_set(): break
            logging.info('Updating image')
            display.refresh(a for a in arrivals if a.stop_id == self.stop_id)
            logging.info('Finished updating image')
            self._cancel.wait(timeout=self.refresh_rate)

        logging.info('Cancelled')


async def _fetch_feeds(urls: List[str]) -> List[gtfs_realtime_pb2.FeedMessage]:
    async with aiohttp.ClientSession() as session:
        async def fetch_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
            try:
                async with session.get(url=url) as response:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(await response.read())
                    return feed
            except Exception as e:
                logging.error(f'Exception when fetching from {url}: {e}')
                return gtfs_realtime_pb2.FeedMessage()

        return await asyncio.gather(*(fetch_feed(url) for url in urls))


'''
Example stop IDs:
    86th/Broadway: 121
    96th/Broadway: 120
    86th/Central Park West: A20
    Columbus Circle: A24
    Pelham Pkway/White Plains Rd: 211
    E 180th St: 213
'''

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s [%(threadName)s] %(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--stop_ids', required=True, nargs='+', help='The stop IDs to display (from stops.txt)')
    parser.add_argument('-r', '--refresh_rate', type=int, default=30, help='The refresh rate in seconds')
    args = parser.parse_args()
    main(args.stop_ids, args.refresh_rate)
