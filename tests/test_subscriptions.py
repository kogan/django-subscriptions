# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from django_fsm_log.models import StateLog
from subscriptions import signals
from subscriptions.models import Subscription
from subscriptions.states import SubscriptionState as State


@contextmanager
def signal_handler(signal):
    handler = mock.Mock()
    signal.connect(handler)
    yield handler
    signal.disconnect(handler)


class SubscriptionTestCase(TestCase):

    nowish = timezone.now()
    yearish = nowish + timedelta(days=365)
    days_ago = nowish - timedelta(days=4)
    hours_ago = nowish - timedelta(hours=6)

    sigs = [
        signals.subscription_due,
        signals.subscription_ended,
        signals.subscription_renewed,
        signals.subscription_error,
        signals.renewal_failed,
        signals.autorenew_canceled,
        signals.autorenew_enabled,
    ]

    def setUp(self):
        # Remove all external receivers for our own testing
        self.receivers = []
        for sig in self.sigs:
            self.receivers.append(sig.receivers)
            sig.receivers = []

    def tearDown(self):
        # Restore external receivers
        for (sig, receivers) in zip(self.sigs, self.receivers):
            sig.receivers = receivers

    def test_subscription_defaults(self):
        sub = Subscription(end=self.yearish)
        self.assertEqual(sub.state, State.ACTIVE)

    def test_state_not_manually_updated(self):
        sub = Subscription(end=self.yearish)
        with self.assertRaises(AttributeError):
            sub.state = State.EXPIRING

    def test_initial_state_can_be_anything(self):
        sub = Subscription(state=State.ENDED, end=self.yearish)
        self.assertEqual(sub.state, State.ENDED)

    def test_state_transition_roundtrip(self):
        sub = Subscription.objects.create(end=self.yearish)
        sub.cancel_autorenew()
        sub = Subscription.objects.get(pk=sub.pk)
        self.assertTrue(sub.state == State.EXPIRING)

    @mock.patch("subscriptions.models.Subscription.post_renew")
    def test_post_transition_hook(self, mock_post_renew):
        sub = Subscription.objects.create(end=self.yearish)
        sub.renew()
        mock_post_renew.assert_called_once()

    def test_signal_subscription_due(self):
        with signal_handler(signals.subscription_due) as handler:
            sub = Subscription(state=State.ACTIVE, end=self.yearish)
            sub.renew()
            handler.assert_called_once_with(sender=sub, signal=signals.subscription_due)
        self.assertEqual(sub.state, State.RENEWING)

    def test_signal_autorenew_enabled(self):
        with signal_handler(signals.autorenew_enabled) as handler:
            sub = Subscription(state=State.EXPIRING, end=self.yearish)
            sub.enable_autorenew()
            handler.assert_called_once_with(sender=sub, signal=signals.autorenew_enabled)
        self.assertEqual(sub.state, State.ACTIVE)

    def test_signal_autorenew_canceled(self):
        with signal_handler(signals.autorenew_canceled) as handler:
            sub = Subscription(state=State.ACTIVE, end=self.yearish)
            sub.cancel_autorenew()
            handler.assert_called_once_with(sender=sub, signal=signals.autorenew_canceled)
        self.assertEqual(sub.state, State.EXPIRING)

    def test_signal_subscription_renewed(self):
        with signal_handler(signals.subscription_renewed) as handler:
            sub = Subscription(state=State.RENEWING, end=self.yearish)
            new_end = self.yearish + timedelta(days=365)
            sub.renewed(new_end, "NEWREF")
            handler.assert_called_once_with(sender=sub, signal=signals.subscription_renewed)
        self.assertEqual(sub.state, State.ACTIVE)
        self.assertEqual(sub.end, new_end)
        self.assertEqual(sub.reference, "NEWREF")

    def test_signal_subscription_renewed_from_active(self):
        with signal_handler(signals.subscription_renewed) as handler:
            sub = Subscription(state=State.ACTIVE, end=self.yearish)
            new_end = self.yearish + timedelta(days=365)
            sub.renewed(new_end, "NEWREF", description="AUTOSUB")
            handler.assert_called_once_with(sender=sub, signal=signals.subscription_renewed)
        self.assertEqual(sub.state, State.ACTIVE)
        self.assertEqual(sub.end, new_end)
        self.assertEqual(sub.reference, "NEWREF")
        log = StateLog.objects.for_(sub).get()
        self.assertEqual(log.description, "AUTOSUB")
        self.assertEqual(log.transition, "renewed")

    def test_signal_renewal_failed(self):
        with signal_handler(signals.renewal_failed) as handler:
            sub = Subscription(state=State.RENEWING, end=self.yearish)
            sub.renewal_failed(description="DECLINED")
            handler.assert_called_once_with(sender=sub, signal=signals.renewal_failed)
        self.assertEqual(sub.state, State.SUSPENDED)
        log = StateLog.objects.for_(sub).get()
        self.assertEqual(log.description, "DECLINED")
        self.assertEqual(log.transition, "renewal_failed")

    def test_signal_subscription_ended(self):
        with signal_handler(signals.subscription_ended) as handler:
            sub = Subscription(state=State.SUSPENDED, end=self.yearish)
            sub.end_subscription(description="LetItGo")
            handler.assert_called_once_with(sender=sub, signal=signals.subscription_ended)
        self.assertEqual(sub.state, State.ENDED)
        log = StateLog.objects.for_(sub).get()
        self.assertEqual(log.description, "LetItGo")
        self.assertEqual(log.transition, "end_subscription")

    def test_signal_subscription_error(self):
        with signal_handler(signals.subscription_error) as handler:
            sub = Subscription(state=State.RENEWING, end=self.yearish)
            sub.state_unknown(description="WAT")
            handler.assert_called_once_with(sender=sub, signal=signals.subscription_error)
        self.assertEqual(sub.state, State.ERROR)
        log = StateLog.objects.for_(sub).get()
        self.assertEqual(log.description, "WAT")
        self.assertEqual(log.transition, "state_unknown")

    @mock.patch("subscriptions.models.signals.subscription_due.send_robust")
    def test_trigger_renewals(self, mock_signal):
        due = Subscription.objects.create(state=State.ACTIVE, end=self.hours_ago)
        not_due = Subscription.objects.create(state=State.ACTIVE, end=self.yearish)
        no_auto_renew = Subscription.objects.create(state=State.EXPIRING, end=self.hours_ago)
        self.assertEqual(Subscription.objects.renewals_due().count(), 1)
        self.assertEqual(Subscription.objects.trigger_renewals(), 1)
        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        no_auto_renew_fresh = Subscription.objects.get(pk=no_auto_renew.pk)

        self.assertEqual(due_fresh.state, State.RENEWING)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(no_auto_renew.state, no_auto_renew_fresh.state)

        mock_signal.assert_called_once_with(due)

    def test_trigger_expiring(self):
        due = Subscription.objects.create(state=State.EXPIRING, end=self.hours_ago)
        not_due = Subscription.objects.create(state=State.EXPIRING, end=self.yearish)
        ended = Subscription.objects.create(state=State.ENDED, end=self.hours_ago)

        self.assertEqual(Subscription.objects.expiring().count(), 1)
        self.assertEqual(Subscription.objects.trigger_expiring(), 1)
        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        ended_fresh = Subscription.objects.get(pk=ended.pk)

        self.assertEqual(due_fresh.state, State.ENDED)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(ended.state, ended_fresh.state)

    @mock.patch("subscriptions.models.signals.subscription_due.send_robust")
    def test_trigger_suspended(self, mock_signal):
        due = Subscription.objects.create(state=State.SUSPENDED, end=self.hours_ago)
        not_due = Subscription.objects.create(state=State.SUSPENDED, end=self.yearish)
        no_auto_renew = Subscription.objects.create(state=State.EXPIRING, end=self.hours_ago)
        self.assertEqual(Subscription.objects.suspended().count(), 1)
        self.assertEqual(Subscription.objects.trigger_suspended(), 1)
        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        no_auto_renew_fresh = Subscription.objects.get(pk=no_auto_renew.pk)

        self.assertEqual(due_fresh.state, State.RENEWING)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(no_auto_renew.state, no_auto_renew_fresh.state)

        mock_signal.assert_called_once_with(due)

    def test_trigger_suspended_timeout(self):
        due = Subscription.objects.create(state=State.SUSPENDED, end=self.days_ago)
        not_due = Subscription.objects.create(state=State.SUSPENDED, end=self.hours_ago)
        renewing = Subscription.objects.create(state=State.RENEWING, end=self.days_ago)

        self.assertEqual(Subscription.objects.suspended_timeout(timeout_hours=72).count(), 1)
        self.assertEqual(Subscription.objects.trigger_suspended_timeout(), 1)
        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        renewing_fresh = Subscription.objects.get(pk=renewing.pk)

        self.assertEqual(due_fresh.state, State.ENDED)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(renewing.state, renewing_fresh.state)

    def test_trigger_stuck(self):
        due = Subscription.objects.create(state=State.RENEWING, end=self.days_ago)
        not_due = Subscription.objects.create(state=State.RENEWING, end=self.days_ago)
        ended = Subscription.objects.create(state=State.ENDED, end=self.days_ago)

        # last_updated rather than end is used for this query
        Subscription.objects.all().update(last_updated=self.hours_ago)
        Subscription.objects.filter(pk=not_due.pk).update(last_updated=timezone.now())

        self.assertEqual(Subscription.objects.stuck(timeout_hours=2).count(), 1)
        self.assertEqual(Subscription.objects.trigger_stuck(), 1)
        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        ended_fresh = Subscription.objects.get(pk=ended.pk)

        self.assertEqual(due_fresh.state, State.ERROR)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(ended.state, ended_fresh.state)

    def test_trigger_stuck_retry(self):
        due = Subscription.objects.create(state=State.RENEWING, end=self.days_ago)
        not_due = Subscription.objects.create(state=State.RENEWING, end=self.days_ago)
        ended = Subscription.objects.create(state=State.ENDED, end=self.days_ago)

        # last_updated rather than end is used for this query
        Subscription.objects.all().update(last_updated=self.hours_ago)
        Subscription.objects.filter(pk=not_due.pk).update(last_updated=timezone.now())

        with self.settings(SUBSCRIPTIONS_STUCK_RETRY=True):
            self.assertEqual(Subscription.objects.stuck(timeout_hours=2).count(), 1)
            self.assertEqual(Subscription.objects.trigger_stuck(), 1)

        due_fresh = Subscription.objects.get(pk=due.pk)
        not_due_fresh = Subscription.objects.get(pk=not_due.pk)
        ended_fresh = Subscription.objects.get(pk=ended.pk)

        self.assertEqual(due_fresh.state, State.SUSPENDED)
        self.assertNotEqual(due.state, due_fresh.state)
        self.assertEqual(not_due.state, not_due_fresh.state)
        self.assertEqual(ended.state, ended_fresh.state)

    def test_renewed_from_suspended(self):
        """
        A subscription in SUSPENDED can be RENEWED if new information arrives after
        the fact.
        """
        sub = Subscription.objects.create(state=State.SUSPENDED, end=self.days_ago)
        sub.renewed(timezone.now() + timedelta(days=7), "MYREF", "Renewed from SUSPENDED")
        self.assertEqual(sub.state, State.ACTIVE)
