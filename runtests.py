"""
A standalone test runner script, configuring the minimum settings
required

Re-use at your own risk.

Script copied, blatantly, from https://github.com/ubernostrum/pwned-passwords-django/blob/master/runtests.py

"""

import os
import sys

# Make sure the app is (at least temporarily) on the import path.
APP_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(APP_DIR, "src/"))

SETTINGS_DICT = {
    "INSTALLED_APPS": [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django_fsm_log",
        "subscriptions.apps.SubscriptionsConfig",
    ],
    "DATABASES": {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    "TEST_RUNNER": "xmlrunner.extra.djangotestrunner.XMLTestRunner",
    "TEST_OUTPUT_VERBOSE": 2,
    "TEST_OUTPUT_DIR": "test-results",
    "TEST_OUTPUT_FILE_NAME": "test-output.xml",
}


def run_tests():
    # First configure settings, then call django.setup() to initialise
    from django.conf import settings

    settings.configure(**SETTINGS_DICT)
    import django

    django.setup()

    # Now create the test runner
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)

    # And then we run tests and return the results.
    test_runner = TestRunner(verbosity=2, interactive=True)
    failures = test_runner.run_tests(["tests"])
    sys.exit(failures)


if __name__ == "__main__":
    run_tests()
