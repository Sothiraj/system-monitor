#!/usr/bin/env python3
"""Generate a clean, one-page, ATS-friendly CV that matches the portfolio.

    python3 tools/make-cv.py            # writes ../assets/YOUR-NAME-CV.pdf

Edit the CONTENT dict below (or export your own copy) and re-run.
Only core PDF fonts are used, so the output stays copy/paste selectable and
parses fine through resume-screening software.
"""
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:  # pragma: no cover
    raise SystemExit("pip install fpdf2   (then re-run this script)")

OUT = Path(__file__).resolve().parent.parent / "assets" / "YOUR-NAME-CV.pdf"

CONTENT = {
    "name": "YOUR NAME",
    "headline": "Cybersecurity Analyst & Certified Ethical Hacker  |  B.E. Computer Science & Engineering",
    "contact": ["Salem, Tamil Nadu, India  ·  +91 90000 00000", "you@yourhandle.dev  ·  github.com/yourusername  ·  linkedin.com/in/yourusername"],
    "sections": [
        ("PROFESSIONAL SUMMARY", [
            "Security engineer with a B.E. in Computer Science and hands-on offensive and defensive experience: "
            "9 scoped VAPT engagements delivered, one year of SOC triage (Splunk/Wazuh), and detection-as-code shipped to production teams.",
            "Writes the proof-of-concept, the fix and the report a manager can forward — 31 developer-validated findings, mean "
            "remediation time cut from 34 to 11 days. 2 CVEs credited, 9 valid VDP/bounty reports, 18 public writeups.",
        ]),
        ("CORE SKILLS", [
            "**Offensive:** Web & API pentesting (OWASP WSTG/ASVS), network + Active Directory attacks, privilege escalation, "
            "recon/OSINT, Burp Suite Pro, Nmap, Metasploit, BloodHound",
            "**Defensive:** SIEM engineering (Splunk, Wazuh, ELK), detection-as-code (Sigma), Suricata/YARA, incident response, "
            "threat hunting (ATT&CK), Volatility/Autopsy forensics",
            "**Engineering:** Python, Bash, SQL, C, Linux hardening, Docker, AWS security, GitHub Actions, Semgrep/Bandit CI gates",
        ]),
        ("EXPERIENCE", [
            ("Security Analyst & Freelance Penetration Tester — Independent", "2025 – Present  ·  Salem / Remote"),
            ["Delivered **9** scoped web, API and network assessments for SaaS and retail clients; produced CVSS-scored reports "
             "with per-finding remediation patches and regression tests.",
             "Built a reusable reporting kit (templated DOCX, CVSS calculator, evidence hashing) that halved turnaround between "
             "last test and final report.",
             "Ran ransomware and third-party-compromise tabletop exercises for leadership; retested every fix at no extra cost."],
            ("SOC Intern (L1 -> L2 triage) — [Client Name] Cyber Defense", "2024 – 2025  ·  Chennai / Hybrid"),
            ["Triaged **~120** alerts/week in Splunk; escalated **14** true positives including a credential-stuffing wave and one "
             "beaconing host found by correlation, not by the vendor rule.",
             "Automated IP/asset enrichment in Python (geo -> ASN -> reputation), cutting average triage time by **4 minutes** per alert.",
             "Authored 6 Sigma detections and 3 IR runbooks adopted across the full shift."],
            ("Founder & Lead — College Cybersecurity Club and CTF team '0xSalem'", "2023 – 2024  ·  Campus"),
            ["Grew membership from 12 to **90+**; ran weekly labs on Wireshark, Burp, privilege escalation and malware triage.",
             "Designed and defended an internal Jeopardy CTF for 140 players; top-15 finish in 3 inter-collegiate CTFs."],
        ]),
        ("PROJECTS", [
            "**Sentinel-SOC** — full blue-team pipeline (Winlogbeat + Sysmon -> Wazuh -> Suricata -> TheHive) with 40 unit-tested Sigma rules and a Slack alert bot.",
            "**VulnScan AI** — continuous attack-surface scanning (subdomain enum -> httpx -> nuclei) with LLM triage, dedupe and automatic ticket drafting.",
            "**PhishGuard** — phishing URL detector: 32 lexical/WHOIS features, gradient-boosted classifier at 0.96 F1, shipped as a browser extension and an ICAP service.",
            "**KeyHunt** — YARA + entropy secret-leak hunter for CI artefacts and container layers.  **TokenSentry** — JWT/OAuth misconfiguration checker.  **CryptoVault** — Argon2id + AES-256-GCM file encryptor.",
            "",
        ]),
        ("EDUCATION", [
            ("B.E. Computer Science & Engineering — [College Name], Anna University", "2021 – 2025  ·  CGPA 8.6 / 10"),
            ["Coursework: Operating Systems, Computer Networks, DBMS, Compiler Design, Cryptography & Network Security, Machine Learning.",
             "Final-year project: 'Adaptive IDS for IoT using lightweight ML' on a Raspberry Pi cluster — departmental best-project shortlist."],
        ]),
        ("CERTIFICATIONS & RECOGNITION", [
            "eJPTv2 — Junior Penetration Tester (INE, 2025)  ·  CompTIA Security+ SY0-701 (in progress, Q4 2026)  ·  HTB CPTS (coursework 80%)  ·  CEH Practical, BTL1 (planned)",
            "Hack The Box: 42 machines owned  ·  TryHackMe: 97 rooms  ·  1,240 logged lab hours  ·  Finalist, National Hackathon security track (top 8 / 240)  ·  Dean's List ×4",
        ]),
    ],
}


