from AmionScraper.AmionScraper import AmionScraper
from AmionScraper.Base import Base, engine
from AmionScraper.GoogleCalender import CalendarReader

if __name__ == '__main__':

    scraper = AmionScraper()
    vacation_calendar = CalendarReader()

    Base.metadata.create_all(engine)
    scraper.main()
    vacation_calendar.main()

