from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

import factory
from factory import fuzzy
from subscriptions.states import SubscriptionState

from .models import Subscription


class SubscriptionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Subscription

    state = SubscriptionState.ACTIVE
    start = factory.LazyFunction(datetime.now)
    end = factory.LazyFunction(lambda: datetime.now() + timedelta(days=365))
    reference = fuzzy.FuzzyText(prefix="REF-", length=10)
