import requests
from datetime import datetime
from bs4 import BeautifulSoup
from google.cloud import firestore
import os

def main():
    # Get dining hall locations
    request = requests.get("https://dining.umich.edu/menus-locations/dining-halls/")
    soup = BeautifulSoup(request.text, "lxml")
    dining_halls = soup.find('ul', id='contentnavlist').findAll('a', class_='level_2')

    # Get menu for each dining hall
    menu = dict()
    item_search = dict()
    for hall in dining_halls:
        if hall.text == 'Select Access':
            continue

        request = requests.get(hall['href'])
        soup = BeautifulSoup(request.content, features='lxml')

        courses = dict()
        courses_elements = soup.find('div', id='mdining-items').findAll('div', class_='courses')
        for course in courses_elements:
            meal = course.previous_sibling.previous_sibling.text.strip()
            courses[meal] = dict()

            stations_elements = course.findAll('h4')
            for station in stations_elements:
                station_name = station.text.strip()
                courses[meal][station_name] = list()

                item_elements = station.next_sibling.next_sibling.findAll('div', class_='item-name')
                for item in item_elements:
                    item_name = item.text.strip()
                    courses[meal][station_name].append(item_name)

                    if item_name in item_search:
                        item_search[item_name].append({'hall': hall.text, 'meal': meal, 'station': station_name})
                    else:
                        item_search[item_name] = [{'hall': hall.text, 'meal': meal, 'station': station_name}]

        menu[hall.text.strip()] = courses

    # Store data to firebase db
    database = firestore.Client(project='michigan-dining-menu')
    date = datetime.now().strftime('%Y-%m-%d')

    # Items by Location
    halls_ref = database.collection('beta', date, 'halls')
    for hall in menu:
        hall_ref = halls_ref.document(hall.title())

        for meal in menu[hall]:
            meal_ref = hall_ref.collection(meal)

            for station in menu[hall][meal]:
                meal_ref.document(station).set({
                    'items': menu[hall][meal][station]
                })
    
    # Locations by Item
    for item_name, locations in item_search.items():
        if '/' in item_name:
            # TODO: handle item names containing "/w"
            continue

        item_ref = database.document('beta', date, 'items', item_name.title())
        item_ref.set({loc['hall']: loc for loc in locations})

if __name__ == "__main__":
    main()
