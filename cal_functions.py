#Pretty much entirely taken from google developer site and https://karenapp.io/articles/2019/07/how-to-automate-google-calendar-with-python-using-the-calendar-api/

import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']

dir_path = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(dir_path, "credentials.json")

def get_calendar_service():

   creds = None
   # The file token.pickle stores the user's access and refresh tokens, and is
   # created automatically when the authorization flow completes for the first
   # time.
   if os.path.exists('token.pickle'):
       with open('token.pickle', 'rb') as token:
           creds = pickle.load(token)
   # If there are no (valid) credentials available, let the user log in.
   if not creds or not creds.valid:
       if creds and creds.expired and creds.refresh_token:
           creds.refresh(Request())
       else:
           flow = InstalledAppFlow.from_client_secrets_file(
               CREDENTIALS_FILE, SCOPES)
           creds = flow.run_local_server(port=0)

       # Save the credentials for the next run
       with open('token.pickle', 'wb') as token:
           pickle.dump(creds, token)

   service = build('calendar', 'v3', credentials=creds)
   return service

def list_calendar_events(calendar_id, min_date):
    service = get_calendar_service()
    # Call the Calendar API
    today_with_time = datetime.datetime(year=min_date.year,month=min_date.month,day=min_date.day)
    now = today_with_time.isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting List of events')
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        singleEvents=True,
        orderBy='startTime'
        ).execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    else:
        print('Found ' + str(len(events)) + ' events')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        #print(start, event['summary'])
    return events

def list_HP_calendar_events(calendar_id, min_date):
    service = get_calendar_service()
    # Call the Calendar API
    first_date_this_month = datetime.datetime(year=min_date.year,month=min_date.month,day=1)
    iso_first_date = first_date_this_month.isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting List of events')
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=iso_first_date,
        q="Harbour Pool",
        singleEvents=True,
        orderBy='startTime'
        ).execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    else:
        print('Found ' + str(len(events)) + ' events')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        #print(start, event['summary'])
    return events

def add_event_to_calendar(event_json, calendar_id):
    service = get_calendar_service()
    result = service.events().insert(calendarId=calendar_id, body=event_json).execute()
    print("Event ID [" + result['id'] + "] created")

def create_event_json(eventdate, starttime, endtime, location, description, summary):
    datestart = datetime.datetime.strptime(starttime, "%I:%M %p")
    fixstarttime = str(eventdate) + "T" + datestart.strftime("%H:%M:%S")
    dateend = datetime.datetime.strptime(endtime, "%I:%M %p")
    fixendtime = str(eventdate) + "T" + dateend.strftime("%H:%M:%S")
    event = {
    'summary': summary,
    'location': location,
    'description': description,
    'start': {
    'dateTime': fixstarttime,
    'timeZone': 'America/Edmonton',
    },
    'end': {
    'dateTime': fixendtime,
    'timeZone': 'America/Edmonton',
    },
    }
    #print(event)
    return event

def remove_event_from_calendar(event_id, calendar_id):
    service = get_calendar_service()
    try:
        service.events().delete(calendarId=calendar_id,eventId=event_id).execute()
    except googleapiclient.errors.HttpError:
        print("Failed to delete event ID [" + event_id + "]")
    #print("Event deleted")

def remove_eventlist_from_calendar(eventlist, calendar_id):
    service = get_calendar_service()
    for event in eventlist:
        try:
            service.events().delete(calendarId=calendar_id,eventId=event['id']).execute()
        except googleapiclient.errors.HttpError:
            print("Failed to delete event ID [" + event_id + "]")
    print(str(len(eventlist)) + " events deleted")