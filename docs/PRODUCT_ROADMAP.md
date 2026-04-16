# Restaurant POS Product Roadmap

## Purpose
This document captures the current product direction for the white-label offline restaurant POS so future work stays aligned even if chat context is lost.

It covers:
- current MVP status
- what is already implemented
- what still needs polish
- the next major product phases
- planned future upgrades

## Product Summary
The product is a Windows-first offline restaurant POS desktop application built with:
- Python
- PySide6
- SQLite
- SQLAlchemy
- bcrypt
- cryptography

Current product direction:
- desktop-first UI
- mouse and keyboard focused
- touch-tolerant, but not touch-first
- offline-first
- license-gated
- white-label ready

## Current Phase
The project is currently in:

`Phase 4: MVP Stabilization and Product Polish`

Meaning:
- the main MVP workflows exist
- the system is usable
- current work is focused on bug fixing, UI/UX cleanup, consistency, and production hardening

## Current MVP Coverage

### Implemented Core Areas
- offline local desktop architecture
- layered project structure
- license-gated app startup
- license generator script
- first-time setup wizard
- admin and staff login roles
- white-label restaurant settings
- category and menu item management
- user management
- dine-in table POS workflow
- order creation and billing
- cash and UPI payment flow
- receipt preview, printing, and PDF export
- order reporting and CSV export
- database backup and restore
- test suite and iterative bug-fix coverage

### Current Quality Level
- logic layer: strong MVP
- UI/UX layer: improving, but still not fully production-polished
- release packaging: not fully hardened yet
- licensing: functional, but still needs stronger release discipline

## Important Current Product Decisions

### POS UI Direction
The POS terminal should follow:
- desktop-first layout
- efficient mouse and keyboard use
- moderate density
- modern business/product look
- not oversized like a tablet-only POS

This means:
- clean panel hierarchy
- balanced spacing
- strong keyboard flow
- compact but readable controls
- modern styling without excessive touch sizing

### Receipt Direction
Receipt content should be based on admin settings and keep a thermal-slip style layout.

Current intended receipt structure:
- logo
- restaurant name
- address
- phone
- divider
- order number
- table
- cashier
- date/time
- divider
- items
- divider
- subtotal
- discount
- service
- GST
- total
- divider
- footer note
- powered by line from code

### Admin Navigation
Admins should be able to move between:
- Admin Dashboard
- POS Terminal

without being forced to log out.

### Keyboard Behavior
Keyboard behavior should feel desktop-natural:
- Enter should trigger focused/primary button actions where appropriate
- Tab should move through forms correctly
- multiline admin text fields should not trap Tab for indentation
- POS should continue using visible shortcut hints like `Cancel [F3]` and `Payment [F4]`

## Remaining MVP Polish Tasks

### POS Terminal Polish
- improve visual hierarchy of tables, menu, and ticket sections
- modernize panel styling
- improve spacing, alignment, and contrast
- make category and menu area more visually refined
- further improve desktop keyboard workflow
- make order/totals area feel more premium and consistent

### Admin UI Polish
- improve consistency across tabs
- refine create/update/save states
- reduce raw form-like appearance
- improve data-table clarity and visual rhythm

### Receipt and Printing Hardening
- improve print-cancel handling
- verify thermal printer behavior on real hardware
- keep logo sizing consistent
- keep preview, PDF, and print outputs aligned

### Production Hardening
- package validation on clean Windows environment
- PyInstaller/distribution hardening
- final asset and runtime path review
- release-only license behavior review
- stronger release documentation

## Next Major Product Expansion
The next major expansion should move the product from a dine-in MVP to a more complete restaurant operations system.

### New Order Types To Add
- Dine-In
- Takeaway
- Delivery

## Phase 5: Multi-Order-Type POS Expansion

### Goal
Expand the current dine-in workflow so the POS supports:
- dine-in
- takeaway
- delivery

### Required Changes

#### POS Flow
Current POS flow is mainly:
- select table
- open order
- add items

New POS flow should become:
- select order type first
- then follow the correct workflow

#### Dine-In
- table required
- current dine-in workflow continues

#### Takeaway
- no table required
- token/order number should be available
- customer name optional
- customer phone optional

#### Delivery
- no table required
- customer name required
- phone required
- address required
- delivery charge may be added later

#### Likely Data Changes
The `orders` model will likely need new fields such as:
- `order_type`
- `customer_name`
- `customer_phone`
- `delivery_address`
- `token_number`
- `kitchen_note`
- `kot_status`

Possible additional structure:
- improved order status tracking
- delivery-specific fields
- optional separate kitchen ticket model later

