# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Subscription

"""
Celery tasks that can be directly added to a projects' Celery Beat configuration,
with whatever timing makes sense for that application.
"""


log = get_task_logger(__name__)


def log_update(trigger: str, count: int):
    log.info("subscriptions.trigger | trigger=%s | count=%s |", trigger, count)


@shared_task(acks_late=True)
def trigger_renewals():
    count = Subscription.objects.trigger_renewals()
    log_update("renewals", count)
    return count


@shared_task(acks_late=True)
def trigger_expiring():
    count = Subscription.objects.trigger_expiring()
    log_update("expiring", count)
    return count


@shared_task(acks_late=True)
def trigger_suspended():
    count = Subscription.objects.trigger_suspended()
    log_update("suspended", count)
    return count


@shared_task(acks_late=True)
def trigger_suspended_timeout(hours=48, days=None):
    if days is not None:
        hours = days * 24

    count = Subscription.objects.trigger_suspended_timeout(timeout_hours=hours)
    log_update("timeout", count)
    return count


@shared_task(acks_late=True)
def trigger_stuck(hours=2):
    count = Subscription.objects.trigger_stuck(timeout_hours=hours)
    log_update("stuck", count)
    return count
