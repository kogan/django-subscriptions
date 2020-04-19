from functools import wraps

from django.dispatch import receiver
from django_fsm.signals import post_transition as post_transition_signal

__all__ = ["post_transition"]

"""
Implements post_transition decorator hooks for Django-FSM.

Usage:

    @transition(field=state, source="abc", target="def)
    def my_state_change(self):
        # self.state hasn't updated yet!
        assert self.state == "abc"

    @post_transition(my_state_change):
    def post_my_state_change(self):
        # self.state has updated, but has not been saved
        assert self.state == "def"
"""


_POST_TRANSITION_IDENTIFIER = "_fsm_post_transition"


def post_transition(transition_method):
    """
    Links a post transition hook to the transition, so that our receiver can
    identify the hook.
    """

    def inner_function(func):
        @wraps(func)
        def _post_transition_hook(instance):
            return func(instance)

        setattr(transition_method, _POST_TRANSITION_IDENTIFIER, func.__name__)
        return _post_transition_hook

    return inner_function


@receiver(post_transition_signal)
def post_transition_handler(sender, instance, name, source, target, **kwargs):
    """
    Identifies the hook linked to the transition method, and calls it with no
    arguments.

    The transition has **not** been saved at this point.
    """
    transition_method = getattr(instance, name)
    try:
        post_hook_name = getattr(transition_method, _POST_TRANSITION_IDENTIFIER)
    except AttributeError:
        return
    post_func = getattr(instance, post_hook_name)
    post_func()
