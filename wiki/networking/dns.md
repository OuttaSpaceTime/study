---
title: DNS
aliases:
- DNS
- domain name system
- DNS resolution
- DNS caching and TTL
tags:
- networking
- dns
created: '2026-07-05'
updated: '2026-07-05'
source_skill: study-walkthrough
review_interval: 10
next_review: '2026-07-11'
flashcard_ids: []
---

# DNS

## DNS resolution

The network stack only deals in IPs. DNS translates names to IPs through a delegated hierarchy. For `www.example.com`:

1. Your machine asks its **resolver** (system resolver, ISP, or `1.1.1.1` / `8.8.8.8`).
2. Resolver asks a **root server**: "who runs `.com`?" → Verisign's nameservers.
3. Resolver asks the `.com` registry: "who runs `example.com`?" → the domain's authoritative nameservers.
4. Resolver asks those nameservers: "A record for `www.example.com`?" → `1.2.3.4`.
5. Resolver caches the answer (per record TTL) and returns it.
6. Browser opens TCP to `1.2.3.4:443`.

Each level only knows the level immediately below. The `.com` registry doesn't know what `www.example.com` resolves to. Only that the domain's nameservers do. Ownership and knowledge are scoped to your delegation.

## DNS caching and TTL

Every cached DNS answer carries a **TTL** (time-to-live, in seconds) set on the record itself. Caches keep the answer that long, then refetch.

Caches live at multiple layers:

1. Browser
2. OS resolver (systemd-resolved, mDNSResponder)
3. Public / ISP resolver (`1.1.1.1`, etc.)
4. Intermediate forwarders

DNS changes "propagate over hours" only because old caches expire one by one. Nothing pushes invalidation.

## Safe migration

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

- [[networking/url-anatomy]]: the host name resolved here is one component of the URL; that page covers scheme, port, path, and query.
- [[security/hsts]]: forced-HTTPS state is keyed on the host (and subdomains with `includeSubDomains`).
