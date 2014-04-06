#!python.exe
import csv
import copy
import logging
import logging.handlers
import os
import time
import traceback

# 3rd party APIs:
import googlemaps  #http://py-googlemaps.sourceforge.net/

gmaps_wait = 0.1 #seconds
gmaps_api_key = "" #needed for geocoding only
gmaps_referrer_url = "" #needed only for local search

logger = None
def setup_logger():
    log = logging.getLogger('find_distances')
    handler = logging.FileHandler('find_distances_log.txt')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log
logger = setup_logger()


class DistanceToPlace(object):
    def __init__(self, place_name, distance_in_m, duration_in_s, gmaps_directions):
        self.place = str(place_name)
        self.distance = float(distance_in_m)
        self.duration = float(duration_in_s)
        self.directions = gmaps_directions

    def string_list(self):
        return [self.place, self.distance, self.duration]
    
    def to_csv(self):
        return "%s, %f, %f" % (
                self.place, self.distance, self.duration)
    
    def __repr__(self):
        return "%s, %f, %f, %s" % (
                self.place, self.distance, self.duration, str(self.directions))
    
    def __str__(self):
        return "name:\t\t%s\ndistance:\t%f\nduration:\t%f\ndirections:\t%s" % (
                self.place, self.distance, self.duration, str(self.directions))
                
        
class Station(object):
    def __init__(self, name, abbrev):
        self.name = str(name)
        self.abbrev = str(abbrev)
        self.distance_to_places = list() #DistanceToPlace

    def string_list(self):
        stringlist = [self.name, self.abbrev]
        for dp in self.distance_to_places:
            stringlist.append(dp.string_list())
        return stringlist
    
    def to_csv(self):
        text = "%s, %s" % (self.name, self.abbrev)
        for dp in self.distance_to_places:
            text += ", %s" % (dp.to_csv())
        return text
    
    def __repr__(self):
        text = "%s, %s" % (self.name, self.abbrev)
        for dp in self.distance_to_places:
            text += ", %s" % (dp.__repr__())
        return text
    
    def __str__(self):
        text = "%s, %s" % (self.name, self.abbrev)
        for dp in self.distance_to_places:
            text += ", %s" % (dp.__str__())
        return text
        
        
def read_stations(uk_stations_filename=r'C:\data\TfL\NationalRail_station_codes.csv'):
    uk_stations = list()
    with open(uk_stations_filename, 'r') as uk_stations_file:
        stations_reader = csv.reader(uk_stations_file, delimiter=',') 
        for row in stations_reader:
            uk_stations.append(Station(row[0], row[1]))
    # remove entry from header
    if uk_stations and uk_stations[0].name=='Station name':
        uk_stations = uk_stations[1:]
    logger.info("Found %d UK rail stations in CSV file '%s'!", len(uk_stations), uk_stations_filename)
    return uk_stations

def get_uk_stations_close_to(place_or_postcode, max_distance_in_m=50000):
    stations = list()
    uk_stations = read_stations()
    errors = dict()
    for station in uk_stations:
        station_place = "%s, UK" % (station.name)
        logger.info("looking for directions from '%s' to '%s' ...", station_place, place_or_postcode)
        try:
            dirs = gmaps.directions(station_place, place_or_postcode)
        except googlemaps.GoogleMapsError as e:
            logger.error(str(e))
            logger.error(traceback.format_exc())
            errors[station_place] = station
            #break  #replace 'continue' with 'break' for testing
            continue
        dur = dirs['Directions']['Duration']['seconds']
        dist = dirs['Directions']['Distance']['meters']
        if dist <= max_distance_in_m:
            logger.info("matched distance: %d meters", dist)
            matched_station = copy.deepcopy(station)
            distance_to_place = DistanceToPlace(place_or_postcode, dist, dur, dirs)
            matched_station.distance_to_places.append(distance_to_place)
            stations.append(matched_station)
        time.sleep(gmaps_wait)
    logger.info("encountered %d errors!", len(errors))
    if errors:
        logger.warning("List of failed stations:\n%s", [e.to_csv() for e in errors.values()])
    return stations

def write_stations(stations, csv_filename):
    with open(csv_filename, 'w') as stations_file:
        stations_writer = csv.writer(stations_file, delimiter=',')
        for s in stations:
            stations_writer.writerow(s.string_list())
    
    
if __name__ == '__main__':
    gmaps = googlemaps.GoogleMaps(gmaps_api_key, gmaps_referrer_url)
    stations_near_us_filename = r'stations_near_London.csv'
    stations_near_d3_filename = r'stations_near_d3.csv'
    stations_near_mbh_filename = r'stations_near_mbh.csv'
    
    stations_near_us = list()
    if not os.path.exists(stations_near_us_filename):
        stations_near_us = get_uk_stations_close_to('London, UK', 50000)
        write_stations(stations_near_us, stations_near_us_filename)
    else:
        stations_near_us = read_stations(stations_near_us_filename)
    