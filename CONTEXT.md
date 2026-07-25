# Domain Context & Glossary

### Shipping Carrier
A shipping company or line operator (e.g. Keihin, Hoegh, Armacup) that operates vessels and publishes port schedules. Managed as a pure standalone entity (`shipping.carrier`) for shipping schedule tracking without coupling to accounting or contact records.

### Vessel
A cargo or RoRo ship (`shipping.vessel`) belonging to a carrier. Stores physical constraints such as maximum deck height (cm) and maximum cargo weight (K/T).

### Port
A sea port location (`shipping.port`) classified by code (e.g., UN/LOCODE `JPYOK`), country, and standard role (Port of Loading - POL vs Port of Discharge - POD).

### Shipping Schedule
A published voyage schedule header (`shipping.schedule`) tying a Carrier, Vessel, Voyage Number, Revision Date, and **Trade Lane** together with cargo restrictions (e.g. EV prohibitions, certificate requirements). One schedule record is created **per region/trade lane** — the same vessel voyage may produce multiple schedule records (e.g. East Africa, Sri Lanka, South America). Uniqueness is enforced on `(carrier, vessel, voyage_no, trade_lane)`.

### Trade Lane
The geographic route label that distinguishes region blocks within a carrier's Excel schedule (e.g. `East Africa / West Africa / Mozambique / UAE`, `Sri Lanka`, `South America`). Acts as the discriminator when one voyage sheet covers multiple regions. This is the **primary grouping key** for users browsing schedules by destination region.

### Region Block
A self-contained section within a carrier Excel sheet representing one trade lane. Each region block has its own column range (e.g. East Africa at col 1–3, Sri Lanka at col 14–16) or row range (South America at rows 30+). A single import creates one `Shipping Schedule` per region block found in the file.

### Schedule Line
A specific port call entry (`shipping.schedule.line`) on a Shipping Schedule. Contains call sequence, call type (`pol` or `pod`), target port, arrival/departure dates (`eta`, `etd`, with end-date range support like `eta_end`), and operational status (`scheduled`, `completed`, `skipped`, `delayed`). Port lines may have null dates if the carrier has not published dates for that region yet — status remains `scheduled` with dates TBC.

