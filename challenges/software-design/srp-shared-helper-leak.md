---
wiki: software-design/splitting-responsibilities
section: What SRP actually measures
kind: predict-output
env: python312
questions:
- Which actor requested the change to rounded_hours, and which actor's output silently changed with it?
- Why does this class violate SRP even though every method does exactly one thing?
created: 2026-07-03
---

## Brief

Finance asked for payroll hours to round up to the next half hour, so a developer edited the shared helper. HR never asked for anything. Predict both printed lines.

## Stub

```python
import math

def rounded_hours(hours):
    return math.ceil(hours * 2) / 2

class Employee:
    def __init__(self, hours):
        self.hours = hours

    def calculate_pay(self, rate):
        return rounded_hours(self.hours) * rate

    def report_hours(self):
        return rounded_hours(self.hours)

e = Employee(39.1)
print("payroll:", e.calculate_pay(10))
print("HR timesheet:", e.report_hours())
```

## Solution

```python
import math

def rounded_hours(hours):
    return math.ceil(hours * 2) / 2

class Employee:
    def __init__(self, hours):
        self.hours = hours

    def calculate_pay(self, rate):
        return rounded_hours(self.hours) * rate

    def report_hours(self):
        return rounded_hours(self.hours)

e = Employee(39.1)
print("payroll:", e.calculate_pay(10))
print("HR timesheet:", e.report_hours())
```

## Expected Output

```
payroll: 395.0
HR timesheet: 39.5
```
