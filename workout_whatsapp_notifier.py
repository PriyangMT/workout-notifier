#!/usr/bin/env python3
"""
Workout WhatsApp Notifier (Twilio Sandbox edition, v7.1)
- Uses ONLY Google links (max click reliability)
- Auto-chunks long messages to fit Twilio's 1600-char limit (error 21617)
- Keeps form cues, prescriptions, alias sending, and optional rest-day logic
"""

import os
import argparse
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from twilio.rest import Client
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from urllib.parse import quote_plus

EXCEL_PATH = os.environ.get("WORKOUT_EXCEL_PATH", "Beginner_Weekly_Workout_Plan.xlsx")
STATE_FILE = "last_day.json"
MAX_CHARS = int(os.environ.get("MAX_MESSAGE_CHARS", "1500"))  # safe buffer under 1600

# --- Form cues ---
FORM_CUES = {
    "Seated Cable Rows": "Back straight, squeeze shoulder blades.",
    "Lat Pulldown": "Chest up; pull bar to upper chest; no swing.",
    "DB Bent-Over Row": "Hinge hips, neutral spine, pull to waist.",
    "Dumbbell Bicep Curls": "Elbows tucked; no swing.",
    "Face Pulls": "Lead with elbows; rope to forehead.",
    "Dumbbell Shoulder Press": "No back arch; smooth press.",
    "Dumbbell Bench Press": "Lower to chest; don’t flare elbows.",
    "Push Up": "Straight line; don’t sag hips.",
    "Squat": "Chest tall; knees out; hips back.",
    "Leg Press": "Feet shoulder-width; full control.",
    "Lunge": "Step forward; knee over ankle.",
    "Romanian Deadlift": "Soft knees; hinge; hamstring stretch.",
    "Plank": "Hips level; brace core.",
    "Side Plank": "Stack shoulders & hips.",
    "Kettlebell Swings": "Hinge; snap glutes; don’t squat.",
    "DB Thrusters": "Full squat then press overhead.",
    "Jump Rope": "Light bounce; upright.",
}

# --- Exercise prescriptions (sets/reps/rest) ---
EXERCISE_PRESCRIPTIONS = {
    "Seated Cable Rows": {"sets": 3, "reps": "10–12", "rest": "60–90s"},
    "Lat Pulldown": {"sets": 3, "reps": "10–12", "rest": "60–90s"},
    "DB Bent-Over Row": {"sets": 3, "reps": "10–12", "rest": "60–90s"},
    "Dumbbell Bicep Curls": {"sets": 3, "reps": "12–15", "rest": "45s"},
    "Face Pulls": {"sets": 3, "reps": "12–15", "rest": "45s"},
    "Dumbbell Shoulder Press": {"sets": 3, "reps": "10–12", "rest": "60s"},
    "Dumbbell Bench Press": {"sets": 3, "reps": "10–12", "rest": "60–90s"},
    "Push Up": {"sets": 3, "reps": "10–15", "rest": "45–60s"},
    "Squat": {"sets": 3, "reps": "10–12", "rest": "90s"},
    "Leg Press": {"sets": 3, "reps": "10–12", "rest": "90s"},
    "Lunge": {"sets": 3, "reps": "10/leg", "rest": "60s"},
    "Romanian Deadlift": {"sets": 3, "reps": "10–12", "rest": "90s"},
    "Plank": {"sets": 3, "reps": "30–45s hold", "rest": "30s"},
    "Side Plank": {"sets": 3, "reps": "20–30s/side", "rest": "30s"},
    "Kettlebell Swings": {"sets": "EMOM", "reps": "10 reps/min", "rest": "balance of min"},
    "DB Thrusters": {"sets": "EMOM", "reps": "8 reps/min", "rest": "balance of min"},
    "Jump Rope": {"sets": "EMOM", "reps": "20 skips/min", "rest": "balance of min"},
}

# --- Warmups & cooldowns (names only; links via Google) ---
WARMUPS = {
    "pull": ["Arm Circles", "Cat–Cow"],
    "push": ["Arm Circles", "Doorway Chest Stretch"],
    "legs": ["Standing Quad Stretch", "Hamstring Stretch"],
    "cardio": ["Arm Circles", "Standing Quad Stretch"],
    "general": ["Arm Circles", "Cat–Cow"],
}

