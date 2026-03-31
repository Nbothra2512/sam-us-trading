# Cloudflare Configuration — SAM - Smart Analyst for Markets

## Domain Setup
- **Domain**: smarttouch.solutions
- **Cloudflare Plan**: Pro
- **SSL Mode**: Full (strict)
- **Proxy Status**: Proxied (orange cloud)

### URLs
| Type | URL |
|---|---|
| Frontend | https://sam.smarttouch.solutions |
| Backend API | https://api-sam.smarttouch.solutions |

## Security Features

### WAF (Web Application Firewall)
- Cloudflare Managed Ruleset: Active
- OWASP Core Ruleset: Active (SQLi, XSS, RCE, LFI protection)

### Bot Protection
- JS Challenge Detection: Enabled
- Definitely Automated Traffic: Blocked
- AI Bot Scraping: Blocked
- Crawler Protection: Enabled

### Firewall Rules
1. Challenge suspicious visitors on login endpoints (threat score > 10)
2. Block known attack tools (sqlmap, nikto, nmap, masscan, dirbuster, havij)
3. Challenge high-threat visitors globally (threat score > 30)

### Rate Limiting
| Endpoint | Limit | Block Duration |
|---|---|---|
| /api/auth/login, /api/login, /token | 10 req/min per IP | 5 minutes |
| Global (all endpoints) | 100 req/min per IP | 1 minute |

### Security Headers (added by Cloudflare)
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()
- X-XSS-Protection: 1; mode=block

## Performance Features

### Speed Optimizations
| Feature | Status |
|---|---|
| Brotli Compression | Enabled |
| Early Hints (103) | Enabled |
| Rocket Loader | Enabled |
| Polish (Image Compression) | Lossless |
| Mirage (Mobile Image Opt) | Enabled |
| HTTP/2 Prioritization | Enabled |
| Always Online | Enabled |
| Browser Cache TTL | 4 hours |

### Caching Rules
| Pattern | Action |
|---|---|
| */assets/* | Cache Everything, Edge TTL 1 month, Browser TTL 1 week |
| */static/* | Cache Everything, Edge TTL 1 month |
| api-sam.smarttouch.solutions/* | Bypass Cache |

## DDoS Protection
- Layer 7 DDoS mitigation: Automatic (always on)
- Advanced DDoS: Enabled

## Edge Location
- Primary: BOM (Mumbai, India)

## DNS Configuration
- Nameservers: eoin.ns.cloudflare.com, rita.ns.cloudflare.com
- CNAME records: Proxied through Cloudflare
- TXT records: Railway verification

## Notes
- All traffic is proxied through Cloudflare edge servers
- Direct Railway URLs (.up.railway.app) still work but bypass Cloudflare protection
- Custom domain should always be used for production traffic
- WebSocket connections for live market streaming are supported through Cloudflare Pro

---
*Configured: 2026-03-31 | Cloudflare Pro Plan | smarttouch.solutions*
