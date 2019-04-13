# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import django_fsm
import subscriptions.states


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "state",
                    django_fsm.FSMIntegerField(
                        choices=[
                            (-1, "ERROR"),
                            (1, "ACTIVE"),
                            (2, "EXPIRING"),
                            (3, "RENEWING"),
                            (4, "SUSPENDED"),
                            (5, "ENDED"),
                        ],
                        default=subscriptions.states.SubscriptionState(1),
                        help_text="The current status of the subscription. May not be modified directly.",
                        protected=True,
                    ),
                ),
                (
                    "start",
                    models.DateTimeField(
                        default=django.utils.timezone.now, help_text="When the subscription begins"
                    ),
                ),
                ("end", models.DateTimeField(help_text="When the subscription ends")),
                (
                    "reference",
                    models.TextField(
                        help_text="Free text field for user references", max_length=100
                    ),
                ),
                (
                    "last_updated",
                    models.DateTimeField(
                        auto_now=True, help_text="Keeps track of when a record was last updated"
                    ),
                ),
                ("reason", models.TextField(help_text="Reason for state change, if applicable.")),
            ],
            options={
                "permissions": (("can_update_state", "Can update subscription state"),),
                "get_latest_by": "start",
            },
        ),
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(fields=["state"], name="subscription_state_idx"),
        ),
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(fields=["end"], name="subscription_end_idx"),
        ),
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(fields=["last_updated"], name="subscription_last_updated_idx"),
        ),
    ]
