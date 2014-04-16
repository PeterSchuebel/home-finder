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
    
    def __eq__(self, rhs):
        return (self.place==rhs.place and self.distance==rhs.distance and 
                self.duration==rhs.duration and self.directions==rhs.directions)

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
    
    def __eq__(self, rhs):
        if self.name!=rhs.name or self.abbrev!=rhs.abbrev:
            return False
        # check list in both directions (this, other), since order could be different
        for d in self.distance_to_places:
            if d not in rhs.distance_to_places:
                return False
        for d in rhs.distance_to_places:
            if d not in self.distance_to_places:
                return False
        return True

    def string_list(self):
        stringlist = [self.name, self.abbrev]
        for dp in self.distance_to_places:
            stringlist.extend(dp.string_list())
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
        
        
def read_stations(stations_filename):
    stations = list()
    with open(stations_filename, 'r') as stations_file:
        stations_reader = csv.reader(stations_file, delimiter=',') 
        for row in stations_reader:
            station = Station(row[0], row[1])
            #read all distance info as a 3-tuple
            for idx in range(2,len(row), 3):
                place = row[idx]
                dist = row[idx+1]
                dur = row[idx+2]
                distpl = DistanceToPlace(place, dist, dur, None)
                station.distance_to_places.append(distpl)
            stations.append(station)
                
    # remove entry from header
    if stations and stations[0].name=='Station name':
        stations = stations[1:]
    logger.info("Found %d rail stations in CSV file '%s'!", len(stations), stations_filename)
    return stations

def get_stations_close_to(src_stations, place_or_postcode, max_distance_in_m=50000):
    stations = list()
    errors = dict()
    for station in src_stations:
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

def merge_stations(stations1, stations2):
    stations_merge = list()
    for st1 in stations1:
        for st2 in stations2:
            if st1.name==st2.name:
                st = copy.deepcopy(st1)
                # copy all new distance info without duplicates
                unique_distpl = set()
                for distpl in st.distance_to_places:
                    unique_distpl.add(distpl)
                for distpl in st2.distance_to_places:
                    if distpl.place not in [d.place for d in unique_distpl]:
                        unique_distpl.add(distpl)
                st.distance_to_places = list(unique_distpl)
                stations_merge.append(st)
    logger.info("merged %d stations from both lists", len(stations_merge))        
    return stations_merge        

def address_to_filename(address):
    f = str(address).strip()
    f = f.replace(' ', '-').replace(',', '_').replace(':', '_').replace(';', '_')
    return f
    
if __name__ == '__main__':
    gmaps = googlemaps.GoogleMaps(gmaps_api_key, gmaps_referrer_url)
    
    # Options
    address0 = 'London, UK'
    address1 = 'SE1 1PP, UK'
    address2 = 'West Byfleet, UK'
    radius0 = 50000 #50km
    radius1 = radius2 = 45000 #45km
    uk_stations_filename = r'NationalRail_station_codes.csv'

    # import/export filenames depending on options
    stations_near_0_filename = r'stations_%dm_near_%s.csv' % (radius0, address_to_filename(address0))
    stations_near_1_filename = r'stations_%dm_near_%s.csv' % (radius1, address_to_filename(address1))
    stations_near_2_filename = r'stations_%dm_near_%s.csv' % (radius2, address_to_filename(address2))
    stations_merge_filename = r'stations_%dm_near_%s_and_%dm_near_%s.csv' % (
            radius1, address_to_filename(address1), radius2, address_to_filename(address2))

    # all UK rail stations
    uk_stations = read_stations(uk_stations_filename)

    # do this 3 times:
    #   - load previously saved station list, or
    #   - query it from google maps and save it for later use
    
    # all rail stations in radius around London
    stations_near_0 = list()
    if not os.path.exists(stations_near_0_filename):
        stations_near_0 = get_stations_close_to(uk_stations, address0, radius0)
        write_stations(stations_near_0, stations_near_0_filename)
    else:
        stations_near_0 = read_stations(stations_near_0_filename)

    # all rail stations in radius around my work
    stations_near_1 = list()
    if not os.path.exists(stations_near_1_filename):
        stations_near_1 = get_stations_close_to(stations_near_0, address1, radius1)
        write_stations(stations_near_1, stations_near_1_filename)
    else:
        stations_near_1 = read_stations(stations_near_1_filename)

    # all rail stations in radius around Dori's work
    stations_near_2 = list()
    if not os.path.exists(stations_near_2_filename):
        stations_near_2 = get_stations_close_to(stations_near_0, address2, radius2)
        write_stations(stations_near_2, stations_near_2_filename)
    else:
        stations_near_2 = read_stations(stations_near_2_filename)

    # merge stations near place 1 and 2 into common set (union)
    stations_merge = list()
    if not os.path.exists(stations_merge_filename):
        stations_merge = merge_stations(stations_near_1, stations_near_2)
        write_stations(stations_merge, stations_merge_filename)
    else:
        stations_merge = read_stations(stations_merge_filename)
    
    # TODO:
    for st in stations_merge:
        pass
        