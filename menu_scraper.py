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

        course_names = soup.find('div', id='mdining-items').findAll('h3')
        course_info = soup.find('div', id='mdining-items').findAll('div', class_='courses')

        hall_menu = dict()

        for i, course in enumerate(course_info):
            items = course.findAll('div', class_='item-name')

            for j, item in enumerate(items):
                items[j] = item.text.strip()

            hall_menu[course_names[i].text.strip()] = items

        menu[hall.text.strip()] = hall_menu

    driver.close()

    # Store data to firebase db
    database = firestore.Client(project='michigan-dining-menu')
    locations_ref = database.collection('locations')

    for hall in menu:
        hall_ref = locations_ref.document(hall.title())

        for course in menu[hall]:
            course_ref = hall_ref.collection(datetime.now().strftime('%Y-%m-%d')).document(course)
            course_ref.set({
                'items': menu[hall][course]
            })

if __name__ == "__main__":
    main()
