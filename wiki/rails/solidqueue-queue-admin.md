---
title: "SolidQueue Queue Admin"
aliases: [solid_queue clear queue, solid queue drain, solid_queue delete jobs, solid_queue purge]
tags: [rails, solid-queue, background-jobs, ops]
created: 2026-04-23
updated: 2026-04-23
source_skill: study-walkthrough
probe_sections: [Clearing a queue, The batching gotcha, Nuclear path for large queues, discard vs delete_all]
last_probed: [Clearing a queue, The batching gotcha, Nuclear path for large queues, discard vs delete_all]
---

# SolidQueue Queue Admin

Reference for clearing and draining SolidQueue queues safely. SolidQueue stores jobs across `solid_queue_jobs` and execution tables (`ready_executions`, `scheduled_executions`, `failed_executions`) linked by FK. Admin choices depend on queue size and environment.

## Clearing a queue

Canonical per-queue clear:

```ruby
SolidQueue::Queue.find_by(name: "my_queue").clear
```

This routes through `Queue#clear`, which runs the proper job lifecycle (executions destroyed, jobs finalized). Safe for production — callbacks fire, instrumentation works.

## The batching gotcha

In older SolidQueue versions, `Queue#clear` only wipes the first batch. Root cause (solid_queue#181): `dependent: :destroy` on `ready_executions` / `scheduled_executions` cascades row-by-row, and the outer relation is re-queried mid-destroy — leaving residual rows.

Mitigation until upgraded:

```ruby
q = SolidQueue::Queue.find_by(name: "my_queue")
q.clear while q.size > 0
```

Upgrade if you can; otherwise loop until `size` (or `SolidQueue::Job.where(queue_name: ...).count`) hits zero.

## Nuclear path for large queues

For staging or one-shot cleanup of a large backlog (e.g. 143k rows), bypass callbacks:

```ruby
SolidQueue::ReadyExecution.where(queue_name: "X").in_batches.delete_all
SolidQueue::ScheduledExecution.where(queue_name: "X").in_batches.delete_all
SolidQueue::Job.where(queue_name: "X").in_batches.delete_all
```

Order matters — executions reference jobs via FK; delete executions first. `delete_all` issues raw DELETE, skipping AR callbacks. Orders of magnitude faster than iterating with `each(&:discard)`, but you lose lifecycle hooks and any custom instrumentation. Use in staging freely; in production prefer the `Queue#clear` loop unless you have accepted the tradeoff.

## discard vs delete_all

- `discard` is an instance method on execution records (notably `SolidQueue::FailedExecution`) that performs a proper "abandon this job" lifecycle — marks the job finished, cleans up associations.
- `discard` is not defined on ActiveRecord relations. `Relation#discard_all` does not exist on SolidQueue models — calling `.discard` on a relation raises `NoMethodError`.
- For bulk failed-execution cleanup you either iterate (`each(&:discard)`, slow but correct) or `delete_all` (fast, skips the lifecycle — rarely what you want for failures you might want to retry).

Rule of thumb: individual discards for correctness, `delete_all` for throw-away bulk cleanup, `Queue#clear` for the normal admin path.

## Sources

- solid_queue GitHub issues #181 (batch clear bug), #124, #278.
