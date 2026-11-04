# Torii — What We Need to Build
### Simple Task List for the Team

> **Date:** October 2026 · **For:** CEO, Founders, Team Leads

---

## First — What We Already Have ✅

Good news: a lot of the hard work is already done by the engineering team.
We do NOT need to rebuild these:

- ✅ The intake form system (user answers questions, form fills itself)
- ✅ AI that researches visa rules for every country automatically
- ✅ Checklist system (tells user which documents they need)
- ✅ Eligibility checker (tells user if they qualify for the visa)
- ✅ Automatic PDF form filler (fills official embassy forms)
- ✅ Full printable dossier generator (creates the ready-to-print packet)
- ✅ Passport scanner (reads passport details from a photo)
- ✅ AI letter writer (writes cover letters, referral letters, etc.)
- ✅ Payment system (charges users, processes cards)
- ✅ Background task runner (runs things automatically in the background)
- ✅ Indian Medical Visa application flow (already fully built)

---

## What We Still Need to Build

There are **4 big things** missing. Below is a simple task list for each.

---

## 🏷️ Thing 1 — Tell Users Clearly What WE Will Do vs What THEY Need to Do
> **Start immediately. Takes about 1–2 weeks.**

Right now the system doesn't clearly tell the user:
- "We will submit your visa automatically" (eVisa countries)
- "We will fill the online form, but you need to go to IVAC" (India Medical Visa)
- "You need to go to VFS yourself, but we'll prepare everything for you" (Schengen, UK)

**Tasks:**
- [x] For each country in our system, mark it as one of three types:
  - **Digital** = We do everything online, user does nothing
  - **Hybrid** = We fill the online form + user goes to IVAC/embassy with our printed packet
  - **Consular** = User must go to embassy, we prepare the perfect packet for them
- [x] Show the correct message to the user on their application page so they know exactly what to expect
- [x] Make sure India Medical Visa is marked as **Hybrid** (online form + IVAC visit)

---

## 🏷️ Thing 2 — Document Concierge (Help Users Get Hard-to-Get Documents)
> **Start in Week 3. Takes about 2–3 weeks.**

Right now, if a user is missing a document, we just show them a red ❌.
We need to add a button that says **"We can get this for you — $X"**.

### 2A. Dummy Flight Reservation
- [x] Sign up with a dummy flight ticket service (they hold a real airline booking for 3 days without paying)
- [x] When user is missing a flight booking, show "Get Flight Reservation — $12"
- [x] Deliver the PDF flight itinerary to their account automatically

### 2B. Travel Insurance Certificate
- [x] Sign up with an insurance company API (AXA or similar)
- [x] When user needs Schengen insurance, show "Get Travel Insurance — $15"
- [x] Deliver the official insurance certificate PDF to their account instantly

### 2C. Doctor Referral Letter Template
- [x] Use our existing AI letter writer to create a professional referral letter template
- [x] When user is missing a doctor referral, show "Generate Referral Letter — $19"
- [x] User downloads it, takes it to their local doctor to sign — takes the doctor 30 seconds

### 2D. Hotel Confirmation Letter
- [x] Connect to Booking.com (free-cancellation rooms, no payment needed upfront)
- [x] When user is missing hotel proof, show "Get Hotel Confirmation — Free" (we earn commission from Booking.com)
- [x] Deliver hotel confirmation letter to their account

### 2E. Invitation Letter (for visiting family or friends)
- [x] Use our AI letter writer to generate a correctly worded host invitation letter
- [x] Show "Generate Invitation Letter — $14"
- [x] Host fills in their name and signs it

### 2F. Update the Checklist Screen
- [x] For every missing document that we can help with, add a green **"Get This — $X"** button
- [x] After user purchases, show them a status card: "Processing... ✅ Delivered"

---

## 🏷️ Thing 3 — The eVisa Submission Bot (We Submit the Visa Automatically)
> **Start in Week 6. Takes about 4 weeks.**

This is the big one. For countries with fully digital visas (Vietnam, Egypt, Bahrain, etc.),
**we need a robot that goes to the government website and submits the application for the user.**

### 3A. Set Up the Robot's Tools
- [x] Sign up for **BrightData** — this gives our robot a real home internet connection so the government website doesn't know it's a robot
- [x] Sign up for **CapSolver** — this solves the "I am not a robot" puzzle when it appears
- [x] Set up **Stripe Issuing** — this creates a temporary virtual debit card so our robot can pay the government visa fee

