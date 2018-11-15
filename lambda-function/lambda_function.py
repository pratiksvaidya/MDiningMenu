import requests
from datetime import datetime
from datetime import timedelta

##############################
# Builders
##############################


def build_PlainSpeech(body):
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


def build_SimpleCard(title, body):
    card = {}
    card['type'] = 'Simple'
    card['title'] = title
    card['content'] = body
    return card


##############################
# Responses
##############################


def conversation(title, body, session_attributes):
    speechlet = {}
    speechlet['outputSpeech'] = build_PlainSpeech(body)
    speechlet['card'] = build_SimpleCard(title, body)
    speechlet['shouldEndSession'] = False
    return build_response(speechlet, session_attributes=session_attributes)


def statement(title, body):
    speechlet = {}
    speechlet['outputSpeech'] = build_PlainSpeech(body)
    speechlet['card'] = build_SimpleCard(title, body)
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
        location = event['request']['intent']['slots']['Location']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name'].title()
        # location = event['request']['intent']['slots']['Location']['value'].title()
        
        now = datetime.now() - timedelta(hours=5)
        date = now.strftime('%Y-%m-%d')
        base_url = 'https://firestore.googleapis.com/v1beta1/projects/michigan-dining-menu/databases/(default)/documents/locations/'

        url = base_url + location + "/" + date + "/" + meal
        request = requests.get(url)
        data = request.json()
        items = data['fields']['items']['arrayValue']['values']
        response = "Here is the " + meal + " menu at " + location + " today: " 
        for item in items:
            response = response + item['stringValue'] + ", " 
        
        return statement(meal + ' at ' + location, response[:-2])

    else:
        return statement("dining_hall_meal_intent", "No dialog")


##############################
# Required Intents
##############################


def cancel_intent():
    return statement("CancelIntent", "You want to cancel")	#don't use CancelIntent as title it causes code reference error during certification 


def help_intent():
    return statement("CancelIntent", "You want help")		#same here don't use CancelIntent


def stop_intent():
    return statement("StopIntent", "You want to stop")		#here also don't use StopIntent


##############################
# On Launch
##############################


def on_launch(event, context):
    return statement("Welcome to Michigan Dining!", "You can ask me for today's menu for any UM location!")


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