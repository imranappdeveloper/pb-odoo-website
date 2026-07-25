# Domain Context & Glossary

### Shipping Carrier
A shipping company or line operator (e.g. Keihin, Hoegh, Armacup) that operates vessels and publishes port schedules. Managed as a pure standalone entity (`shipping.carrier`) for shipping schedule tracking without coupling to accounting or contact records.

### Vessel
A cargo or RoRo ship (`shipping.vessel`) belonging to a carrier. Stores physical constraints such as maximum deck height (cm) and maximum cargo weight (K/T).

### Port
A sea port location (`shipping.port`) classified by code (e.g., UN/LOCODE `JPYOK`), country, and standard role (Port of Loading - POL vs Port of Discharge - POD).

### Shipping Schedule
A published voyage schedule header (`shipping.schedule`) tying a Carrier, Vessel, Voyage Number, Revision Date, and Trade Lane together with cargo restrictions (e.g. EV prohibitions, certificate requirements).

### Schedule Line
A specific port call entry (`shipping.schedule.line`) on a Shipping Schedule. Contains call sequence, call type (`pol` or `pod`), target port, arrival/departure dates (`eta`, `etd`, with end-date range support like `eta_end`), and operational status (`scheduled`, `completed`, `skipped`, `delayed`).
