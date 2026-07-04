---
wiki: rails/routing/route-organization
section: draw -- Split Routes into Files
kind: write-code
env: rails
questions:
- Where does draw :admin look for the route file in a real Rails app?
- Do routes loaded via draw behave any differently from routes written inline in routes.rb?
created: 2026-07-03
---

## Brief

An external route file exists at `config/routes/admin.rb`. Load it into the main route set so the admin routes work exactly as if they were written inline.

## Stub

```ruby
begin
  FileUtils.mkdir_p(Rails.root.join("config/routes"))
  File.write(Rails.root.join("config/routes/admin.rb"), <<~ROUTES)
    namespace :admin do
      resources :users, only: [:index]
    end
  ROUTES

  Rails.application.routes.draw do
    # TODO: load the external route file config/routes/admin.rb here
    resources :posts, only: [:index]
  end

  helpers = Rails.application.routes.url_helpers
  puts helpers.admin_users_path
  puts helpers.posts_path
ensure
  FileUtils.rm_f(Rails.root.join("config/routes/admin.rb"))
end
```

## Solution

```ruby
begin
  FileUtils.mkdir_p(Rails.root.join("config/routes"))
  File.write(Rails.root.join("config/routes/admin.rb"), <<~ROUTES)
    namespace :admin do
      resources :users, only: [:index]
    end
  ROUTES

  Rails.application.routes.draw do
    draw :admin
    resources :posts, only: [:index]
  end

  helpers = Rails.application.routes.url_helpers
  puts helpers.admin_users_path
  puts helpers.posts_path
ensure
  FileUtils.rm_f(Rails.root.join("config/routes/admin.rb"))
end
```

## Expected Output

```
/admin/users
/posts
```
