# Changelog

## v0.4.0 (2019-05-07)

- Added a new trigger for renewing subscriptions in SUSPENDED state, which helps for retries
- Changed `timeout_days` to `timeout_hours` in `suspended_timeout`. `timeout_hours` is still around
  for backward compatibility


## v0.3.0 (2019-05-01)

- Generated missing migration file
- Added a migrate.py helper for generating migrations
- Updated version dependencies to (hopefully) make this installable under py2.7

## v0.2.0 (2019-04-13)

- Initial working release
- Subscription models, tasks, and signals defined