## Phase 6: Kitchen Display / KOT

### Goal
Add kitchen workflow support so orders are visible in kitchen operations.

### Kitchen Screen Requirements
- display incoming open kitchen orders
- show order type
- show table number for dine-in
- show token number for takeaway
- show customer/delivery info for delivery
- show item list
- show special notes
- show age/time since order placed

### Suggested Kitchen Statuses
- Pending
- Preparing
- Ready

Possible later extensions:
- Served
- Dispatched

### Kitchen Workflow Value
This turns the product into:
- front counter POS
- order management system
- kitchen workflow system

instead of only a billing application

## Phase 7: KOT Printing and Delivery Flow Expansion

### KOT Printing
Potential addition:
- print kitchen order tickets separately from customer receipts

### Delivery Enhancements
Potential later additions:
- delivery charge
- rider assignment
- dispatch tracking
- delivered status

## UI/UX Direction for Future Versions

### Overall Style Direction
The application should move toward:
- modern restaurant POS look
- product-style interface
- cleaner color system
- stronger visual grouping
- better typography
- clearer statuses and focus states

### Desktop UX Priorities
- efficient for mouse and keyboard
- low-friction repeated actions
- visible shortcut hints
- stable layouts at different screen sizes

### Shared UI System Needed
To reduce inconsistent UI fixes, the project should gradually adopt shared styling patterns for:
- buttons
- forms
- tables
- cards/sections
- spacing
- focus states
- keyboard behavior

## Future Updates and Suggested Improvements

### High-Priority Future Updates
- full POS visual redesign
- admin visual consistency pass
- packaging and installer hardening
- production-grade print workflow QA
- release licensing hardening
- dine-in/takeaway/delivery support
- kitchen display system

### Medium-Priority Future Updates
- improved table state visuals
- quick order search and recall
- better report filters and summaries
- more advanced receipt customization
- audit trail for important admin changes
- stronger backup management UX

### Long-Term Future Updates
- multi-terminal sync architecture
- cloud sync or hybrid mode
- inventory management
- customer database / CRM
- loyalty and promotions
- waiter-wise performance tracking
- advanced kitchen routing
- multi-printer configuration
- branch / multi-location support

## Recommended Build Order From Here

### Track A: Product Polish
1. POS UI/UX redesign
2. Admin panel consistency cleanup
3. receipt/printing hardening
4. packaging and release hardening

### Track B: Product Expansion
1. add order type system
2. implement takeaway flow
3. implement delivery flow
4. add kitchen display / KOT
5. add kitchen ticket printing

## Working Definition of Release Readiness
The product should only be called commercially release-ready when:
- main workflows are stable
- UI/UX is consistent and professional
- build/distribution flow is validated
- license flow is hardened for real deployment
- real printer testing is done
- backup/restore is validated on actual user setups

## Note for Future Sessions
If future work loses context, treat this document as the current product reference.

The current direction is:
- stabilize and polish the existing MVP
- then expand from dine-in-only to dine-in + takeaway + delivery + kitchen workflow

## Order Number Strategy For Production

### Goal
Replace the current long timestamp-style visible order number with a simpler daily running order number.

### Decision
The system should use:
- an internal date-bound order sequence
- a simple visible daily order number for staff and receipts

### Production Rule
Visible order number should show only the daily running number, for example:
- `001`
- `002`
- `003`

The date should not be shown in the printed/displayed order number.

### Internal Logic
The order number should still be bound to the business date internally.

Recommended internal structure:
- `business_date`
- `daily_order_number`

Meaning:
- the visible order number resets each day
- internal uniqueness comes from the combination of date + daily sequence

Example:
- 2026-04-16 + 001
- 2026-04-16 + 002
- 2026-04-16 + 003
- 2026-04-17 + 001

### Display Rules
Use only the short daily number in:
- POS ticket display
- printed receipt
- receipt preview
- admin order listing
- kitchen/KOT display in future phases

### Search and Lookup Rules
Because the visible order number repeats daily, admin lookup should use:
- order number
- date filter / calendar filter

This means staff can search a particular order by:
- daily order number
- selected date

### Why This Is The Preferred Production Approach
- cleaner POS UI
- shorter receipt number
- easier for staff to read and call out
- suitable for dine-in, takeaway, delivery, and KOT workflows
- keeps the internal system reliable without exposing long technical IDs

### Implementation Note For Future Build Phase
When implemented, the current long mixed datetime order number should be replaced in user-facing areas by the daily visible number only.

The old long-format identifier should not remain the main visible order number in production.
