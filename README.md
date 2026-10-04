<p align="center">
  <img src="https://raw.githubusercontent.com/maverickaayush/maverickaayush/main/assets/profile.svg" alt="Terminal card: nmap scan of maverickaayush" width="100%" />
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/aayush-yadav-477028370"><img src="https://img.shields.io/badge/LinkedIn-aayush--yadav-00ff41?style=flat-square&logo=linkedin&logoColor=white&labelColor=0a0e14" alt="LinkedIn" /></a>
  <a href="https://tryhackme.com/p/maverickaayush"><img src="https://img.shields.io/badge/TryHackMe-top%206%25-00ff41?style=flat-square&logo=tryhackme&logoColor=white&labelColor=0a0e14" alt="TryHackMe top 6 percent" /></a>
  <a href="https://tryonus.tech"><img src="https://img.shields.io/badge/ONUS-tryonus.tech-00ff41?style=flat-square&labelColor=0a0e14" alt="ONUS" /></a>
  <a href="https://github.com/maverickaayush/Valsec"><img src="https://img.shields.io/badge/Valsec-source-00ff41?style=flat-square&labelColor=0a0e14" alt="Valsec" /></a>
</p>

## ~$ whoami

Second-year B.Tech CSE (Cybersecurity) student at Bennett University. I build security tooling that is deterministic where it has to be (scoring, compliance verdicts) and uses AI only where it helps (remediation text, schema suggestions), never in the decision path.

## ~$ cat projects/ONUS

**[ONUS](https://github.com/maverickaayush/ONUS)** is an open-source, AI-assisted VAPT platform, listed in OWASP's Vulnerability Scanning Tools directory. Point it at a domain you are authorized to test and it does the rest.

```
domain -> 8 parallel scan modules -> dedup + OWASP mapping -> passive verification
       -> deterministic CVSS v3.1 scoring -> optional local LLM remediation text
       -> PDF report + live dashboard
```

- 8 parallel modules (Nmap, ZAP, Nikto, Nuclei, testssl.sh, FFUF and more) feeding one normalized finding schema
- Three-tier confidence stage (confirmed / probable / unverified) via passive re-observation
- Deterministic CVSS v3.1 engine across 73 finding types, 690 pytest tests, byte-identical results on repeat scans
- Air-gapped by design, local AI through Ollama is optional, and AI text is isolated from scoring
- Self-host with `docker compose up`, or use the hosted instance at [tryonus.tech](https://tryonus.tech) (Oracle Cloud ARM64 behind a hardened Caddy proxy with TLS)

`FastAPI` `PostgreSQL` `Celery/Redis` `Next.js` `Docker` `Ollama`

## ~$ cat projects/Valsec

**[Valsec](https://github.com/maverickaayush/Valsec)** is a network security compliance auditor.

```
seed device -> CDP/LLDP discovery -> normalized config -> CIS / NIST 800-53 / DISA STIG / ISO 27001
            -> PASS / FAIL / N/A -> operator-approved remediation push -> post-change diff
```

- Normalizes Cisco IOS/IOS-XE, Juniper JunOS and Fortinet FortiOS configs into one schema
- Human-in-the-loop onboarding: a local Ollama model proposes schema mappings, kept strictly separate from PASS/FAIL/N/A scoring
- Authenticated seed-based discovery with resolve-then-pin validation
- Validated on real hardware (OpenWrt router, Cirotech appliance over SSH/Telnet) with a documented lab setup and recovery runbook

`FastAPI` `PostgreSQL` `Celery/Redis` `Next.js` `Docker` `Ollama`

## ~$ ls projects/

- **[stock-exchange-simulator](https://github.com/maverickaayush/stock-exchange-simulator)**: multi-symbol limit-order-book matching engine (LIMIT, MARKET, STOP_LIMIT) with strict price-time priority. Benchmarked at 300,000 orders in 0.55 to 0.84s, covered by 67 JUnit 5 tests. `Java 21` `Maven` `Swing`

## ~$ cat achievements.log

- Listed in OWASP's Vulnerability Scanning Tools directory (ONUS)
- Responsibly disclosed a vendor-validated production vulnerability on Kickbacks.ai (ShiftKeys Inc.), awarded a $100 researcher reward
- Publicly credited on Kickbacks.ai's Security Acknowledgements page (Jul 2026, Business Logic) for a separate revenue-integrity finding
- Top 6% globally on [TryHackMe](https://tryhackme.com/p/maverickaayush), 80 rooms completed

## ~$ cat experience.log

- **Deputy Minister of Digital Infrastructure**, SCSET Student Cabinet, Bennett University (Aug 2026 to present). Directing digital-infrastructure initiatives for the student body that oversees all 24 technical clubs and chapters
- **Cybersecurity Project Intern**, IIT Kanpur Computer Centre (Jun to Jul 2026). Designed and built ONUS under the Chief Computer Engineer, later open-sourced it
- **Founder & CEO**, Clinkl (Jul 2025 to present). Leading a student-run team building an AI-powered adtech marketplace for brands and influencers

## ~$ tail -n 5 advisories.log

Latest critical, GitHub-reviewed advisories. Refreshed daily by a GitHub Action.

<!-- ADVISORIES:START -->
- `CRITICAL` [CVE-2026-73802](https://github.com/advisories/GHSA-x4q3-gcj3-m6cf) | gitea-runner: workflow container.options passes host namespaces and capability flags to job... | 2026-10-02
- `CRITICAL` [CVE-2026-10032](https://github.com/advisories/GHSA-72qq-p3r5-f7wq) | a2ui/webcore: openUrl permits javascript: URI execution via agent-supplied button actions | 2026-10-02
- `CRITICAL` [GHSA-v2f8-6655-7grj](https://github.com/advisories/GHSA-v2f8-6655-7grj) | Vibe-Trading FastAPI endpoints permit unauthenticated access, file upload, and an RCE chain | 2026-10-02
- `CRITICAL` [GHSA-jqmf-mx4f-hfr6](https://github.com/advisories/GHSA-jqmf-mx4f-hfr6) | Vibe-Trading LLM-callable tools permit command execution, code injection, and SSRF | 2026-10-02
- `CRITICAL` [GHSA-gg6r-gp4c-89hp](https://github.com/advisories/GHSA-gg6r-gp4c-89hp) | Trigger.dev: V1 coordinator default-secret unauth Socket.IO | 2026-10-02

<sub>Source: GitHub Advisory Database | synced 2026-10-03 20:01 UTC</sub>
<!-- ADVISORIES:END -->

## ~$ ls skills/

<img src="https://skillicons.dev/icons?i=python,java,ts,fastapi,nextjs,react,tailwind,docker,postgres,redis,git,githubactions,linux,bash&theme=dark" alt="Skills" />

**Security tooling:** OWASP ZAP, Nikto, Nuclei, Nmap, testssl.sh, FFUF, Burp Suite, CVSS v3.1
**Also:** Celery, SQLAlchemy, Alembic, Caddy, Ollama, Selenium, SQL

## ~$ ./connect

[LinkedIn](https://www.linkedin.com/in/aayush-yadav-477028370) | [ONUS](https://tryonus.tech) | [TryHackMe](https://tryhackme.com/p/maverickaayush) | [GitHub](https://github.com/maverickaayush)
