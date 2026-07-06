---
title: URL Anatomy
aliases:
- URL parts
- URL structure
- scheme host port path
- domain vs host
- subdomain SLD TLD
tags:
- networking
- web
- http
- dns
created: '2026-05-04'
updated: '2026-05-04'
source_skill: study-walkthrough
flashcard_ids:
- cmoqrprzu0000ld0mfbwqly5v
probe_sections:
- URL anatomy at a glance
- Scheme vs protocol
- Host - subdomain, SLD, TLD
- 'Port: default ports and when the URL includes one'
- Path and query
last_probed:
- Host - subdomain, SLD, TLD
- Scheme vs protocol
- 'Port: default ports and when the URL includes one'
- Path and query
- URL anatomy at a glance
review_interval: 10
next_review: '2026-07-11'
---

# URL Anatomy

## TL;DR

A URL is a chain of narrowing handoffs. Each layer answers one question and passes the rest down. Scheme → host → port → path → query. Turning the host name into an IP is DNS's job. Resolution, TTL caching, and the `Host` header that picks a site when many share one IP all live in [[networking/dns]]. Everything else (TLDs, subdomains) follows from these handoffs.

## URL anatomy at a glance

```
  https://www.example.com:443/pixel?utm=foo
  └─┬─┘   └──────┬──────┘ └┬┘ └─┬─┘ └──┬──┘
    │            │          │     │      │
  scheme       host        port  path   query
                └──────────┬──────┘
                       authority
```

Each piece narrows the target:

| Piece          | Question it answers                                              |
|----------------|------------------------------------------------------------------|
| Scheme         | What kind of resource. And how do I talk to it?                 |
| Host           | Which machine, named in human-readable form?                     |
| Port           | Which program on that machine?                                   |
| Path           | Which resource within that program?                              |
| Query          | What parameters for the response?                                |

The **authority** (`host[:port]`, optionally `userinfo@host:port`) is the chunk between `://` and the next `/`.

## Scheme vs protocol

Same word in different jobs:

- **Scheme** is a URL-syntax label: the literal token before `://`. It tells the URL parser how to interpret what follows. Examples: `https`, `http`, `mailto`, `file`, `ssh`, `git+ssh`.
- **Protocol** is the wire-level rule for exchanging bytes. Examples: HTTP, TLS, TCP.

For most schemes the two coincide (`https://` selects HTTP-over-TLS as the wire protocol). For some they don't:

- `mailto:foo@bar.com` is a scheme with no wire protocol: the OS hands it to a mail client.
- `tcp` is a protocol but never appears as a URL scheme.

Keep the layers straight. The parser cares about schemes; the network stack cares about protocols.

## Host - subdomain, SLD, TLD

Read host names **right-to-left**. That mirrors how DNS delegates ownership.

```
  www       .  example       .  com
  └─ subdomain  └─ second-level    └─ top-level
                    domain (SLD)        domain (TLD)
```

- **TLD** (`.com`, `.org`, `.de`): run by a registry (Verisign for `.com`, DENIC for `.de`). The TLD only knows which authoritative nameservers handle each SLD beneath it.
- **SLD** (`example`): the registered domain. This is what you pay the registry for. You control everything to the left.
- **Subdomain** (`www`, `chat`, `staging`, `api`): labels the domain owner adds under their SLD. No coordination with anyone else needed; just add a DNS record.

`www` is purely a 1990s convention for "the public Web server on this domain." It has no technical meaning today. `example.com` and `www.example.com` are two independent DNS names that may or may not point to the same place.

A **host** in URL syntax can be:

- a domain name (`www.example.com`): resolved via DNS
- an IP literal (`192.168.1.10`, `[2001:db8::1]`: IPv6 needs the brackets)
- a special name (`localhost`, resolved locally to `127.0.0.1`)

## Port: default ports and when the URL includes one

A port is a 16-bit number (0–65535) the OS uses as a per-program mailbox.

```
  IP address  →  which machine
  Port        →  which program on that machine
```

Many programs share one IP. A web server, Postgres, SSH, Redis. Each tells the OS "deliver everything for port N to me." Postgres lives on 5432, SSH on 22, web servers on 80/443.

**Every URL has a port. The question is whether it's written.** Each scheme has a default port:

| Scheme  | Default port |
|---------|--------------|
| `http`  | 80           |
| `https` | 443          |
| `ssh`   | 22           |
| `ftp`   | 21           |

When the URL omits the port, the browser uses the scheme default. The browser does **not** remember "I just used 3000". It has no idea your local server exists. The rule is purely scheme → default port.

Practical consequence. `http://localhost` connects to `:80`. If your dev server is on `:3000`, you get `ECONNREFUSED` because nothing's listening on `:80`. You must write `http://localhost:3000`.

## Path and query

After the authority comes:

- **Path** (`/pixel`): identifies the resource *within* the program at that port. The web server / app matches it against its routing table.
- **Query** (`?utm=foo`): key-value parameters for the response (`utm=foo&page=2`). Parsed into request params by the server.
- **Fragment** (`#section`): *never sent to the server*. Browser-only; controls in-page navigation. Useful to remember when debugging server-side analytics.

## Related Concepts

- [[networking/dns]]: how the host name resolves to an IP, TTL caching, safe IP migrations, and the `Host` header for virtual hosts.
- [[security/hsts]]: uses the host (and its subdomains, with `includeSubDomains`) as the keying for forced-HTTPS state.
- [[security/same-origin-policy]]: origin = `(scheme, host, port)` triple; this page explains each component.
