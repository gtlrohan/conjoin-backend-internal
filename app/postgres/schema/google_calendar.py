from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.postgres.database import Base


class CalendarEvent(Base):
    __tablename__ = "GoogleCalendarEvents"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    kind = Column(String, nullable=False)
    etag = Column(String, nullable=False)
    status = Column(String)
    htmlLink = Column(String)
    created = Column(DateTime)
    updated = Column(DateTime)
    summary = Column(String)
    description = Column(String)
    location = Column(String)
    colorId = Column(String)
    endTimeUnspecified = Column(Boolean)
    recurrence = Column(JSONB)
    recurringEventId = Column(String)
    transparency = Column(String)
    visibility = Column(String)
    iCalUID = Column(String)
    sequence = Column(Integer)
    hangoutLink = Column(String)
    anyoneCanAddSelf = Column(Boolean)
    guestsCanInviteOthers = Column(Boolean)
    guestsCanModify = Column(Boolean)
    guestsCanSeeOtherGuests = Column(Boolean)
    privateCopy = Column(Boolean)
    locked = Column(Boolean)
    source_url = Column(String)
    source_title = Column(String)
    eventType = Column(String)

    creator_id = Column(String, ForeignKey("GoogleEventCreators.id"))
    organizer_id = Column(String, ForeignKey("GoogleEventOrganizers.id"))
    start_id = Column(String, ForeignKey("GoogleEventDates.id"))
    end_id = Column(String, ForeignKey("GoogleEventDates.id"))

    # Relationship to User
    user = relationship("User", back_populates="google_calendar_event")

    creator = relationship("EventCreator", back_populates="events")
    organizer = relationship("EventOrganizer", back_populates="events")
    start = relationship("EventDate", foreign_keys=[start_id])
    end = relationship("EventDate", foreign_keys=[end_id])
    attendees = relationship("EventAttendee", back_populates="event")
    reminders = relationship("EventReminder", back_populates="event")
    conference_data = relationship("ConferenceData", uselist=False, back_populates="event")


class EventCreator(Base):
    __tablename__ = "GoogleEventCreators"
    id = Column(String, primary_key=True, index=True)
    email = Column(String)
    displayName = Column(String)
    self_field = Column(Boolean)

    events = relationship("CalendarEvent", back_populates="creator")


class EventOrganizer(Base):
    __tablename__ = "GoogleEventOrganizers"
    id = Column(String, primary_key=True, index=True)
    email = Column(String)
    displayName = Column(String)
    self_field = Column(Boolean)

    events = relationship("CalendarEvent", back_populates="organizer")


class EventDate(Base):
    __tablename__ = "GoogleEventDates"
    id = Column(String, primary_key=True, index=True)
    date = Column(Date)
    dateTime = Column(DateTime)
    timeZone = Column(String)


class EventAttendee(Base):
    __tablename__ = "GoogleEventAttendees"
    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("GoogleCalendarEvents.id"))
    email = Column(String)
    displayName = Column(String)
    organizer = Column(Boolean)
    self_field = Column(Boolean)
    resource = Column(Boolean)
    optional = Column(Boolean)
    responseStatus = Column(String)
    comment = Column(String)
    additionalGuests = Column(Integer)

    event = relationship("CalendarEvent", back_populates="attendees")


class EventReminder(Base):
    __tablename__ = "GoogleEventReminders"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("GoogleCalendarEvents.id"))
    method = Column(String)
    minutes = Column(Integer)

    event = relationship("CalendarEvent", back_populates="reminders")


class ConferenceData(Base):
    __tablename__ = "GoogleConferenceData"
    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("GoogleCalendarEvents.id"))
    createRequest = Column(JSONB)
    entryPoints = Column(JSONB)
    conferenceSolution = Column(JSONB)
    conferenceId = Column(String)
    signature = Column(String)
    notes = Column(String)

    event = relationship("CalendarEvent", back_populates="conference_data")