class CV(FPDF):
    ML, MR, MT = 14, 14, 12
    BODY, LEAD = 3.85, 1.32

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        # core Helvetica is latin-1 only; cp1252 lets us keep real — • “ ” quotes
        self.core_fonts_encoding = "cp1252"
        self.set_auto_page_break(True, margin=10)
        self.set_margins(self.ML, self.MT, self.MR)


    def heading(self, text):
        if self.get_y() > 258:
            self.add_page()
        self.ln(2.4)
        self.set_font("helvetica", "B", 9.6)
        self.set_text_color(16, 34, 60)
        self.cell(0, 4.4, text.upper(), new_x="LMARGIN", new_y="NEXT")
        y = self.get_y() + 0.5
        self.set_draw_color(0, 121, 92)
        self.set_line_width(0.45)
        self.line(self.ML, y, self.ML + 16, y)
        self.set_draw_color(205, 214, 226)
        self.set_line_width(0.2)
        self.line(self.ML + 16.5, y, self.epw, y)
        self.ln(2.1)

    def para(self, text, size=8.7, italic=False, gap=0.7):
        self.set_font("helvetica", "I" if italic else "", size)
        self.set_text_color(48, 60, 78)
        self.multi_cell(self.epw, self.BODY, text, align="J", markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(gap)

    def bullet(self, text):
        self.set_left_margin(self.ML + 4.4)
        self.set_x(self.ML + 4.4)
        self.set_font("helvetica", "", 8.7)
        self.set_text_color(48, 60, 78)
        self.multi_cell(self.epw - 4.4, self.BODY, "\u2022  " + text, markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.set_left_margin(self.ML)
        self.ln(0.35)

    def entry_title(self, left, right):
        self.set_font("helvetica", "B", 9.1)
        self.set_text_color(12, 24, 40)
        self.set_right_margin(self.MR + self.get_string_width(right) + 2)
        self.cell(0, 4.1, left, new_x="LMARGIN", new_y="NEXT")
        self.set_right_margin(self.MR)
        self.set_font("helvetica", "", 7.9)
        self.set_text_color(110, 122, 140)
        self.set_y(self.get_y() - 4.0)
        self.cell(self.epw, 4.1, right, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.3)


def build():
    pdf = CV()
    pdf.add_page()

    # header band
    pdf.set_fill_color(244, 247, 251)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_xy(pdf.ML, 9)
    pdf.set_font("helvetica", "B", 19)
    pdf.set_text_color(8, 16, 28)
    pdf.cell(0, 9, CONTENT["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 8.9)
    pdf.set_text_color(0, 105, 80)
    pdf.cell(0, 4.6, CONTENT["headline"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)
    pdf.set_font("helvetica", "", 8.1)
    pdf.set_text_color(70, 82, 100)
    for line in CONTENT["contact"]:
        pdf.cell(0, 3.9, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(36.5)

    for title, blocks in CONTENT["sections"]:
        pdf.heading(title)
        for block in blocks:
            if isinstance(block, str):
                pdf.para(block)
            elif isinstance(block, list):
                for b in block:
                    pdf.bullet(b)
                pdf.ln(0.6)
            else:  # (title, meta) pair -> project or job header
                text, meta = block
                if meta:
                    pdf.entry_title(text, meta)
                else:
                    pdf.para("**" + text + "**", size=8.7, gap=0.4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    pages = "unknown"
    print(f"wrote {path.relative_to(path.parents[2])}  ({path.stat().st_size/1024:.1f} KB)")