### 3B. Build the Robot Brain
- [x] Build a system that can open a website, fill forms, click buttons, and upload photos — just like a human does
- [x] Make the robot look and behave exactly like a real person using Chrome on a laptop
- [x] Build a card payment module so the robot can pay the government fee with a virtual card
- [x] When the robot finishes, it downloads the approved visa PDF and puts it in the user's account

### 3C. Build a Robot for Each eVisa Country (Phase 1 — Easy Countries First)
- [x] 🇻🇳 **Vietnam** — evisa.xuatnhapcanh.gov.vn
- [x] 🇪🇬 **Egypt** — visa2egypt.gov.eg
- [x] 🇧🇭 **Bahrain** — evisa.gov.bh
- [x] 🇰🇭 **Cambodia** — evisa.gov.kh
- [x] 🇯🇴 **Jordan** — eservices.moi.gov.jo
- [x] 🇶🇦 **Qatar** — portal.moi.gov.qa
- [x] 🇱🇰 **Sri Lanka** — eta.gov.lk

### 3D. Build Robot for Phase 2 Countries (Harder — Have Captcha/Bot Protection)
- [x] 🇹🇷 **Turkey** — evisa.gov.tr
- [x] 🇸🇦 **Saudi Arabia** — visa.mofa.gov.sa
- [x] 🇲🇾 **Malaysia** — evisamalaysia.com

### 3E. Monitoring
- [x] Build a simple dashboard in the admin panel: how many bots are running, success rate, any failures

---

## 🏷️ Thing 4 — The Appointment Slot Sniper
> **Start in Week 10. Takes about 2–3 weeks.**

The biggest problem for people applying at VFS or IVAC is **finding an appointment**.
Everything is booked for months. We need a bot that watches 24/7 and grabs a slot the moment one opens.

- [ ] Build a background system that checks VFS appointment availability every 10 minutes, non-stop
- [ ] Do the same for IVAC Bangladesh (India visa appointments)
- [ ] Do the same for US Consulate appointments
- [ ] The moment a slot opens → **immediately send the user an SMS + email alert**
- [ ] Optional: if the user said "auto-book for me" → the bot books it automatically
- [ ] Add a button on the user's application page: **"Activate Slot Sniper — $49"**

---

## 🏷️ Thing 5 — Hospital Letter Partnership (For Medical Visas)
> **Start in Week 13. CEO does the business part first.**

For India Medical Visa, the user needs an official letter from the Indian hospital.
We need to become a partner with these hospitals so we can request the letter on the patient's behalf.

### CEO/Business Development Tasks
- [ ] Email Apollo Hospitals international department — ask to become a referral partner
- [ ] Email Fortis Healthcare international department — ask to become a referral partner
- [ ] Email Medanta hospital — ask to become a referral partner
- [ ] Email Bumrungrad Hospital Bangkok (Thailand) — ask to become a referral partner
- [ ] Negotiate: We send them patients → they pay us a referral fee AND we charge the patient a coordination fee

### Engineering Tasks (after agreements are signed)
- [ ] Build a system to automatically send appointment request emails to partner hospitals
- [ ] When hospital sends back the letter, automatically upload it to the patient's account
- [ ] Add **"Get Hospital Invitation Letter — $39"** button to India Medical Visa checklist

---

## 📅 Simple Timeline Summary

| When | What We're Building |
| :--- | :--- |
| **Week 1–2** | Show users clearly what Torii will do vs what they need to do themselves |
| **Week 3–5** | Document Concierge — dummy flights, insurance, doctor referral, hotel, invitation letter |
| **Week 6–9** | eVisa Robot — 7 easy countries (Vietnam, Egypt, Bahrain, etc.) |
| **Week 10–12** | Appointment Slot Sniper — VFS, IVAC, US Consulate |
| **Week 13–16** | Hospital letter partnerships (CEO starts this in Week 1 in parallel) |
| **Week 17–20** | eVisa Robot — Turkey, Saudi Arabia, Malaysia (harder countries) |

---

## 🚫 What We Will NOT Build (Save Time and Money)

- ❌ A robot for USA, UK, Canada visas — these websites use the most advanced bot protection in the world. Not worth fighting right now.
- ❌ Our own telemedicine platform — we will partner with an existing licensed doctor service
- ❌ Our own insurance company — we will just earn commission from AXA or a similar insurer
- ❌ A mobile app — the website is enough until we are making $500K/month

---

*This plan lives in the `Businees-research` branch. See also [BUSINESS_PLAN.md](BUSINESS_PLAN.md) for the full business strategy.*
