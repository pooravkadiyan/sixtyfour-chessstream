# Electronic Chess Board Manufacturing Opportunity — Research Report

**For: Monara Ventures (Poorav Kadiyan)**  
**Date: October 15, 2026**

---

## Executive Summary

The electronic chess board manufacturing opportunity in India is **technically feasible** with the key patent barrier removed, but achieving the ₹1,000 target cost is aggressive. The market is real but fragmented, and a rental-first model appears more viable than direct sales. DGT's dominance stems from ecosystem lock-in (LiveChess software, tournament integrations) rather than hardware superiority.

**Key Numbers:**
- DGT Smart Board: €295 (~₹27,000) | DGT Wooden boards: €500-€1,750
- Open-source BOM (ChessTrace): ₹1,850 at retail component prices
- India FIDE-rated tournaments: ~570/year (1,138 in Nov 2024–Oct 2026)
- DGT patent US6168158B1: **Expired 2013** (non-payment of maintenance fees)

---

## 1. DGT Board Market Analysis

### Current DGT Pricing (2026)

| Model | Price (EUR) | Price (INR approx.) |
|-------|-------------|---------------------|
| DGT Pegasus (entry-level) | €189 | ₹17,000 |
| DGT Smart Board (plastic, tournament) | €295-€330 | ₹27,000-₹30,000 |
| USB e-Board Walnut | €500 | ₹45,000 |
| USB e-Board Wengé | €520 | ₹47,000 |
| USB e-Board Rosewood | €530 | ₹48,000 |
| Bluetooth e-Board Walnut | €685 | ₹62,000 |
| Bluetooth e-Board Rosewood | €715 | ₹65,000 |
| Bluetooth e-Board Black & Red Leather | €1,750 | ₹1,60,000 |

**India pricing:** Chennai Chess Products lists DGT Smart Board at ₹36,000-₹40,000. Historical reference: ₹25,000 per board was cited for the 2018 IIFL tournament setup.

### What Makes DGT Expensive?

1. **RFID/Resonance coil technology** — Each piece contains a unique resonance coil for piece identification (not just occupancy detection)
2. **Premium materials** — Wooden boards use real walnut, rosewood, wengé
3. **Software ecosystem** — LiveChess software, cloud service, Chess.com/Lichess integrations
4. **Tournament certification** — FIDE-approved, used at World Championships since 1998
5. **Low volume manufacturing** — Netherlands-based, not mass-produced
6. **R&D amortization** — Decades of development costs

### Competitors

| Brand | Price Range | Key Features |
|-------|-------------|--------------|
| **Chessnut** (Air/Pro/Evo) | $162-$719 | Chip-based recognition, Chess.com/Lichess, built-in AI |
| **Square Off** (Miko Grand) | $549 | Robotic self-moving pieces, premium design |
| **ChessUp 2** | ~$259 | LED move guidance, beginner-focused |
| **GoChess** | $199-$449 | 32 AI levels, robotic option |
| **Millennium** (ChessGenius Pro) | $169 | Pressure sensors, up to 2200 Elo |
| **FEMUEY/VONSET** | Various | Chinese manufacturers entering market |
| **SenseRobot** | $999 | Full robotic, 25 levels |

**Market positioning gap:** No serious player targets the <$50 (₹4,000) tournament rental market.

### Market Size (India)

- **FIDE-rated tournaments:** 1,138 events (Nov 2024–Oct 2026) = ~570/year
- **Top states:** Tamil Nadu (233), Maharashtra (182), Karnataka (124), West Bengal (77), Odisha (53)
- **Registered players with AICF:** 96,585+ (as of 2020, likely higher now)
- **Boards per tournament:** Typically 20-100 boards for rated events; 111 boards was cited as a "national record" in 2018

**Estimated addressable market:** If 500 tournaments/year need 30 boards average = 15,000 board-days/year for FIDE events alone. Non-rated school/club tournaments likely 5-10x this volume.

---

## 2. Patent Status — CONFIRMED EXPIRED ✅

### DGT's Key Patent: US6168158B1

- **Title:** "Device for detecting playing pieces on a board"
- **Filed:** June 30, 1999
- **Granted:** January 2, 2001
- **Inventor:** Bernard Johan Bulsink
- **Assignee:** DGT Projects B.V. (later Digital Game Technology B.V.)
- **Status:** **Expired - Fee Related** (June 30, 2019 anticipated expiration, but actually lapsed earlier)

