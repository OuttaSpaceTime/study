---
wiki: software-design/software-complexity
section: Guarantee ownership at the trust boundary
kind: write-code
questions:
- Who owns the guarantee that quantity is positive after the deletion, and where is it enforced?
- Why did the deleted check add no protection even though it was syntactically identical to the boundary check?
env: ruby
created: 2026-07-03
---

## Brief

parse_quantity is the boundary where raw external input becomes a trusted positive integer. The re-check inside reserve_stock guards a case that cannot occur past that boundary. Delete the dead guard.

## Stub

```ruby
def parse_quantity(raw)
  quantity = Integer(raw)
  raise ArgumentError, "quantity must be positive" unless quantity.positive?
  quantity
end

def reserve_stock(quantity)
  # TODO: parse_quantity already guarantees this at the boundary,
  # delete the dead guard below
  raise ArgumentError, "quantity must be positive" unless quantity.positive?
  puts "reserved #{quantity}"
end

reserve_stock(parse_quantity("3"))

begin
  reserve_stock(parse_quantity("-1"))
rescue ArgumentError => error
  puts "boundary rejected: #{error.message}"
end
```

## Solution

```ruby
def parse_quantity(raw)
  quantity = Integer(raw)
  raise ArgumentError, "quantity must be positive" unless quantity.positive?
  quantity
end

def reserve_stock(quantity)
  puts "reserved #{quantity}"
end

reserve_stock(parse_quantity("3"))

begin
  reserve_stock(parse_quantity("-1"))
rescue ArgumentError => error
  puts "boundary rejected: #{error.message}"
end
```

## Expected Output

```
reserved 3
boundary rejected: quantity must be positive
```
