"""Seed the SAMRUDHI pilot database with 3 consenting healthcare clients and
one sample deliverable (idempotent)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db import Database  # noqa: E402

CLIENTS = [
    {
        "name": "Arogya Multi-Speciality Hospital",
        "specialty": "multi-speciality hospital (cardiology, orthopaedics, paediatrics)",
        "geography": "Hyderabad, India",
        "tone": "warm, trustworthy, reassuring, professional",
        "audience": "patients and their families seeking specialist care",
        "channels": "Instagram, Facebook, YouTube",
        "brand_do": "Use real clinician voices, plain language, calming visuals",
        "brand_dont": "No fear-based messaging, no outcome guarantees, no patient imagery",
    },
    {
        "name": "Snehaa Women's Health Clinic",
        "specialty": "women's health & reproductive care clinic",
        "geography": "Pune, India",
        "tone": "empathetic, dignified, confidential, supportive",
        "audience": "women aged 20-45 and their families",
        "channels": "Instagram, Facebook",
        "brand_do": "Respect privacy, use inclusive language, destigmatise topics",
        "brand_dont": "No before/after imagery, no unapproved testimonials, no diagnosis claims",
    },
    {
        "name": "Vaidya Ayurveda Wellness Centre",
        "specialty": "ayurveda & preventive wellness centre",
        "geography": "Rishikesh, India",
        "tone": "calm, grounded, evidence-aware, traditional yet modern",
        "audience": "wellness seekers and patients exploring ayurvedic care",
        "channels": "Instagram, YouTube",
        "brand_do": "Ground claims in classical + modern evidence, seasonal framing",
        "brand_dont": "No cure claims, no disease-treatment guarantees, no unverified remedies",
    },
]

SAMPLE_DELIVERABLES = [
    ("Arogya Multi-Speciality Hospital",
     "Understanding Angina: When Chest Pain Needs a Doctor",
     "carousel", "recognising angina and when to seek emergency care"),
    ("Snehaa Women's Health Clinic",
     "PCOS Myths vs. Facts: A Calm Guide",
     "static post", "common PCOS misconceptions and evidence-based basics"),
    ("Vaidya Ayurveda Wellness Centre",
     "Monsoon Wellness: 5 Ayurvedic Habits, Evidence-Checked",
     "short-form script", "monsoon season wellness habits with evidence checks"),
]


def main() -> None:
    settings = get_settings()
    db = Database(settings.db_path)
    clients = db.list_clients()
    if not clients:
        for c in CLIENTS:
            created = db.create_client(**c)
            print(f"created client {created['id']} — {c['name']}")
    else:
        print(f"{len(clients)} clients already present")

    # map client name -> id
    clients_by_name = {c["name"]: c["id"] for c in db.list_clients()}
    existing = {d["title"] for d in db.list_deliverables()}
    for client_name, title, ctype, topic in SAMPLE_DELIVERABLES:
        if title in existing:
            continue
        cid = clients_by_name.get(client_name)
        if not cid:
            continue
        d = db.create_deliverable(client_id=cid, title=title,
                                  content_type=ctype, topic=topic, brief={})
        db.log(d["id"], "Shruti", "deliverable.created",
               f"content_type={ctype} (seeded)")
        print(f"created deliverable {d['id']} — {title}")
    print("seed complete")


if __name__ == "__main__":
    main()