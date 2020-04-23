import logging
import requests
from bs4 import BeautifulSoup
import lxml
import datetime
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import calendar
import random
from dateutil.relativedelta import relativedelta
import cal_functions

#URL constants
dropinsport_url = "https://recreation.fortsask.ca/CFS/public/Category/ClassList?CategoryGUID=15f3b83b-91f9-4a54-b35c-0a67c1708c36&StartDate="
dropinfitness_wellness_url = "https://recreation.fortsask.ca/CFS/public/Category/ClassList?CategoryGUID=a139707b-5b7d-429c-9bed-e4834a669b9f&StartDate="
dropinaquatics_url = "https://recreation.fortsask.ca/CFS/public/Category/ClassList?CategoryGUID=42ab1e5c-5788-4790-b6ff-d1ececc63c2a&StartDate="
communityevents_url = "https://calendar.fortsask.ca/default/Advanced?StartDate="
pool_schedule = "https://www.fortsask.ca/en/things-to-do/resources/Documents/Swim-Schedule.pdf"

#how many days in the future to look for events for at the DCC
DCC_days_to_scrape = 92
#how many months into the future to look for community events
community_events_months_to_scrape = 12

#calendar ID:
cal_id = "7j2uo10g1uf4vj02pl3p5rgkq0@group.calendar.google.com"

#user agent for scraping web pages, make a random list of popular ones to lazily avoid possible bans for scraping
user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1; rv:7.0.1) Gecko/20100101 Firefox/7.0.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
]
user_agent = random.choice(user_agent_list)

def get_event_type(bs_class):
    switch = {
    "calendar-bar-color-10": "Budget Meetings",
    "calendar-bar-color-11": "Canada Day",
    "calendar-bar-color-12": "Community Events",
    "calendar-bar-color-13": "City Events and Festivals",
    "calendar-bar-color-14": "Harbour Pool",
    "calendar-bar-color-15": "Public Engagement",
    "calendar-bar-color-16": "Shell Theatre"
    }
    return switch.get(bs_class, "")

def scrape_DCC_events(dcc_event_type, url, datespan):
    #scrape all the events for the next DCC_days_to_scrape days
    today = datetime.date.today()
    future = today + datetime.timedelta(days=datespan)
    date = today
    while date < future:
        print("Checking for events on " + str(date))
        #hit the web page and scrape it
        headers = {'User-Agent': user_agent}
        response = requests.get(url+str(date), headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml")
            info = soup.find( "table", {"class":"table"} )
            if info is not None:
                table_body = info.find('tbody')
                rows = table_body.find_all('tr')
                for row in rows:
                    #print("New event found for " + str(date) + ":\n")
                    cols = row.find_all('td')
                    for col in cols:
                        try:
                            link = "https://recreation.fortsask.ca" + col.find('a').get('href')
                            break
                        except:
                            link = None
                    cols = [ele.text.strip() for ele in cols]
                    if link is not None:
                        #now parse this link out and get the summary from it
                        headers = {'User-Agent': user_agent}
                        details = requests.get(link, headers=headers)
                        if details.status_code == 200:
                            detail_soup = BeautifulSoup(details.text, "lxml")
                            detail_info = detail_soup.find( "div", {"class":"panel panel-primary"} ).find('p').text.strip()
                    else:
                        detail_info = ""
                    if len(cols[3]) > 0:
                        detail_info += "\n Instructors: " + cols[3]
                    #we now have the data for our event of choice. Let's build the calendar entry
                    event = cal_functions.create_event_json(date, cols[0],cols[2], cols[4], detail_info, dcc_event_type + " - " + cols[1])
                    cal_functions.add_event_to_calendar(event, cal_id)
        date += datetime.timedelta(days=1)

def scrape_Community_events(url, this_month, current_month=True):
    last_day_of_month = calendar.monthrange(this_month.year,this_month.month)[1]
    if(current_month):
        start_day = str(this_month.day)
    else:
        start_day = "01"
    hp_url = communityevents_url + str(this_month.month) + "/" + start_day + "/" + str(this_month.year) + "&EndDate=" + str(this_month.month) + "/" + str(last_day_of_month) + "/" + str(this_month.year)
    headers = {'User-Agent': user_agent}
    response = requests.get(hp_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        info = soup.find_all( "div", {"class":"calendar-list-info-inner"} )  
        event_types = soup.find_all( "div", {"class":"calendar-list-calendar"})
        if info is not None:
            e = 0
            for event in info:
                e_type = get_event_type(event_types[e].find("div").attrs['class'][1])
                #event = [ele.text.strip() for ele in event]
                event_summary = e_type + " - " + event.find("h3").text.strip()
                event_location = event.find("div", {"id":"calendar-list-location"}).text.strip()
                if event.find("div", {"class":"calendar-list-content"}) is not None:
                    event_description = event.find("div", {"class":"calendar-list-content"}).text.strip()
                else:
                    event_description = ""
                if event_location == "Harbour Pool":
                    event_description+= "\nSee standard swim schedule at " + pool_schedule
                event_datetime = event.find("div", {"class":"calendar-list-time"}).text.strip().replace(",","").replace(".","")
                edt = event_datetime.split(" ")
                date = datetime.datetime.strptime(edt[1] + " " + edt[2] + " " + edt[3], '%B %d %Y').date()
                start = edt[5] + " " + edt[6].upper()
                if len(edt) < 8:
                    end = start
                else:
                    end = edt[8] + " " + edt[9].upper()
                
                #now create an event based on this information
                calendar_event = cal_functions.create_event_json(date, start,end, event_location, event_description, event_summary)
                cal_functions.add_event_to_calendar(calendar_event, cal_id)
                e+=1

#get a list of all events (up to 2500) for the future, starting from today
today = datetime.datetime.today()

#find and delete all events from today and into the future. Ensures this calendar is always in sync
while True:
    All_events_list = cal_functions.list_calendar_events(cal_id, today)
    cal_functions.remove_eventlist_from_calendar(All_events_list, cal_id)
    if len(All_events_list) == 0:
        break

print("Scraping Community events")
#Get all Community events from today until the end of the current month and add them to the calendar
scrape_Community_events(communityevents_url, today)
#check events as far into the future as you want.
for this_month in range(1, community_events_months_to_scrape):
    scrape_Community_events(communityevents_url, today + relativedelta(months=this_month), False)

#get all DCC events from the website and add them to the calendar
scrape_DCC_events("DCC Sports", dropinsport_url, DCC_days_to_scrape)
scrape_DCC_events("DCC Fitness/Wellness", dropinfitness_wellness_url, DCC_days_to_scrape)
scrape_DCC_events("HP Aquatics",dropinaquatics_url, DCC_days_to_scrape)
