# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django_fsm import FSMIntegerField, transition
from django_fsm_log.decorators import fsm_log_by

from . import signals
from .fsm_hooks import post_transition
from .states import SubscriptionState as State


class SubscriptionManager(models.Manager):
    def add_subscription(self, start, end, reference):
        return self.create(state=State.ACTIVE, start=start, end=end, reference=reference)

    def trigger_renewals(self):
        """
        Finds all subscriptions that are due to be renewed, and begins the renewal process.
        """
        count = 0
        renewals = self.get_queryset().renewals_due().order_by("last_updated").iterator()
        for subscription in renewals:
            subscription.renew()
            count += 1
        return count

    def trigger_expiring(self):
        """
        Finds all subscriptions that have now finished, and begins the end subscription process.
        """
        count = 0
        ended = self.get_queryset().expiring().order_by("last_updated").iterator()
        for subscription in ended:
            subscription.end_subscription()
            count += 1
        return count

    def trigger_suspended_timeout(self, timeout_days=3):
        """
        Finds all subscriptions that have remained in Suspended status for `timeout_days`, and begins
        the end subscription process.
        """
        count = 0
        suspended = (
            self.get_queryset().suspended_timeout(timeout_days).order_by("last_updated").iterator()
        )
        for subscription in suspended:
            subscription.end_subscription()
            count += 1
        return count

    def trigger_stuck(self, timeout_hours=2):
        """
        Finds all subscriptions that begun the renewal process but did not complete, and moves them
        to the unknown state, requiring manual intervention.

        Subscriptions in this state usually crashed during the renewal process, so we don't know if
        the renewal succeeded or failed.
        """
        count = 0
        old_renewing = self.get_queryset().stuck(timeout_hours).order_by("last_updated").iterator()
        for subscription in old_renewing:
            subscription.state_unknown()
            count += 1
        return count


class SubscriptionQuerySet(models.QuerySet):
    def renewals_due(self):
        return self.filter(state=State.ACTIVE, end__lt=timezone.now())

    def expiring(self):
        return self.filter(state=State.EXPIRING, end__lt=timezone.now())

    def suspended_timeout(self, timeout_days=3):
        return self.filter(
            state=State.SUSPENDED, last_updated__lte=timezone.now() - timedelta(days=timeout_days)
        )

    def stuck(self, timeout_hours=2):
        return self.filter(
            state=State.RENEWING, last_updated__lte=timezone.now() - timedelta(hours=timeout_hours)
        )


@python_2_unicode_compatible
class Subscription(models.Model):
    state = FSMIntegerField(
        default=State.ACTIVE,
        choices=State.choices(),
        protected=True,
        help_text="The current status of the subscription. May not be modified directly.",
    )
    start = models.DateTimeField(default=timezone.now, help_text="When the subscription begins")
    end = models.DateTimeField(help_text="When the subscription ends")
    reference = models.TextField(max_length=100, help_text="Free text field for user references")
    last_updated = models.DateTimeField(
        auto_now=True, help_text="Keeps track of when a record was last updated"
    )
    reason = models.TextField(help_text="Reason for state change, if applicable.")

    objects = SubscriptionManager.from_queryset(SubscriptionQuerySet)()

    class Meta:
        indexes = [
            models.Index(fields=["state"], name="subscription_state_idx"),
            models.Index(fields=["end"], name="subscription_end_idx"),
            models.Index(fields=["last_updated"], name="subscription_last_updated_idx"),
        ]
        get_latest_by = "start"
        permissions = (("can_update_state", "Can update subscription state"),)

    def __str__(self):
        return "({}) {}: {:%Y-%m-%d} to {:%Y-%m-%d}".format(
            self.id or -1, self.get_state_display(), self.start, self.end
        )

    @transition(field=state, source=State.ACTIVE, target=State.EXPIRING)
    def cancel_autorenew(self):
        self.reason = ""

    @post_transition(cancel_autorenew)
    def post_cancel_autorenew(self):
        self.save()
        signals.autorenew_canceled.send_robust(self)

    @transition(field=state, source=State.EXPIRING, target=State.ACTIVE)
    def enable_autorenew(self):
        self.reason = ""

    @post_transition(enable_autorenew)
    def post_enable_autorenew(self):
        self.save()
        signals.autorenew_enabled.send_robust(self)

    @transition(field=state, source=[State.ACTIVE, State.SUSPENDED], target=State.RENEWING)
    def renew(self):
        self.reason = ""

    @post_transition(renew)
    def post_renew(self):
        self.save()
        signals.subscription_due.send_robust(self)

    @transition(field=state, source=[State.RENEWING, State.ERROR], target=State.ACTIVE)
    def renewed(self, new_end_date, new_reference):
        self.reason = ""
        self.end = new_end_date
        self.reference = new_reference

    @post_transition(renewed)
    def post_renewed(self):
        self.save()
        signals.subscription_renewed.send_robust(self)

    @transition(field=state, source=[State.RENEWING, State.ERROR], target=State.SUSPENDED)
    def renewal_failed(self, reason=""):
        self.reason = reason

    @post_transition(renewal_failed)
    def post_renewal_failed(self):
        self.save()
        signals.renewal_failed.send_robust(self)

    @fsm_log_by
    @transition(
        field=state,
        source=[State.ACTIVE, State.SUSPENDED, State.EXPIRING, State.ERROR],
        target=State.ENDED,
    )
    def end_subscription(self, reason="", by=None):
        self.reason = reason
        self.end = timezone.now()

    @post_transition(end_subscription)
    def post_end_subscription(self):
        self.save()
        signals.subscription_ended.send_robust(self)

    @transition(field=state, source=State.RENEWING, target=State.ERROR)
    def state_unknown(self, reason=""):
        """
        An error occurred after the payment was signalled, but before the
        subscription could be updated, so the correct state is unknown.

        Requires manual investigation to determine the correct state from
        here.

        If a record remains in RENEWING state for longer than some timeout, the
        record will be moved to this state.
        """
        self.reason = reason

    @post_transition(state_unknown)
    def post_state_unknown(self):
        self.save()
        signals.subscription_error.send_robust(self)
