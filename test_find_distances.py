#!python.exe
import find_distances

stations_in = [find_distances.Station("Raynes Park, UK", "RAY")]
stations_out = find_distances.get_stations_close_to(stations_in, "driving", "sw20 8dx, UK", 5000)
for s in stations_out:
    print s
