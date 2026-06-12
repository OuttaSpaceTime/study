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
depth: 1
probe_sections:
- URL anatomy at a glance
- Scheme vs protocol
- Host - subdomain, SLD, TLD
- 'Port: default ports and when the URL includes one'
- Path and query
- DNS resolution
- DNS caching, TTL, and safe migrations
- Host header and virtual hosts
last_probed:
- Host - subdomain, SLD, TLD
- DNS resolution
- DNS caching, TTL, and safe migrations
- Host header and virtual hosts
- URL anatomy at a glance
- Scheme vs protocol
- 'Port: default ports and when the URL includes one'
- Path and query
review_interval: 2
next_review: '2026-06-12'
---

# URL Anatomy

## TL;DR

A URL is a chain of narrowing handoffs. Each layer answers one question and passes the rest down. Scheme → host → port → path → query. DNS turns the host name into an IP. The server then uses the `Host` header to pick the right site when many domains share one IP. Everything else (TLDs, subdomains, TTL caching, virtual hosts) follows from these handoffs.

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

## DNS resolution

The network stack only deals in IPs. DNS translates names to IPs through a delegated hierarchy. For `www.example.com`:

1. Your machine asks its **resolver** (system resolver, ISP, or `1.1.1.1` / `8.8.8.8`).
2. Resolver asks a **root server**: "who runs `.com`?" → Verisign's nameservers.
3. Resolver asks the `.com` registry: "who runs `example.com`?" → the domain's authoritative nameservers.
4. Resolver asks those nameservers: "A record for `www.example.com`?" → `1.2.3.4`.
5. Resolver caches the answer (per record TTL) and returns it.
6. Browser opens TCP to `1.2.3.4:443`.

Each level only knows the level immediately below. The `.com` registry doesn't know what `www.example.com` resolves to. Only that the domain's nameservers do. Ownership and knowledge are scoped to your delegation.

## DNS caching, TTL, and safe migrations

Every cached DNS answer carries a **TTL** (time-to-live, in seconds) set on the record itself. Caches keep the answer that long, then refetch.

Caches live at multiple layers:

1. Browser
2. OS resolver (systemd-resolved, mDNSResponder)
3. Public / ISP resolver (`1.1.1.1`, etc.)
4. Intermediate forwarders

DNS changes "propagate over hours" only because old caches expire one by one. Nothing pushes invalidation.

**Naive failure mode:** flip the A record AND immediately decommission the old IP. Users with cached old answers fail until their TTL expires.

**Safe migration playbook:**

1. **Lower TTL ahead of time.** Days before, drop TTL from 3600 → 60. After the old TTL window has fully passed, every cache holds the short-TTL record.
2. **Flip the A record** to the new IP. Recovery is now within the new TTL (~1 minute).
3. **Keep the old IP serving** during the cutover. Duplicate the site or 301-redirect to the new host. Decommission only after the longest plausible cache lifetime has passed.
4. **Raise TTL back** afterward.

Production environments avoid the dance entirely by **not changing the IP**:

- Put a **load balancer / reverse proxy** at a stable IP; move backends behind it. DNS never moves.
- **CDN / Anycast**: same IP advertised from many locations; routing changes happen at the network layer, not in DNS.

Rule of thumb. **Never combine a DNS change with immediate teardown of the old endpoint.**

## Host header and virtual hosts

After DNS, the network only knows an IP. If many domains point to one IP (`chat.example.com` and `intranet.example.com` both at `1.2.3.4`), the server has to be told *which* site the user wanted.

The browser puts that information in the HTTP **request**:

```
GET /messages HTTP/1.1
Host: chat.example.com
User-Agent: Mozilla/5.0 ...
Accept: text/html
```

The `Host` header is the entire mechanism for **name-based virtual hosts**. The server reads it and dispatches to the right app. This is what nginx's `server_name`, Apache's `<VirtualHost>`, and Rails' `config.hosts` key on.

For HTTPS, **SNI** (Server Name Indication) carries the same hostname earlier. In the TLS handshake. So the server knows which certificate to present. Same job, different layer.

Direction matters. The **browser sends the request** with `Host`; the **server reads it and sends a response back**. The header is in the *request*, never the response.

## Related Concepts

- [[security/hsts]]: uses the host (and its subdomains, with `includeSubDomains`) as the keying for forced-HTTPS state.
- [[security/same-origin-policy]]: origin = `(scheme, host, port)` triple; this page explains each component.
