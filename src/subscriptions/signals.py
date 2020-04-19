from django.dispatch import Signal

subscription_due = Signal()
subscription_ended = Signal()
subscription_renewed = Signal()
subscription_error = Signal()
renewal_failed = Signal()
autorenew_canceled = Signal()
autorenew_enabled = Signal()
