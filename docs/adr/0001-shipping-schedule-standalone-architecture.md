# 1. Standalone Shipping Schedule Models Architecture

* **Status**: Accepted
* **Date**: 2026-07-25

## Context and Problem Statement
Pacific Boeki imports vehicle shipping schedules (e.g., Keihin RoRo schedules) to track vessel voyages, port laydays, arrival windows in East Africa, and cargo height/weight/EV restrictions. We need to decide how to represent Carriers, Vessels, Ports, and Voyage Schedules in Odoo.

## Decision Drivers
* Clean separation of concern: shipping schedule management vs core financial/contact accounting.
* Support for port call date ranges (e.g., DAR ES SALAAM Aug 19–22).
* API performance for frontend website schedule search endpoints.
* Ease of parsing and importing carrier Excel sheets.

## Considered Options
1. **Inherit `res.partner` for Carriers & `product.template` for Vessels**
2. **Standalone Domain Models (`shipping.carrier`, `shipping.vessel`, `shipping.port`, `shipping.schedule`, `shipping.schedule.line`)**

## Decision Outcome
Chosen Option: **Option 2 (Standalone Domain Models)**.

### Positive Consequences
* Completely decouples shipping schedule data from customer/vendor contacts (`res.partner`).
* Fast, lightweight database queries for website schedule APIs.
* Full flexibility for shipping-specific fields (deck height limits, weight limits, EV restrictions, POL/POD date ranges).

### Negative Consequences
* Standalone carrier records cannot directly be selected in purchase/sales orders without explicit Many2one bridges if needed in the future.
