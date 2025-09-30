import uuid
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.postgres.schema.google_calendar import (
    CalendarEvent,
    ConferenceData,
    EventAttendee,
    EventCreator,
    EventDate,
    EventOrganizer,
    EventReminder,
)


def create_events(events: List[Dict[str, str]], user_id: int, db: Session):
    created_events = []

    for event in events:
        # Create CalendarEvent object
        calendar_event = CalendarEvent(
            user_id=user_id,
            id=event.get("id"),
            kind=event.get("kind"),
            etag=event.get("etag"),
            status=event.get("status"),
            htmlLink=event.get("htmlLink"),
            created=datetime.strptime(event.get("created"), "%Y-%m-%dT%H:%M:%S.%fZ") if event.get("created") else None,
            updated=datetime.strptime(event.get("updated"), "%Y-%m-%dT%H:%M:%S.%fZ") if event.get("updated") else None,
            summary=event.get("summary"),
            description=event.get("description"),
            location=event.get("location"),
            colorId=event.get("colorId"),
            endTimeUnspecified=event.get("endTimeUnspecified"),
            recurrence=event.get("recurrence"),
            recurringEventId=event.get("recurringEventId"),
            transparency=event.get("transparency"),
            visibility=event.get("visibility"),
            iCalUID=event.get("iCalUID"),
            sequence=event.get("sequence"),
            hangoutLink=event.get("hangoutLink"),
            anyoneCanAddSelf=event.get("anyoneCanAddSelf"),
            guestsCanInviteOthers=event.get("guestsCanInviteOthers"),
            guestsCanModify=event.get("guestsCanModify"),
            guestsCanSeeOtherGuests=event.get("guestsCanSeeOtherGuests"),
            privateCopy=event.get("privateCopy"),
            locked=event.get("locked"),
            source_url=event.get("source", {}).get("url"),
            source_title=event.get("source", {}).get("title"),
            eventType=event.get("eventType"),
        )

        # Create and associate EventCreator object
        creator_data = event.get("creator")
        if creator_data:
            creator = EventCreator(
                id=creator_data.get("id") if creator_data.get("id") else str(uuid.uuid4()),
                email=creator_data.get("email"),
                displayName=creator_data.get("displayName"),
                self_field=creator_data.get("self"),
            )
            calendar_event.creator = creator

        # Create and associate EventOrganizer object
        organizer_data = event.get("organizer")
        if organizer_data:
            organizer = EventOrganizer(
                id=organizer_data.get("id") if organizer_data.get("id") else str(uuid.uuid4()),
                email=organizer_data.get("email"),
                displayName=organizer_data.get("displayName"),
                self_field=organizer_data.get("self"),
            )
            calendar_event.organizer = organizer

        # Create and associate EventDate objects for start and end
        start_data = event.get("start")
        if start_data:
            start = EventDate(
                id=start_data.get("id") if start_data.get("id") else str(uuid.uuid4()),
                date=start_data.get("date"),
                dateTime=start_data.get("dateTime"),
                timeZone=start_data.get("timeZone"),
            )
            calendar_event.start = start

        end_data = event.get("end")
        if end_data:
            end = EventDate(
                id=end_data.get("id") if end_data.get("id") else str(uuid.uuid4()),
                date=end_data.get("date"),
                dateTime=end_data.get("dateTime"),
                timeZone=end_data.get("timeZone"),
            )
            calendar_event.end = end

        # Create and associate EventAttendee objects
        attendees_data = event.get("attendees", [])
        attendees = []
        for attendee_data in attendees_data:
            attendee = EventAttendee(
                id=attendee_data.get("id") if attendee_data.get("id") else str(uuid.uuid4()),
                email=attendee_data.get("email"),
                displayName=attendee_data.get("displayName"),
                organizer=attendee_data.get("organizer"),
                self_field=attendee_data.get("self"),
                resource=attendee_data.get("resource"),
                optional=attendee_data.get("optional"),
                responseStatus=attendee_data.get("responseStatus"),
                comment=attendee_data.get("comment"),
                additionalGuests=attendee_data.get("additionalGuests"),
            )
            attendees.append(attendee)
        calendar_event.attendees = attendees

        # Create and associate EventReminder objects
        reminders_data = event.get("reminders", {}).get("overrides", [])
        reminders = []
        for reminder_data in reminders_data:
            reminder = EventReminder(method=reminder_data.get("method"), minutes=reminder_data.get("minutes"))
            reminders.append(reminder)
        calendar_event.reminders = reminders

        # Create and associate ConferenceData object
        conference_data = event.get("conferenceData")
        if conference_data:
            conference = ConferenceData(
                id=conference_data.get("id") if conference_data.get("id") else str(uuid.uuid4()),
                createRequest=conference_data.get("createRequest"),
                entryPoints=conference_data.get("entryPoints"),
                conferenceSolution=conference_data.get("conferenceSolution"),
                conferenceId=conference_data.get("conferenceId"),
                signature=conference_data.get("signature"),
                notes=conference_data.get("notes"),
            )
            calendar_event.conference_data = conference

        # Add CalendarEvent object to session
        db.add(calendar_event)

        # Append created event to the list
        created_events.append(calendar_event)

    # Commit the transaction
    db.commit()

    return created_events
