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


@shared_task(acks_late=True)
def trigger_renewals():
    count = Subscription.objects.trigger_renewals()
    log.info("Trigger [%s] updated [%d] records", "renewals", count)
    return count


@shared_task(acks_late=True)
def trigger_expiring():
    count = Subscription.objects.trigger_expiring()
    log.info("Trigger [%s] updated [%d] records", "expiring", count)
    return count


@shared_task(acks_late=True)
def trigger_suspended():
    count = Subscription.objects.trigger_suspended()
    log.info("Trigger [%s] updated [%d] records", "renewals", count)
    return count


@shared_task(acks_late=True)
def trigger_suspended_timeout(hours=48, days=None):
    if days is not None:
        hours = days * 24

    count = Subscription.objects.trigger_suspended_timeout(timeout_hours=hours)
    log.info("Trigger [%s] updated [%d] records", "suspended", count)
    return count


@shared_task(acks_late=True)
def trigger_stuck(hours=2):
    count = Subscription.objects.trigger_stuck(timeout_hours=hours)
    log.info("Trigger [%s] updated [%d] records", "stuck", count)
    return count
