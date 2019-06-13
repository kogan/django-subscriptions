# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.test import TestCase, override_settings
from django.utils import timezone
from subscriptions.models import as_date


class UtilTests(TestCase):
    @override_settings(USE_TZ=False, TIME_ZONE="Australia/Melbourne")
    def test_as_date_naive(self):
        dt = datetime(2019, 6, 13, 23, 30)
        self.assertEqual(as_date(dt), datetime(2019, 6, 13).date())

    @override_settings(USE_TZ=True, TIME_ZONE="Australia/Melbourne")
    def test_as_date_aware(self):
        dt = datetime(2019, 6, 13, 23, 30)
        dt = timezone.make_aware(dt, timezone=timezone.utc)
        # localise will push from 23:30 -> 9:30 the next day
        self.assertEqual(as_date(dt), datetime(2019, 6, 14).date())