**Critical finding:** The patent status shows "Expired - Fee Related" — meaning DGT stopped paying maintenance fees. US patents require maintenance fees at 3.5, 7.5, and 11.5 years. Non-payment causes the patent to lapse.

### What the Patent Covered

The patent describes DGT's specific **resonance coil detection system**:
- Resonance coils in each playing piece with unique electrical/magnetic properties
- Transmit and receive coils in the board arranged in rows/columns
- Scanning amplifier system to detect piece type and position
- Compensation windings to handle edge effects

### Alternative Technologies NOT Covered by This Patent

1. **Reed switches + magnets** — Simple binary detection (piece present/absent)
2. **Hall effect sensors** — Magnetic field detection, can distinguish polarity
3. **Photoresistors** — Light-based detection (LiBoard approach)
4. **Pressure sensors** — Weight/contact detection
5. **RFID** — Different technology entirely

**Conclusion:** You can legally manufacture electronic chess boards using reed switches, Hall sensors, or other non-resonance-coil methods. Even the resonance coil method is now public domain.

---

## 3. Technical Feasibility

### How Electronic Chess Boards Work

**Method 1: Reed Switches (Simplest, Cheapest)**
- Magnet in each piece base
- Reed switch under each square
- Switch closes when magnet is near
- Binary output: occupied/empty
- Cannot identify piece type

**Method 2: Hall Effect Sensors**
- Magnet in each piece
- Hall sensor under each square
- Analog output proportional to magnetic field
- Can potentially distinguish piece types by magnet strength/polarity
- More complex but more capable

