from bs4 import BeautifulSoup
from datetime import datetime
from google.cloud import firestore
import requests
import selenium.webdriver as webdriver

# Get dining hall locations

michigan_dining = "https://dining.umich.edu/menus-locations/dining-halls/"
request = requests.get(michigan_dining)

soup = BeautifulSoup(request.text, "html.parser")

dining_halls = soup.find('ul',id='contentnavlist').findAll('a', class_='level_2')

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

    for i in range(len(course_info)):
        items = course_info[i].findAll('div', class_='item-name')

        for j in range(len(items)):
            items[j] = items[j].text.strip()

        hall_menu[course_names[i].text.strip()] = items


    menu[hall.text.strip()] = hall_menu

driver.close()

# Store data to firebase db

db = firestore.Client(project='michigan-dining-menu')
locations_ref = db.collection('locations')

for hall in menu.keys():
    hall_ref = locations_ref.document(hall.title())

    for course in menu[hall].keys():
        course_ref = hall_ref.collection(datetime.now().strftime('%Y-%m-%d')).document(course)
        course_ref.set({
            'items': menu[hall][course]
        })
