import os
import sys

# Make sure the app is (at least temporarily) on the import path.
APP_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(APP_DIR, "src/"))

SETTINGS_DICT = {
    "INSTALLED_APPS": [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "subscriptions.apps.SubscriptionsConfig",
    ],
    "DATABASES": {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
}


def migrate(name):
    from django.conf import settings

    settings.configure(**SETTINGS_DICT)
    import django

    django.setup()

    from django.core import management

    management.call_command("makemigrations", "subscriptions", name=name)


if __name__ == "__main__":
    args = sys.argv[1:]
    assert len(args) == 1, "Must supply the name of the migration"
    migrate(args[0])
