# Going Live With a Real Team — Checklist

**This is product/engineering guidance, not legal advice.** Everything
below should be reviewed by an actual attorney, compliance officer, and
security professional before any of it is acted on — same disclaimer as
`PRIVACY.md`. The point of this document is to give you an accurate list
of what's involved so you know what to ask for, not to be a substitute
for asking for it.

**Nothing here needs to happen for the current portfolio/demo use case.**
This only matters if "try this with Arkansas or another team" stops
meaning "synthetic wellness data + real box scores for a demo" and starts
meaning "collect and store real athletes' real medical/wellness data."
That's a different, much bigger project than anything documented in
`SETUP_GUIDE.md` or `MULTI_SPORT_SETUP.md`.

---

## Phase 0: Figure out what you'd actually be collecting

This changes everything else, so decide it first.

- **Performance/game stats only** (box scores, GPS, shot data) — lower
  risk, closer to what's already public via ESPN/box scores anyway.
- **Wellness/medical data** (sleep, soreness, injuries, HRV, force plate)
  tied to a real, named athlete — this is the category that triggers
  FERPA (student education records at a university) and potentially
  HIPAA (if handled by athletic training/medical staff acting as a
  covered entity or business associate). This is what's currently
  synthetic in WAIMS and needs to stay synthetic until the rest of this
  checklist is actually done.

---

## Phase 1: Legal & compliance foundation

- **FERPA review** — university student records law. Get the athletic
  department's compliance office to confirm whether this data counts as
  an "education record" and who has "legitimate educational interest"
  (see `PRIVACY.md` for the FERPA links already in the repo).
- **HIPAA applicability determination** — not automatic; depends on
  whether team medical staff are acting as a HIPAA covered entity for
  this data. Get an actual determination, don't assume either way.
- **Data use agreement / athlete consent** — athletes should know what's
  collected, who sees it, and how long it's kept, in writing, with actual
  consent, not implied consent from being on the roster.
- **University counsel sign-off** before any real data touches the system.

---

## Phase 2: Technical security (the actual engineering work)

Current state, for reference: `auth.py` has hardcoded demo
username/password pairs in source code, no encryption at rest, no audit
logging. None of this is acceptable for real athlete data.

- **Real authentication** — at minimum, real password hashing (not
  plaintext-in-code); ideally SSO through the university's identity
  provider (Okta / Azure AD / Shibboleth), so accounts are managed
  centrally and can be revoked when someone leaves the program.
- **Role-based access control, audited** — the `TAB_ACCESS` system
  already exists structurally; it needs a real review to confirm it
  actually restricts what it's supposed to, not just visually hides tabs.
- **Encryption at rest and in transit** — the SQLite-file-on-disk model
  works for a demo; real data needs a properly access-controlled database
  with encryption, not a file anyone with filesystem access can open.
- **Audit logging** — who viewed which athlete's data, when. Required for
  any real accountability, and often required for compliance.
- **Secrets management** — no API keys or credentials in source code or
  the repo, ever, once real data is involved (this repo is currently
  public).
- **Dependency/vulnerability scanning** — ongoing, not one-time.

---

## Phase 3: Hosting

- **Streamlit Community Cloud is not appropriate for this** once real
  sensitive data is involved — no Business Associate Agreement (BAA)
  available, no enterprise-grade access control, no compliance
  guarantees. It's fine for the current synthetic-data demo; it is not
  fine for real athlete medical data.
- **Realistic options**: university-hosted infrastructure (if IT/security
  will support and sign off on it), a cloud provider (AWS/Azure/GCP) with
  a signed BAA, or a vendor that specifically sells into sports
  medicine/compliance (this space exists — e.g., Teamworks-style
  platforms already solve this; worth asking whether buying vs. building
  makes more sense once real data is involved).
- **Backup and disaster recovery plan** — written down, tested, not
  assumed.
- **Data retention and deletion policy** — how long data is kept after an
  athlete leaves the program, and a real process for deleting it.

---

## Phase 4: If partnering with a university CS department (e.g., UA)

This is a genuinely good way to get real engineering work done — SSO
integration, audit logging, security hardening are exactly the kind of
scoped, well-defined project a capstone or research group could take on.
But it adds its own requirements on top of everything above:

- **MOU (Memorandum of Understanding)** between the athletic department
  and the CS department, in writing, covering: who owns the code and any
  resulting IP, who's liable if something goes wrong (a breach, or a
  faulty risk prediction that leads to a bad decision), and what happens
  to the code/data when the partnership or a given student's involvement
  ends.
- **IRB (Institutional Review Board) approval** is very likely required
  if any student or faculty research use touches real athlete data —
  especially if any results ever get published, presented, or used in a
  thesis. This applies even to what feels like "just building a tool,"
  if the underlying work involves analyzing real human subjects' health
  data. Ask the IRB office before assuming it doesn't apply, not after.
- **CITI training** (or the university's equivalent human-subjects
  research training) for any student or faculty member who'll have real
  data access under an IRB protocol.
- **Scope student access carefully.** A reasonable pattern: give students
  a synthetic or de-identified subset to build and test against (the
  existing synthetic-data demo is already most of the way there), and
  keep real data access restricted to a much smaller, vetted group —
  rather than the whole class/lab having open access to real records.
- **IP/ownership clarity up front.** Some universities claim IP over
  student work by default; get this settled in writing before any student
  code lands in a repo that has real athlete data anywhere near it.

---

## Phase 5: Ongoing operations

- **Incident response plan** — a real, written "what do we do the day of
  a breach" plan, not something improvised after the fact.
- **Staff training** — everyone with access understands what they can and
  can't do with the data, not just "here's your login."
- **Periodic security review** — not a one-time checklist, a recurring
  cadence (e.g., annual, or whenever hosting/auth changes).

---

## Bottom line

Nothing in Phases 1-5 is a documentation task or a code change you can
make solo in an afternoon — it's legal review, a real auth system, a
compliant hosting decision, and (if going the university route) an MOU
and IRB approval. The honest next step, if this ever becomes real, is
starting conversations with the athletic department's compliance office
and, if pursuing the CS department partnership, that department's
research administration — not writing more code first.
