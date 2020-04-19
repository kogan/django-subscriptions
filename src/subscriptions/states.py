from enum import IntEnum


class SubscriptionState(IntEnum):
    ACTIVE = 1
    EXPIRING = 2
    RENEWING = 3
    SUSPENDED = 4
    ENDED = 5
    ERROR = -1

    @classmethod
    def choices(cls):
        return sorted((s.value, "{}".format(SubscriptionState(s.value).name)) for s in cls)
