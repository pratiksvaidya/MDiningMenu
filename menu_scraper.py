from datetime import datetime
from bs4 import BeautifulSoup
import requests
from google.cloud import firestore
import selenium.webdriver as webdriver

def main():
    # Get dining hall locations
    michigan_dining = "https://dining.umich.edu/menus-locations/dining-halls/"
    request = requests.get(michigan_dining)

    soup = BeautifulSoup(request.text, "html.parser")

    dining_halls = soup.find('ul', id='contentnavlist').findAll('a', class_='level_2')

    # Get menu for each dining hall
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('headless')
    driver = webdriver.Chrome(options=chrome_options)

    menu = dict()
    for hall in dining_halls:
        if hall.text == 'Select Access':
            continue

        driver.get(hall['href'])
        soup = BeautifulSoup(driver.page_source, features='html.parser')

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

        menu[hall.text.strip()] = courses

    driver.close()

    # Store data to firebase db
    database = firestore.Client(project='michigan-dining-menu')
    date = datetime.now().strftime('%Y-%m-%d')
    halls_ref = database.collection(date)

    for hall in menu:
        hall_ref = halls_ref.document(hall.title())

        for meal in menu[hall]:
            meal_ref = hall_ref.collection(meal)

            for station in menu[hall][meal]:
                meal_ref.document(station).set({
                    'items': menu[hall][meal][station]
                })

if __name__ == "__main__":
    main()
