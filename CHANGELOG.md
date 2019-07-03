# Changelog

## v1.0.0 (2019-07-03)

- **Breaking Change** `suspended_timeout` now triggers for subscriptions in SUSPENDED state that are
  `timeout_hours` past the `subscription.end` time. It used to trigger if `subscription.last_updated`
  hadn't changed for `timeout_hours`, but if `trigger_suspended` was running daily, the subscription
  was constantly being updated, and `trigger_suspended_timeout` would never find a record to `end()`.


## v0.5.1 (2019-06-13)

- Only localise datetimes to dates when they are aware

## v0.5.0 (2019-06-04)

- Display start/end dates in the local timezone
- Changed the display of Subscription.__str__
- Renewed can now be called from Active state, for an early renewal.

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
