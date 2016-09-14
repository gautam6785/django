from decimal import Decimal

# The number of days to use as a month in the calculation of monthly average users.
MAU_DURATION_DAYS = 28

# The number of days to use as a month in the calculation of monthly recurring revenue.
MRR_DURATION_DAYS = 28

# Event IDs indicating the start of a user session.
# Includes app_start and app_foreground.
SESSION_START_EVENT_IDS = [2, 3]

# Event IDs indicating the end of a user session.
# Includes app_terminate, app_background, and logout.
SESSION_STOP_EVENT_IDS  = [1, 4, 8]

# Event IDs indicating the start or end of a user session.
SESSION_BOUNDARY_EVENT_IDS = SESSION_START_EVENT_IDS + SESSION_STOP_EVENT_IDS

# The proportion of app and in-app purchase proceeds that is given back to developers.
ANDROID_DEVELOPER_REVENUE_SHARE = Decimal('0.7')
IOS_DEVELOPER_REVENUE_SHARE = Decimal('0.7')

# Timezones compatible with Apple's day boundary definition for each territory.
APPLE_REPORT_TERRITORY_TIMEZONES = ['America/Los_Angeles', 'Europe/Berlin', 'Japan',
    'Australia/Sydney']
