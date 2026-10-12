/**
 * Dates and times shown in the app. The API stores UTC; we always display campus time
 * (America/New_York, the backend's TIME_ZONE) so a meetup reads the same for both people,
 * wherever their device is set. Give School a time zone when a school outside Eastern joins.
 */
export const CAMPUS_TIME_ZONE = "America/New_York";

type DateInput = string | number | Date;

function formatter(options: Intl.DateTimeFormatOptions, locale?: string) {
  return new Intl.DateTimeFormat(locale, { timeZone: CAMPUS_TIME_ZONE, ...options });
}

const dayKeyFormat = formatter({ year: "numeric", month: "2-digit", day: "2-digit" }, "en-CA");
const timeFormat = formatter({ hour: "numeric", minute: "2-digit" });
const shortDateFormat = formatter({ month: "short", day: "numeric" });
const dateTimeFormat = formatter({ month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const weekdayDateFormat = formatter({ weekday: "short", month: "short", day: "numeric" });

/** The campus calendar day, as "2026-10-12", for grouping and same-day checks. */
export const dayKey = (value: DateInput) => dayKeyFormat.format(new Date(value));
export const isSameCampusDay = (a: DateInput, b: DateInput) => dayKey(a) === dayKey(b);

/** "4:30 PM" */
export const formatTime = (value: DateInput) => timeFormat.format(new Date(value));
/** "Oct 12" */
export const formatShortDate = (value: DateInput) => shortDateFormat.format(new Date(value));
/** "Oct 12, 4:30 PM" */
export const formatDateTime = (value: DateInput) => dateTimeFormat.format(new Date(value));
/** "Mon, Oct 12" */
export const formatWeekdayDate = (value: DateInput) => weekdayDateFormat.format(new Date(value));
