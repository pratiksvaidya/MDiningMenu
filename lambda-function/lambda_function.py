from datetime import datetime
from datetime import timedelta
import requests

##############################
# Builders
##############################


def build_plain_speech(body):
    speech = {}
    speech['type'] = 'PlainText'
    speech['text'] = body
    return speech


def build_response(message, session_attributes={}):
    response = {}
    response['version'] = '1.0'
    response['sessionAttributes'] = session_attributes
    response['response'] = message
    return response


def build_simple_card(title, body):
    card = {}
    card['type'] = 'Simple'
    card['title'] = title
    card['content'] = body
    return card

##############################
# Process Data
##############################

def build_menu_url(meal, location, station):
    now = datetime.now() - timedelta(hours=5)
    date = now.strftime('%Y-%m-%d')

    if station:
        return f'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/beta/{date}/halls/{location}/{meal}/{station}'
    
    return f'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/beta/{date}/halls/{location}/{meal}'

def build_item_url(item):
    now = datetime.now() - timedelta(hours=5)
    date = now.strftime('%Y-%m-%d')

    return f'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/beta/{date}/items/{item}'

def get_menu_data(url, station):
    request = requests.get(url).json()

    if 'error' in request:
        return []

    if station:
        return [(station, request['fields']['items']['arrayValue']['values'])]
    
    station_data = request['documents']
    stations = list()
    for station in station_data:
        name = station['name'].split('/')[-1]
        items = station['fields']['items']['arrayValue']['values']
        stations.append((name, items))

    return stations

def get_item_data(url):
    request = requests.get(url).json()

    if 'error' in request:
        return []

    location_data = request['fields']
    locations = list()
    for location in location_data.items():
        name = location[0]
        station = location[1]['mapValue']['fields']['station']['stringValue'] 
        meal = location[1]['mapValue']['fields']['meal']['stringValue']
        locations.append([name, station, meal])
    
    return locations

def build_menu_response(meal, location, station=None):
    url = build_menu_url(meal, location, station)
    data = get_menu_data(url, station)

    if len(data) == 0:
        if station:
            return "Sorry, we don't have any information about the " + station + " station's " + meal + " menu at " + location + " today."

        return "Sorry, we don't have any information about " + meal + " at " + location + " today."

    response = "Here is the " + meal + " menu at " + location + " today: "
    for station in data:
        name = station[0]
        items = station[1]

        response = response + 'The ' + name + ' station is serving '
        for item in items:
            response = response + item['stringValue'] + ", "

        response = response[:-2] + '. '

    return response[:-1]

def build_item_search_response(item):
    url = build_item_url(item)
    data = get_item_data(url)

    if len(data) == 0:
        return 'Sorry, ' + item + ' doesn\'t seem to be served today at any Michigan Dining locations.'
    
    # TODO: Handle singular/plural items in response
    response = 'Here are the locations where ' + item + ' are being served today: '
    for location in data:
        name = location[0]
        station = location[1]
        meal = location[2]

        response = response + ' ' + name + '\'s ' + station + ' station during ' + meal + ', '

    return response[:-2]

##############################
# Responses
##############################


def conversation(title, body, session_attributes):
    speechlet = {}
    speechlet['outputSpeech'] = build_plain_speech(body)
    speechlet['card'] = build_simple_card(title, body)
    speechlet['shouldEndSession'] = False
    return build_response(speechlet, session_attributes=session_attributes)


def statement(title, body):
    speechlet = {}
    speechlet['outputSpeech'] = build_plain_speech(body)
    speechlet['card'] = build_simple_card(title, body)
    speechlet['shouldEndSession'] = True
    return build_response(speechlet)


def continue_dialog():
    message = {}
    message['shouldEndSession'] = False
    message['directives'] = [{'type': 'Dialog.Delegate'}]
    return build_response(message)


##############################
# Custom Intents
##############################


def dining_hall_meal_intent(event, context):
    dialog_state = event['request']['dialogState']

    if dialog_state in ("STARTED", "IN_PROGRESS"):
        return continue_dialog()

    elif dialog_state == "COMPLETED":
        meal = event['request']['intent']['slots']['Meal']['value'].title()
        location = event['request']['intent']['slots']['Location']['resolutions'] \
                        ['resolutionsPerAuthority'][0]['values'][0]['value']['name'].title()
        
        if 'value' in event['request']['intent']['slots']['Station']:
            station = event['request']['intent']['slots']['Station']['resolutions'] \
                        ['resolutionsPerAuthority'][0]['values'][0]['value']['name'].title()
        else:
            station = None

        title = meal + ' at ' + location
        menu = build_menu_response(meal, location, station)

        return statement(title, menu)

    return statement("dining_hall_meal_intent", "No dialog")

def item_search_intent(event, context):
    dialog_state = event['request']['dialogState']

    if dialog_state in ("STARTED", "IN_PROGRESS"):
        return continue_dialog()

    elif dialog_state == "COMPLETED":
        item = event['request']['intent']['slots']['item']['value'].title()
        
        title = 'Where can I find ' + item + ' today?'
        locations = build_item_search_response(item)

        return statement(title, locations)

    return statement("item_search_intent", "No dialog")


##############################
# Required Intents
##############################


def cancel_intent():
    title = "Exit Michigan Dining"
    body = "Thanks for using the Michigan Dining skill on Alexa! Have a great day!"
    return statement(title, body)


def help_intent():
    title = "Michigan Dining Help"
    body = "Looking for help? Try asking for the menu at a UM dining hall. For example, you can ask, What's for dinner at Mojo today?"
    return conversation(title, body, {})


def stop_intent():
    title = "Exit Michigan Dining"
    body = "Thanks for using the Michigan Dining skill on Alexa! Have a great day!"
    return statement(title, body)


##############################
# On Launch
##############################


def on_launch(event, context):
    title = "Welcome to Michigan Dining!"
    body = "You can ask me for today's menu for any UM location. Give it a try!"
    return conversation(title, body, {})


##############################
# Routing
##############################


def intent_router(event, context):
    intent = event['request']['intent']['name']

    # Custom Intents

    if intent == "DiningHallMeal":
        return dining_hall_meal_intent(event, context)

    if intent == "ItemSearch":
        return item_search_intent(event, context)

    # Required Intents

    if intent == "AMAZON.CancelIntent":
        return cancel_intent()

    if intent == "AMAZON.HelpIntent":
        return help_intent()

    if intent == "AMAZON.StopIntent":
        return stop_intent()


##############################
# Program Entry
##############################


def lambda_handler(event, context):
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event, context)

    elif event['request']['type'] == "IntentRequest":
        return intent_router(event, context)
