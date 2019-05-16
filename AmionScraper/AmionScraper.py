import os
import re
import requests

from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from sqlalchemy import func, and_

from .Base import Session
from .Physician import Physician
from .Position import Position
from .ScheduleUpdate import ScheduleUpdate
from .Service import Service
from .Shift import Shift


class AmionScraper:
    def __init__(self):
        self.session = Session()
        self.shifts_to_store = []

        self.services = {}
        self.physicians = {}

    def main(self):
        password = os.environ.get('AMION_PASSWORD')
        print(password)
        if not password:
            return False
        url_services = "http://www.amion.com/cgi-bin/ocs?Lo=" + password
        page = requests.get(url_services)
        file_string_regex = re.compile('=[a-z0-9!]+')
        file_string = file_string_regex.search(page.url).group()[1:]

        services = self.session.query(Service).all()
        for service in services:
            self.services[service.name] = service.id

        physicians = self.session.query(Physician).all()
        for physician in physicians:
            self.physicians[physician.name.lower()] = physician

        updated_schedule = self.check_for_updated_schedule(file_string)
        if updated_schedule:
            self.get_all_date_data(file_string)

    def check_for_updated_schedule(self, file_string):
        last_schedule_update_object = self.session.query(ScheduleUpdate).first()
        if last_schedule_update_object is None:
            last_schedule_update_object = ScheduleUpdate(id=1, update_date=datetime.min)
            self.session.add(last_schedule_update_object)
            self.session.flush()
        last_updated_datetime = last_schedule_update_object.update_date

        url_services = "http://www.amion.com/cgi-bin/ocs?Lo=" + file_string
        page = requests.get(url_services)
        html_data = page.content
        soup = BeautifulSoup(html_data, 'html5lib')
        regex_text = re.compile('Schedule last updated [A-Za-z]{3} [0-9]{1,2} [0-9:]+ [0-9]{4}')
        search_result = soup.body.find(text=regex_text)
        regex_date = re.compile('[A-Za-z]{3} [0-9]{1,2} [0-9:]+ [0-9]{4}')
        new_updated_date_string = regex_date.search(search_result).group()
        print(new_updated_date_string)
        new_string_split = new_updated_date_string.split(" ")

        # Make sure date and time is zero padded
        if len(new_string_split[1]) == 1:
            new_string_split[1] = "0" + str(new_string_split[1])
            new_updated_date_string = " ".join(new_string_split)
            print(new_updated_date_string)
        if len(new_string_split[2]) == 4:
            new_string_split[2] = "0" + str(new_string_split[2])
            new_updated_date_string = " ".join(new_string_split)
            print(new_updated_date_string)
        new_updated_datetime = datetime.strptime(new_updated_date_string, '%b %d %H:%M %Y')
        print(new_updated_datetime.strftime('%b %d %H:%M %Y'))

        if new_updated_datetime > last_updated_datetime:
            last_schedule_update_object.update_date = new_updated_datetime
            self.session.flush()
            return True
        return False

    def get_all_date_data(self, file_string):
        # start_date needs to have 0's for time
        start_date = datetime.combine(datetime.today().date() - timedelta(days=7), datetime.min.time())
        # start_date = datetime.strptime("08/01/2018", "%m/%d/%Y")

        stop_date = datetime.strptime("06/30/2020", "%m/%d/%Y")

        number_of_days = (stop_date - start_date).days + 1
        print(number_of_days)

        self.shifts_to_store = []

        for days in range(number_of_days):
            shift_date = start_date + timedelta(days=days)
            print(shift_date.strftime("%m/%d/%Y"))
            self.get_date_data(shift_date, file_string)

        # Delete all shifts from Shifts table
        self.session.query(Shift).delete()
        self.session.commit()

        # save_shifts_to_database
        self.session.bulk_save_objects(self.shifts_to_store)
        self.session.commit()

        # sometimes night float is scheduled for both day and night
        self.delete_duplicate_shifts()

    def get_date_data(self, shift_date, file_string):
        url_date_string = self.convert_date(shift_date)

        # Get core services (not call)
        url_services = "http://www.amion.com/cgi-bin/ocs?Lo=" + file_string + \
                       "&Syr=2017&Page=Alrots&Fsiz=0&Yjd=" + url_date_string
        page = requests.get(url_services)
        html_data = page.content
        shifts = self.scrape_page_for_shifts(html_data)
        print(shifts)
        self.store_shifts(shifts, shift_date)

        # Get call services
        url_call = "http://www.amion.com/cgi-bin/ocs?Lo=" + file_string + \
                   "&Syr=2017&Page=OnCall&Fsiz=0&Yjd=" + url_date_string
        page = requests.get(url_call)
        html_data = page.content
        shifts = self.scrape_page_for_shifts(html_data, is_call = True)
        print(shifts)
        self.store_shifts(shifts, shift_date, is_call=True)

    def store_shifts(self, shifts, shift_date, is_call=False):
        for shift in shifts:
            this_service = shift[0]
            this_physician = shift[1]
            this_position = shift[2]

            changes_made = False
            # Get/Insert Service
            if this_service not in self.services:
                service_record = Service(name=this_service, is_call=is_call)
                self.session.add(service_record)
                self.session.flush()
                self.services[service_record.name] = service_record.id
                changes_made = True
            # service_record = self.session.query(Service).filter(Service.name == this_service).first()
            # if service_record is None:

            # Get/Insert Physician

            # Check if comma separated
            if this_physician.find(', ') != -1:
                last, first = this_physician.split(', ')
                this_physician = first + " " + last

            # manual corrections to names
            this_physician = this_physician.replace('Nate A', 'Nathaniel A')
            this_physician = this_physician.replace('Jen B', 'Jennifer B')
            this_physician = this_physician.replace('Rob P', 'Robert P')

            this_physician_lowercase = this_physician.lower()  # to reduce errors between years

            if this_physician_lowercase not in self.physicians:
                # Insert Position if new Physician
                position_record = self.session.query(Position).filter(Position.name == this_position).first()
                if position_record is None:
                    position_record = Position(name=this_position)
                    self.session.add(position_record)
                    self.session.flush()
                physician_record = Physician(name=this_physician, position_id=position_record.id)
                self.session.add(physician_record)
                self.session.flush()
                self.physicians[this_physician_lowercase] = physician_record
                changes_made = True
            # Update Physician position_id
            else:
                physician_record = self.physicians[this_physician_lowercase]
                if physician_record.position.name != this_position:
                    position_record = self.session.query(Position).filter(Position.name == this_position).first()
                    if position_record is None:
                        position_record = Position(name=this_position)
                        self.session.add(position_record)
                        self.session.flush()
                    physician_record.position_id = position_record.id
                    self.session.flush()
                    changes_made = True

            # Insert Shift
            new_shift = Shift(
                shift_date=shift_date,
                service_id=self.services[this_service],
                physician_id=self.physicians[this_physician_lowercase].id)
            # self.session.add(new_shift)
            self.shifts_to_store.append(new_shift)
            if changes_made:
                self.session.commit()

    def delete_duplicate_shifts(self):
        counts = self.session\
            .query(
                Shift.physician_id,
                Shift.service_id,
                Shift.shift_date,
                func.count('*').label('count')
            ).group_by(
                Shift.physician_id,
                Shift.service_id,
                Shift.shift_date
            ).subquery('counts')

        query = self.session\
            .query(
                Shift.id, Shift.physician_id, Shift.service_id, Shift.shift_date, counts.c.count
            ).distinct(
                Shift.id, Shift.physician_id, Shift.service_id, Shift.shift_date
            ).filter(and_(
                Shift.physician_id == counts.c.physician_id,
                Shift.service_id == counts.c.service_id,
                Shift.shift_date == counts.c.shift_date,
                counts.c.count >= 2,)
            ).all()
        for index, row in enumerate(query):
            print(row)
            if index == 0:
                continue
            if row[1] == query[index-1][1] and row[2] == query[index-1][2] and row[3] == query[index-1][3]:
                self.session.query(Shift).filter(Shift.id == row[0]).delete()
                print("delete")
        self.session.commit()

    @staticmethod
    def scrape_page_for_shifts(html_data, is_call=False):
        soup = BeautifulSoup(html_data, 'html5lib')
        table_rows = soup.find_all("tr")
        begin_search = False
        shifts = []
        for row in table_rows:
            this_shift = []
            for td in row.find_all("td"):
                if td.text == "Service":
                    begin_search = True
                    break
                if not begin_search:
                    break
                text = td.text.strip().replace("\xa0", " ")
                if not text:
                    continue
                this_shift.append(text)
                if is_call and len(this_shift) == 4:
                    shifts.append((this_shift[0], this_shift[2], this_shift[3]))
                elif not is_call and len(this_shift) == 3:
                    shifts.append((this_shift[0], this_shift[1], this_shift[2]))
        return shifts

    @staticmethod
    def convert_date(desired_date):
        day_1 = datetime.strptime("12/31/1996", "%m/%d/%Y")
        difference_timedelta = desired_date - day_1
        url_date = difference_timedelta.days
        return str(url_date)