**Method 3: Resonance Coils (DGT's method)**
- Unique LC circuit in each piece
- Transmit/receive coils in board
- Identifies exact piece type
- Most complex, highest cost

**Method 4: RFID**
- RFID tag in each piece
- Reader coils in board
- Full piece identification
- Higher cost per piece

### Component Costs (Chinese Sourcing)

| Component | Qty | Unit Price (bulk) | Total |
|-----------|-----|-------------------|-------|
| ESP32-WROOM-32E | 1 | $2.00-2.50 | $2.25 |
| Reed switches (glass) | 64 | $0.08-0.12 | $6.40 |
| Neodymium magnets (10mm) | 32 | $0.10 | $3.20 |
| CD74HC4067 multiplexer | 4 | $0.30 | $1.20 |
| PCB (custom) | 1 | $3-5 | $4.00 |
| Passive components | lot | — | $1.00 |
| USB-C connector + cable | 1 | $0.50 | $0.50 |
| **Electronics subtotal** | | | **~$18.55** |
| MDF/plastic enclosure | 1 | $3-5 | $4.00 |
| Chess pieces (plastic, weighted) | 32 | $0.15 | $4.80 |
| Assembly labor | 1 | $2-3 | $2.50 |
| **Total BOM** | | | **~$30 (~₹2,500)** |

### Can ₹1,000 Be Achieved?

**At retail component prices:** No. ChessTrace's ₹1,850 BOM is already optimized.

**At scale (1,000+ units):**
- ESP32: $1.50 → ₹125
- Reed switches (64): $3.20 → ₹270
- Magnets (32): $1.60 → ₹135
- PCB: $2.00 → ₹170
- Enclosure: $2.00 → ₹170
- Pieces: $3.00 → ₹250
- Assembly: $1.00 → ₹85
- **Optimistic total: ~₹1,200**

**To hit ₹1,000:** Would require:
- Own PCB manufacturing or very high volume
- Simplified enclosure (vinyl mat instead of rigid board)
- Pieces sourced separately (tournament venues often have pieces)
- Board-only product (no pieces included)

**Realistic target:** ₹1,500-2,000 for a functional board with WiFi streaming capability.

### Open-Source Reference Designs

| Project | Technology | BOM | Status |
|---------|------------|-----|--------|
| **ChessTrace** | ESP32 + reed switches | ₹1,850 | Complete, documented |
| **LiBoard** | Pro Micro + photoresistors | €35 (~₹3,200) | Complete |
| **Chess Pro** | RPi Zero + Hall sensors | Not listed | Complete, GPL-3.0 |
| **eChess** | Arduino + Hall sensors | Not listed | Complete, AGPL-3.0 |
| **OpenChess** | Arduino Nano RP2040 + Hall | Not listed | Active development |

**ChessTrace** is the most relevant reference — it's specifically designed for low-cost tournament use with cloud recording.

---

## 4. Tournament Market in India

### Tournament Volume

| Period | FIDE-Rated Tournaments | Source |
|--------|------------------------|--------|
| 2019-20 | 409 | AICF Annual Report |
| 2021-22 | 70 | AICF Annual Report (COVID impact) |
| Nov 2024 - Oct 2026 | 1,138 | FIDE database |

**Current run rate:** ~570 FIDE-rated tournaments/year

### Geographic Distribution (Nov 2024 - Oct 2026)

| State | Tournaments | Host Cities |
|-------|-------------|-------------|
| Tamil Nadu | 233 | 35 |
| Maharashtra | 182 | 27 |
| Karnataka | 124 | 19 |
| West Bengal | 77 | 13 |
| Odisha | 53 | 13 |
| Assam | 47 | 13 |
| Madhya Pradesh | 43 | 18 |
| Delhi | 39 | 1 |
| Others | 340 | — |

**Key insight:** Top 5 states host 59% of tournaments. Tamil Nadu alone hosts 20%.

### Boards Per Tournament

- Small club events: 10-20 boards
- State-level: 30-50 boards
- National championships: 50-100 boards
- Major internationals: 100+ boards (111 was cited as record in 2018)

### Tournament Organizer Pain Points

1. **Cost of DGT boards** — ₹36,000+ per board is prohibitive for most organizers
2. **Limited rental availability** — One provider mentioned max 4 boards for independent rental
3. **Technical expertise required** — "DGT boards are very sensitive and do not tolerate errors"
4. **Setup time** — Large tournaments need day-before setup
5. **Internet reliability** — Live streaming requires stable connectivity
6. **Software complexity** — LiveChess setup, cloud configuration

### Key Stakeholders

**Federations:**
- **AICF** (All India Chess Federation) — National body, owns tournament boards
- **TNSCA** (Tamil Nadu State Chess Association) — Largest state, Chennai-based
- **MCA** (Maharashtra Chess Association) — Pune-based, active tournament scene

**Tournament Organizers:**
- **SHRIHM Sports** (Mumbai) — Full-service tournament management
- **Pinnacle Chess Events** (Thane) — FIDE-rated tournament specialists
- **Chennai Chess Products** — Equipment supplier, DGT distributor

**Contact Information:**
- TNSCA: tnchess64@gmail.com, 9940342937
- MCA: maharashtrachessassociation@gmail.com, 9673003780
- SHRIHM: shrihmsports@gmail.com, 9821005106

---

## 5. Business Model Analysis

### Model A: Rental (Recommended) ⭐

**Current market rates:**
- Basic chess sets: ₹500/day per set
- Chess clocks: ₹300/day
- 10 sets package: ₹2,000 including delivery
- Full tournament package (40 players): ₹18,000-24,000
- Corporate event (60 players): ₹35,000-48,000

**Proposed e-board rental pricing:**
- Per board/day: ₹500-800 (vs ₹36,000 purchase)
- 20-board tournament package: ₹8,000-12,000/day
- Includes: Setup, technical support, live streaming setup

**Unit economics (rental):**
- Board cost: ₹2,000
- Useful life: 100 rentals (2-3 years)
- Cost per rental: ₹20
- Revenue per rental: ₹500
- Gross margin: 96%

**Break-even:** 4 rentals per board

### Model B: Sales

**Target pricing:** ₹5,000-8,000 per board (vs DGT ₹36,000)

**Challenges:**
- Lower margin than rental
- Requires after-sales support
- Competes with Chinese imports
- Customers may not value "Made in India"

### Model C: Hybrid (Tournament-as-a-Service)

**Offering:**
- Boards + clocks + live streaming + technical support
- Per-tournament flat fee based on board count
- Software platform for game recording, PGN export, analysis

**Pricing:** ₹15,000-30,000 per tournament (20-50 boards)

### Revenue Projections (Conservative)

**Year 1:**
- 50 boards manufactured
- 200 rental-days
- Revenue: ₹1,00,000
- Costs: ₹1,50,000 (boards + development)
- Net: -₹50,000

**Year 2:**
- 200 boards
- 1,000 rental-days
- Revenue: ₹5,00,000
- Costs: ₹4,00,000
- Net: ₹1,00,000

**Year 3:**
- 500 boards
- 3,000 rental-days
- Revenue: ₹15,00,000
- Costs: ₹10,00,000
- Net: ₹5,00,000

### Competition and Barriers

**Direct competitors:**
- DGT (incumbent, premium positioning)
- Chinese manufacturers (Chessnut, FEMUEY entering market)
- Local rental providers (limited e-board inventory)

**Barriers to entry:**
1. **Software ecosystem** — LiveChess compatibility is expected by organizers
2. **Reliability requirements** — Tournament use demands 100% uptime
3. **AICF relationships** — Federation approval/endorsement matters
4. **Technical support** — Need trained operators in multiple cities

**Competitive advantages (potential):**
1. **Local presence** — Faster support, no import duties
2. **Lower cost** — Can undercut DGT significantly
3. **Customization** — Hindi interface, local payment integration
4. **Rental model** — Lower barrier for organizers

---

## 6. Risks and Challenges

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sensor reliability issues | Medium | High | Extensive testing, quality components |
| WiFi connectivity problems | Medium | Medium | Offline recording with sync |
| Software bugs during tournament | Medium | High | Thorough QA, fallback modes |
| Piece magnet alignment issues | Low | Medium | Standardized piece design |
| Battery life (if wireless) | Medium | Low | USB power option |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DGT price reduction | Medium | High | Focus on rental, not sales |
| Chinese competitors enter India | High | Medium | Service differentiation |
| Low tournament adoption | Medium | High | Pilot with friendly organizers |
| AICF doesn't endorse | Medium | Medium | Build grassroots reputation |

### Regulatory/Legal Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Unknown patents | Low | High | Patent search, design-around |
| BIS certification required | Medium | Medium | Research requirements early |
| Import restrictions on components | Low | Medium | Domestic sourcing alternatives |

### Supply Chain Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Component shortages | Medium | Medium | Buffer inventory |
| Quality issues from China | Medium | Medium | Supplier qualification, inspection |
| Shipping delays | Medium | Low | Local assembly, air freight option |
| Currency fluctuation | Medium | Low | Forward contracts, pricing buffer |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Damage during transport | Medium | Medium | Robust packaging, insurance |
| Theft/loss at tournaments | Low | Medium | Deposit system, tracking |
| Scaling support team | Medium | Medium | Train local partners |

---

## 7. Recommendations

### Go/No-Go Assessment

**Factors favoring GO:**
- ✅ Patent barrier removed
- ✅ Clear market need (cost is #1 pain point)
- ✅ Open-source reference designs available
- ✅ India is world's largest chess market by player count
- ✅ Rental model has strong unit economics

**Factors favoring CAUTION:**
- ⚠️ ₹1,000 target is unrealistic; ₹2,000 is achievable
- ⚠️ Software ecosystem (LiveChess compatibility) is critical
- ⚠️ Tournament reliability requirements are demanding
- ⚠️ Need relationships with AICF/state associations
- ⚠️ Chinese competitors may enter with lower costs

### Recommended Approach

1. **Start with rental model** — Lower risk, faster feedback
2. **Target ₹2,000 BOM** — Realistic with quality components
3. **Build software first** — LiveChess-compatible or Lichess Board API
4. **Pilot with 20 boards** — Partner with one friendly organizer
5. **Focus on Tamil Nadu/Maharashtra** — 36% of market
6. **Develop local support network** — Train operators in key cities

### Next Steps

1. **Technical validation** — Build one prototype using ChessTrace design
2. **Software development** — Create LiveChess-compatible streaming software
3. **Cost optimization** — Get quotes from Alibaba suppliers for 100-unit MOQ
4. **Market validation** — Interview 5 tournament organizers about pain points
5. **Pilot partnership** — Approach TNSCA or MCA for pilot tournament

---

## Sources

1. DGT Shop — https://www.dgtshop.com/products/chess-boards
2. Google Patents US6168158B1 — https://patents.google.com/patent/US6168158B1/en
3. ChessTrace GitHub — https://github.com/anujjainbatu/chess-trace
4. AICF Annual Reports — https://aicf.in/downloads/
5. LWSed FIDE Tournament Analysis — https://lwsed.com/research/where-india-plays-rated-chess/
6. Chennai Chess Products — https://www.chennaichessproducts.com/
7. Chess.com Tournament Broadcast Guide — https://www.chess.com/announcements/view/tournament-broadcast-guide-dgt-livechess-cloud
8. The Hindu (2018 IIFL tournament) — https://www.thehindu.com/news/cities/mumbai/e-boards-app-taking-chess-to-the-spectator/article22389164.ece
9. Alibaba/AliExpress component pricing — Various listings
10. Chessnut Buyer's Guide 2026 — https://www.chessnutech.com/pages/smart-chess-board-buyers-guide-2026

---

*Research conducted by [DGT Chess Board Business Research](0abda61d-a60e-4da8-a614-59238b4c14b5)*