COOLDOWNS = {
    "pull": ["Child’s pose", "Hamstring Stretch"],
    "push": ["Doorway Chest Stretch", "Child’s pose"],
    "legs": ["Standing Quad Stretch", "Hamstring Stretch", "Figure-4 Stretch"],
    "cardio": ["Child’s pose", "Hamstring Stretch"],
    "general": ["Child’s pose", "Hamstring Stretch"],
}

def classify_day(day_name: str) -> str:
    name = (day_name or "").lower()
    if "pull" in name: return "pull"
    if "push" in name: return "push"
    if "leg" in name or "legs" in name: return "legs"
    if "cardio" in name: return "cardio"
    return "general"

def load_plan(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    return df

def ordered_unique_days(df: pd.DataFrame):
    seen = set()
    out = []
    for d in df["Day"].dropna().tolist():
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out

def build_alias_map(df: pd.DataFrame):
    days = ordered_unique_days(df)
    counts = {"pull":0, "push":0, "legs":0, "cardio":0, "general":0}
    alias_to_day = {}
    rows = []
    for d in days:
        typ = classify_day(d)
        counts[typ] = counts.get(typ, 0) + 1
        alias = f"{typ}{counts[typ]}"
        alias_to_day[alias] = d
        if counts[typ] == 1:
            alias_to_day[typ] = d
        rows.append((alias, d))
    return alias_to_day, rows

def google_exercise_link(ex: str) -> str:
    q = quote_plus(f"site:musclewiki.com {ex}")
    return f"https://www.google.com/search?q={q}"

def google_ref_link(term: str, suffix: str) -> str:
    q = quote_plus(f"{term} {suffix}")
    return f"https://www.google.com/search?q={q}"

def build_message_for_day(df: pd.DataFrame, day: str) -> str:
    sub = df[df["Day"] == day]
    typ = classify_day(day)

    warm = [f"• {w}\n  {google_ref_link(w, 'warm up')}" for w in WARMUPS.get(typ, WARMUPS["general"])]
    cool = [f"• {c}\n  {google_ref_link(c, 'stretch')}" for c in COOLDOWNS.get(typ, COOLDOWNS["general"])]

    lines = []
    for _, r in sub.iterrows():
        ex = str(r["Exercise"]).strip()
        url = google_exercise_link(ex)
        cue = FORM_CUES.get(ex, "")
        details = f"- *{ex}*\n  {url}\n  Primary: {r['Primary Target']}"
        if str(r.get("Secondary Target", "")):
            details += f" | Secondary: {r['Secondary Target']}"
        if str(r.get("Tertiary Target", "")):
            details += f" | Tertiary: {r['Tertiary Target']}"
        if cue:
            details += f"\n  Form Cue: {cue}"
        pres = EXERCISE_PRESCRIPTIONS.get(ex)
        if pres:
            details += f"\n  Prescription: {pres['sets']} × {pres['reps']} | Rest: {pres['rest']}"
        lines.append(details)

    if typ == "cardio":
        lines = []
        for ex in ["Kettlebell Swings", "DB Thrusters", "Jump Rope"]:
            url = google_exercise_link(ex)
            cue = FORM_CUES.get(ex, "")
            pres = EXERCISE_PRESCRIPTIONS.get(ex, {})
            pres_str = f"{pres.get('sets')} × {pres.get('reps')} | Rest: {pres.get('rest')}" if pres else ""
            details = f"- *{ex}*\n  {url}\n  Form Cue: {cue}\n  Prescription: {pres_str}"
            lines.append(details)

    body = (
        f"📅 *{day}*\n\n"
        f"🔥 *Warm-up*\n" + "\n".join(warm) + "\n\n"
        f"🏋️ *Main Workout*\n" + "\n".join(lines) + "\n\n"
        f"🧊 *Cool-down*\n" + "\n".join(cool) + "\n\n"
        f"Reply *DONE* when finished 💪"
    )
    return body

def chunk_message(body: str, limit: int = MAX_CHARS):
    """Split body into multiple parts <= limit, preferring paragraph boundaries."""
    paras = body.split("\n\n")
    parts = []
    cur = ""
    for p in paras:
        add = (p + "\n\n")
        if len(cur) + len(add) <= limit:
            cur += add
        else:
            if cur:
                parts.append(cur.rstrip())
                cur = ""
            # If a single paragraph is too big, split by lines
            if len(add) > limit:
                lines = (p + "\n").split("\n")
                block = ""
                for ln in lines:
                    addl = ln + "\n"
                    if len(block) + len(addl) <= limit:
                        block += addl
                    else:
                        parts.append(block.rstrip())
                        block = addl
                if block:
                    parts.append(block.rstrip())
            else:
                cur = add
    if cur:
        parts.append(cur.rstrip())

    # Add part headers if multiple
    if len(parts) > 1:
        total = len(parts)
        parts = [f"(Part {i+1}/{total})\n\n{pt}" for i, pt in enumerate(parts)]
    return parts

def pick_day_for_today(days: list[str]) -> str:
    idx = datetime.now().weekday() % len(days)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        if state.get("rest_today"):
            state["rest_today"] = False
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
            return state["last_day"]
    return days[idx]

def send_whatsapp_parts(parts):
    load_dotenv()
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    to_list = [x.strip() for x in os.getenv("WHATSAPP_TO_LIST", "").split(",") if x.strip()]
    if not sid or not tok or not to_list:
        raise RuntimeError("Missing Twilio creds in .env")
    client = Client(sid, tok)
    for to in to_list:
        for i, part in enumerate(parts, 1):
            msg = client.messages.create(from_=from_num, to=to, body=part)
            print(f"Sent part {i}/{len(parts)} to {to}: SID={msg.sid}")

def job_send_today():
    df = load_plan(EXCEL_PATH)
    days = ordered_unique_days(df)
    day = pick_day_for_today(days)
    body = build_message_for_day(df, day)
    parts = chunk_message(body, MAX_CHARS)
    send_whatsapp_parts(parts)
    with open(STATE_FILE, "w") as f:
        json.dump({"last_day": day, "rest_today": False}, f)

def schedule_daily():
    load_dotenv()
    ist = pytz.timezone("Asia/Kolkata")
    hhmm = os.getenv("SEND_TIME_IST", "07:00")
    hh, mm = [int(x) for x in hhmm.split(":")]
    sched = BlockingScheduler(timezone=ist)
    trigger = CronTrigger(hour=hh, minute=mm)
    sched.add_job(job_send_today, trigger=trigger, name="daily_whatsapp_workout")
    print(f"Scheduler started. Messages will go daily at {hh:02d}:{mm:02d} IST.")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-today", action="store_true")
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--send-key", type=str)
    parser.add_argument("--send-day", type=str)
    parser.add_argument("--list-keys", action="store_true")
    args = parser.parse_args()

    df = load_plan(EXCEL_PATH)
    days = ordered_unique_days(df)
    alias_map, rows = build_alias_map(df)

    if args.list_keys:
        print("Available aliases:")
        width = max(len(a) for a,_ in rows) if rows else 8
        for a, d in rows:
            print(f"  {a.ljust(width)} -> {d}")
        for simple in ["pull", "push", "legs", "cardio"]:
            if simple in alias_map:
                print(f"  {simple.ljust(width)} -> {alias_map[simple]}")
    elif args.send_key:
        key = args.send_key.strip().lower()
        if key not in alias_map:
            print(f"Alias '{key}' not found. Use --list-keys to see options.")
        else:
            day = alias_map[key]
            body = build_message_for_day(df, day)
            parts = chunk_message(body, MAX_CHARS)
            send_whatsapp_parts(parts)
            with open(STATE_FILE, "w") as f:
                json.dump({"last_day": day, "rest_today": False}, f)
    elif args.send_day:
        day = args.send_day.strip()
        if day not in days:
            print(f"Day '{day}' not found in Excel. Options: {days}")
        else:
            body = build_message_for_day(df, day)
            parts = chunk_message(body, MAX_CHARS)
            send_whatsapp_parts(parts)
            with open(STATE_FILE, "w") as f:
                json.dump({"last_day": day, "rest_today": False}, f)
    elif args.preview:
        day = pick_day_for_today(days)
        text = build_message_for_day(df, day)
        parts = chunk_message(text, MAX_CHARS)
        print("== Preview ==")
        for i, p in enumerate(parts, 1):
            print(f"\n--- Part {i}/{len(parts)} ({len(p)} chars) ---\n{p}")
    elif args.send_today:
        job_send_today()
    elif args.schedule:
        schedule_daily()
    else:
        print("Use --list-keys, --send-key, --send-day, --preview, --send-today, or --schedule")
