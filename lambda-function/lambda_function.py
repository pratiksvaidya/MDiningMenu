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

def build_request_url(meal, location, station):
    now = datetime.now() - timedelta(hours=5)
    date = now.strftime('%Y-%m-%d')

    if station:
        return f'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/{date}/{location}/{meal}/{station}'
    
    return f'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/{date}/{location}/{meal}'

def get_data(url, station):
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

def build_menu_response(meal, location, station=None):
    url = build_request_url(meal, location, station)
    data = get_data(url, station)

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


##############################
# Required Intents
##############################


def cancel_intent():
    # NOTE: don't use CancelIntent as title it causes code reference error during certification
    return statement("CancelIntent", "You want to cancel")


def help_intent():
    # NOTE: same here don't use CancelIntent
    return statement("CancelIntent", "You want help")


def stop_intent():
    # NOTE: here also don't use StopIntent
    return statement("StopIntent", "You want to stop")


##############################
# On Launch
##############################


def on_launch(event, context):
    return statement("Welcome to Michigan Dining!", \
                     "You can ask me for today's menu for any UM location!")


##############################
# Routing
##############################


def intent_router(event, context):
    intent = event['request']['intent']['name']

    # Custom Intents

    if intent == "DiningHallMeal":
        return dining_hall_meal_intent(event, context)

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
