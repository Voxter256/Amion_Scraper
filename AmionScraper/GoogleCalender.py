# from __future__ import print_function
import httplib2
import os
import re
import datetime
import json

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from difflib import get_close_matches

from .Base import Session
from .Physician import Physician
from .Vaction import Vacation
from .BlockedDays import BlockedDays
from .Authentication import Authentication


class CalendarReader:

    def __init__(self):
        super().__init__()
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart.json')
        self.credential_path = credential_path

        self.session, self.authentication_data = self.get_authentication_data()

    @staticmethod
    def get_authentication_data():
        session = Session()
        return session, session.query(Authentication).first()

    def get_credentials(self):
        try:
            import argparse
            flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
            flags.noauth_local_webserver = True
        except ImportError:
            flags = None

        # If modifying these scopes, delete your previously saved credentials
        # at ~/.credentials/calendar-python-quickstart.json
        SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
        CLIENT_SECRET_FILE = '../client_secret.json'
        APPLICATION_NAME = 'Google Calendar API Python Quickstart'

        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        credential_path = self.credential_path
        if not os.path.isfile(credential_path):
            # credentials kept up to date in database to allow for ephemeral filesystems
            credentials_file = open(credential_path, "w+")
            credentials_file.write(self.authentication_data.data)
            credentials_file.close()

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                print("yes")
                credentials = tools.run_flow(flow, store, flags)
            else:  # Needed only for compatibility with Python 2.6
                print("no")
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def store_credentials(self):
        # credentials kept up to date in database to allow for ephemeral filesystems
        credential_path = self.credential_path
        with open(credential_path) as credentials_file:
            new_authentication_data = credentials_file.read()
            self.authentication_data.data = new_authentication_data
            self.session.add(self.authentication_data)
            self.session.commit()

    def main(self):
        """Shows basic usage of the Google Calendar API.

        Creates a Google Calendar API service object and outputs a list of the next
        10 events on the user's calendar.
        """
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http, developerKey=self.authentication_data.developerKey)

        # now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        now = '2017-07-01T00:00:00Z'  # indicates UTC time

        print('Getting All Events')

        events_result = service.events().list(
            calendarId=self.authentication_data.calendarId, timeMin=now, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        self.process_events(events)
        self.store_credentials()

    def process_events(self, events):
        all_physicians = self.session.query(Physician).all()
        physician_dictionary = {}
        physician_name_list = []
        event_calendar_ids = []
        for physician in all_physicians:
            physician_name_split = physician.name.split(" ")
            first_name = physician_name_split[0]
            # first_initial = first_name[0:1] + ". "
            if len(physician_name_split) == 3:
                # one entry for each last name
                last_name_1 = physician_name_split[1]
                this_name_1 = first_name + " " + last_name_1
                physician_dictionary[this_name_1] = physician.id
                physician_name_list.append(this_name_1)

                # last_name_2 = physician_name_split[1]
                # this_name_2 = first_name + " " + last_name_2
                # physician_dictionary[this_name_2] = physician.id
                # physician_name_list.append(this_name_2)
            else:
                last_name = " ".join(physician_name_split[1:])
                this_name = first_name + " " + last_name
                physician_dictionary[this_name] = physician.id
                physician_name_list.append(this_name)

        for event in events:
            summary = event["summary"]
            start_date = datetime.datetime.strptime(event["start"]["date"], "%Y-%m-%d")
            end_date = datetime.datetime.strptime(event["end"]["date"], "%Y-%m-%d") - datetime.timedelta(days=1)
            calendar_id = event["id"]
            created_at = datetime.datetime.strptime(event["created"][:19], "%Y-%m-%dT%H:%M:%S")
            updated_at = datetime.datetime.strptime(event["updated"][:19], "%Y-%m-%dT%H:%M:%S")
            # print(summary + " " + start_date.strftime("%Y-%m-%dT%H:%M:%S") + " " + end_date.strftime("%Y-%m-%dT%H:%M:%S") + " " + calendar_id)
            # print(str(created_at) + " " + str(updated_at))

            # Store all calendar ids to see if any are missing and delete those entries
            event_calendar_ids.append(calendar_id)

            summary_split = re.split(' ((vaca)|(edu))', summary, re.IGNORECASE)
            physician_matches = get_close_matches(summary_split[0], physician_name_list, n=1, cutoff=0.9)
            if len(physician_matches) == 0:
                current_blocked_days = self.session.query(BlockedDays).filter(BlockedDays.calendar_id == calendar_id).first()
                if current_blocked_days is not None:
                    if updated_at > current_blocked_days.updated_at:
                        current_blocked_days.summary = summary
                        current_blocked_days.start_date = start_date
                        current_blocked_days.end_date = end_date
                        current_blocked_days.updated_at = updated_at
                        print("Updated Unknown Entry")
                        print(summary + " " + start_date.strftime("%Y-%m-%d") + " " +
                              end_date.strftime("%Y-%m-%d") + " " + calendar_id)
                else:
                    new_blocked_days = BlockedDays(summary=summary, calendar_id=calendar_id,
                                                   start_date=start_date, end_date=end_date,
                                                   created_at=created_at, updated_at=updated_at)
                    self.session.add(new_blocked_days)
                    print("Unknown Entry")
                    print(summary + " " + start_date.strftime("%Y-%m-%d") + " " +
                          end_date.strftime("%Y-%m-%d") + " " + calendar_id)

                continue
            this_physician = physician_matches[0]
            this_physician_id = physician_dictionary[this_physician]
            # print(this_physician + " " + str(this_physician_id))
            previous_entry = self.session.query(Vacation).filter(Vacation.calendar_id == calendar_id).first()
            if previous_entry is not None:
                if updated_at > previous_entry.updated_at:
                    previous_entry.start_date = start_date
                    previous_entry.end_date = end_date
                    previous_entry.physician_id = this_physician_id
                    previous_entry.updated_at = updated_at
            else:
                this_vacation = Vacation(
                    calendar_id=calendar_id, start_date=start_date, end_date=end_date,
                    physician_id=this_physician_id, created_at=created_at, updated_at=updated_at
                )
                self.session.add(this_vacation)

        # Delete Vacations days that no longer exist
        old_vacations = self.session.query(Vacation).filter(~Vacation.calendar_id.in_(event_calendar_ids))
        print(old_vacations.count())
        old_vacations.delete(synchronize_session=False)
        self.session.commit()
