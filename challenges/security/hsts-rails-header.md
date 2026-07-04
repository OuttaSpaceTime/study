---
wiki: security/hsts
section: What the HSTS header looks like on a real site
kind: predict-output
env: rails
questions:
- What two behaviors does config.force_ssl = true enable?
- Why does the emitted max-age differ from 31536000 even though expires is 1.year?
created: 2026-07-04
---

## Brief

ActionDispatch::SSL is the middleware behind config.force_ssl. Predict the exact header it adds to an HTTPS response for these ssl_options.

## Stub

```ruby
app = ->(env) { [200, {}, ["ok"]] }
ssl = ActionDispatch::SSL.new(app, hsts: { expires: 1.year, subdomains: true, preload: true })
_, headers, = ssl.call(Rack::MockRequest.env_for("https://example.com/"))
puts headers["strict-transport-security"]
```

## Solution

```ruby
app = ->(env) { [200, {}, ["ok"]] }
ssl = ActionDispatch::SSL.new(app, hsts: { expires: 1.year, subdomains: true, preload: true })
_, headers, = ssl.call(Rack::MockRequest.env_for("https://example.com/"))
puts headers["strict-transport-security"]
```

## Expected Output

```
max-age=31556952; includeSubDomains; preload
```
