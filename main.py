#import logging
import requests
from bs4 import BeautifulSoup
#import lxml
import datetime
#import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import calendar
import random
from dateutil.relativedelta import relativedelta
import cal_functions

#URL constants
communityevents_url = "https://calendar.fortsask.ca/default/Advanced?StartDate="
pool_schedule = "https://www.fortsask.ca/en/things-to-do/resources/Documents/Harbour-Pool/Swim-Schedule.pdf"
dropin_schedules_url = "https://recreation.fortsask.ca/CFS/public/category/browse/WDROPISCH"

#how many days in the future to look for events for at the DCC
dropin_days_to_scrape = 61 #92
#how many months into the future to look for community events
community_events_months_to_scrape = 6 #12

#calendar ID:
cal_id = "7j2uo10g1uf4vj02pl3p5rgkq0@group.calendar.google.com"

#user agent for scraping web pages, make a random list of popular ones to lazily avoid possible bans for scraping
user_agent_list = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
]
user_agent = random.choice(user_agent_list)

def get_dropin_links(url):
    links_dict = {}
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        info = soup.find_all( "div", {"class":"media-body"} )
        # get all the links to the pages that have the drop in calenders for the respective activities
        if info is not None:
            for i in range(len(info)):
                if i%2 == 1:
                    link = "https://recreation.fortsask.ca" + info[i].find('a')['href']
                    title = info[i].find('a').text
                    links_dict[title] = link
            #update the links from the main page to the link that takes input parameters
            for title in links_dict:
                activity_response = requests.get(links_dict[title], headers=headers)
                if activity_response.status_code == 200:
                    activity_soup = BeautifulSoup(activity_response.text, "lxml")
                    activity_link = "https://recreation.fortsask.ca" + activity_soup.find("div",{"class":"col-sm-9 hidden-xs"}).find("a")['href']
                    activity_link = activity_link.split('?')[0]
                    links_dict[title] = activity_link
                else:
                    links_dict[title] = None
    return links_dict

def get_event_type(bs_class):
    switch = {
    "calendar-bar-color-10": "Budget Meetings",
    "calendar-bar-color-11": "Canada Day",
    "calendar-bar-color-12": "City Events and Festivals",
    "calendar-bar-color-13": "Community Events",
    "calendar-bar-color-14": "Council Meetings",
    "calendar-bar-color-15": "FCSS",
    "calendar-bar-color-16": "Harbour Pool",
    "calendar-bar-color-17": "Municipal Election",
    "calendar-bar-color-18": "Public Engagement",
    "calendar-bar-color-19": "Shell Theatre",
    "calendar-bar-color-110": "Sportsplex",
    "calendar-bar-color-111": "Waste and Recycling Events"
    }
    return switch.get(bs_class, "")

def scrape_dropin_events(dcc_event_type, url, datespan):
    #scrape all the events for the next dropin_days_to_scrape days
    today = datetime.date.today()
    future = today + datetime.timedelta(days=datespan)
    date = today
    full_url = url + "?StartDate=" + str(today) + "&EndDate=" + str(future)
    print("Checking activity: " + dcc_event_type)
    headers = {'User-Agent': user_agent}
    #url + "?StartDate=2022-01-04&EndDate=2022-03-31"
    response = requests.get(full_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        info = soup.find( "table", {"class":"table"} )
        if info is not None:
            table_body = info.find('tbody')
            rows = table_body.find_all('tr')
            #parse out the details from each table row into an event
            for row in rows:
                cols = row.find_all('td')
                event_date = cols[0].text.split(',')[1].strip()
                event_date = datetime.datetime.strptime(event_date, "%d-%b-%y").strftime("%Y-%m-%d")
                start_time = cols[1].text.split('-')[0].strip()
                end_time = cols[1].text.split('-')[1].strip()
                loc = cols[4].text.strip()
                try:
                    desc = soup.find("div", {"class":"panel panel-primary"}).find("p").text
                except:
                    desc = ""
                if len(cols[3].text.strip()) > 1:
                    desc += "\n  Instructors: " + cols[3].text.strip()
                summ = dcc_event_type + " - " + cols[5].text.strip()
                #create the event
                event = cal_functions.create_event_json(event_date, start_time,end_time, loc, desc, summ)
                cal_functions.add_event_to_calendar(event, cal_id)

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
                event_location = event.find("div", {"class":"calendar-list-location"}).text.strip()
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

#get a list of all events for the future, starting from today
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

print("Gathering all drop in event details")
#gather links to all drop in event schedules
drop_in = get_dropin_links(dropin_schedules_url)

#iterate through all the different drop in events and create calendar entries for them all
for activity in drop_in:
    scrape_dropin_events(activity, drop_in[activity], dropin_days_to_scrape)
