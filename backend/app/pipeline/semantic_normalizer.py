"""
Stage 3.5: Semantic Field Normalization & Alias Resolution.

Sits between EntityExtractor and TripletMatcher.
Resolves vendor-specific field label variants to canonical entity keys,
normalizes values (units, dates, vendor name aliases), and rescans OCR
text for fields that the regex-based EntityExtractor may have missed.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Canonical field alias vocabulary
# ---------------------------------------------------------------------------
# Maps every known field label variant (lower-cased) to the canonical key
# used throughout the rest of the pipeline.
FIELD_ALIASES: Dict[str, List[str]] = {
    "shipment_id": [
        "shipment id", "shipment no", "shipment number", "shipment ref",
        "lr no", "lr number", "lr#", "lorry receipt no", "lorry receipt number",
        "consignment no", "consignment number", "cn no", "cn number",
        "docket no", "docket number", "awb no", "airway bill no",
        "invoice no", "invoice number", "inv no", "bill no",
        "pod no", "pod number", "delivery order no",
        "reference no", "ref no", "booking no", "booking id",
        "gr no", "gr number",
    ],
    "amount": [
        "total amount", "net amount", "grand total", "amount",
        "basic freight", "freight amount", "freight charges",
        "invoice amount", "taxable amount", "payable amount",
        "total payable", "amount due", "bill amount",
        "total value", "total freight", "charges",
        "amount acknowledged", "met amount",
    ],
    "date": [
        "date", "invoice date", "bill date", "booking date",
        "shipment date", "dispatch date", "issue date",
        "lr date", "pod date", "delivery date", "dated",
    ],
    "party_name": [
        "consignee", "receiver", "ship to", "delivered to", "recipient",
        "deliver to", "deliver at", "bill to", "billed to",
        "consignor", "shipper", "sender", "from", "booked by",
        "party", "client", "customer",
    ],
    "origin": [
        "origin", "from", "pickup", "pickup location", "source",
        "loading point", "dispatch from", "place of loading",
        "collected from",
    ],
    "destination": [
        "destination", "to", "delivery", "delivery location",
        "drop point", "place of delivery", "unloading point",
        "deliver to",
    ],
    "vehicle_number": [
        "vehicle no", "vehicle number", "truck no", "truck number",
        "lorry no", "lorry number", "transport no",
        "registration no", "reg no",
    ],
    "weight": [
        "weight", "gross weight", "net weight", "wt", "total weight",
        "chargeable weight", "actual weight",
    ],
}

# Flat lookup: alias_label → canonical_key (built once at import time)
_ALIAS_LOOKUP: Dict[str, str] = {}
for _canonical, _variants in FIELD_ALIASES.items():
    for _variant in _variants:
        _ALIAS_LOOKUP[_variant] = _canonical

# ---------------------------------------------------------------------------
# Unit normalisation tables
# ---------------------------------------------------------------------------
# All weights are converted to kilograms internally.
WEIGHT_UNIT_TO_KG: Dict[str, float] = {
    "kg": 1.0,
    "kgs": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "mt": 1000.0,
    "mts": 1000.0,
    "metric ton": 1000.0,
    "metric tons": 1000.0,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "ton": 1000.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "lb": 0.453592,
    "lbs": 0.453592,
    "pound": 0.453592,
    "pounds": 0.453592,
    "quintal": 100.0,
    "quintals": 100.0,
    "q": 100.0,
}

# Pattern to match a weight value with its unit
_WEIGHT_PATTERN = re.compile(
    r"([0-9,]+(?:\.[0-9]+)?)\s*"
    r"(mt|mts|metric\s*ton[s]?|tonne[s]?|ton[s]?|kg[s]?|kilogram[s]?|g|gram[s]?|lb[s]?|pound[s]?|quintal[s]?|q)\b",
    re.IGNORECASE,
)

# Pattern to capture a key:value pair from raw OCR lines
_KV_PATTERN = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z\s/()#&.-]{1,40}?)\s*[:\-]\s*(?P<value>.+)",
)


class SemanticFieldNormalizer:
    """
    Stage 3.5 of the pipeline.

    Responsibilities:
    1. Value normalization — standardise weights with unit conversion,
       clean amount strings, re-validate date formats.
    2. Alias re-scan — parse OCR text line by line for key:value pairs
       whose labels were not matched by the regex EntityExtractor, resolve
       those labels via the alias vocabulary (exact + fuzzy), and back-fill
       any missing canonical entity fields.
    3. Vendor/party name alias resolution — when the same vendor appears
       under slightly different names across documents, normalise to the
       dominant form using fuzzy similarity.
    """

    # Minimum label similarity score to accept a fuzzy alias match
    FUZZY_THRESHOLD: float = 0.72

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def normalize(
        self,
        entities: Dict,
        ocr_text: str,
        doc_type: str = "",
    ) -> Tuple[Dict, Dict]:
        """
        Normalise extracted entities and attempt to recover missing fields.

        Returns:
            normalized_entities : updated entity dict (same keys as input,
                                   possibly with extra back-filled keys)
            normalization_log   : human-readable log of every change made,
                                   useful for the audit trail.
        """
        log: Dict[str, str] = {}

        # Work on a copy so the caller's dict is not mutated in-place
        result = dict(entities)

        # Step 1 — Normalise values that are already present
        result, log = self._normalize_existing_values(result, log)

        # Step 2 — Back-fill missing fields from OCR text
        result, log = self._backfill_from_ocr(result, ocr_text, log)

        # Step 3 — Vendor/party name deduplication within the document
        result, log = self._resolve_party_aliases(result, log)

        return result, log

    # ---------------------------------------------------------------------------
    # Step 1 — Value normalisation
    # ---------------------------------------------------------------------------

    def _normalize_existing_values(
        self, entities: Dict, log: Dict
    ) -> Tuple[Dict, Dict]:
        result = dict(entities)

        # --- Amount ---
        if "amount" in result and result["amount"] is not None:
            cleaned = self._clean_amount(str(result["amount"]))
            if cleaned != result["amount"]:
                log["amount_normalized"] = (
                    f"Amount '{result['amount']}' → {cleaned}"
                )
                result["amount"] = cleaned

        # --- Weight with unit conversion ---
        if "weight" in result and result["weight"] is not None:
            normalized_weight, unit = self._normalize_weight(str(result["weight"]))
            if normalized_weight is not None:
                if normalized_weight != result["weight"]:
                    log["weight_normalized"] = (
                        f"Weight '{result['weight']}' → {normalized_weight} kg (from {unit})"
                    )
                result["weight"] = normalized_weight
                result["weight_unit"] = "kg"

        # --- Dates: ensure ISO 8601 ---
        for date_field in ("date", "booking_date", "delivery_date"):
            if date_field in result and result[date_field]:
                iso = self._to_iso_date(str(result[date_field]))
                if iso and iso != result[date_field]:
                    log[f"{date_field}_normalized"] = (
                        f"Date '{result[date_field]}' → '{iso}'"
                    )
                    result[date_field] = iso

        # --- Strip whitespace from string fields ---
        for key, val in result.items():
            if isinstance(val, str):
                stripped = val.strip()
                if stripped != val:
                    result[key] = stripped

        return result, log

    # ---------------------------------------------------------------------------
    # Step 2 — Back-fill missing fields from OCR text
    # ---------------------------------------------------------------------------

    def _backfill_from_ocr(
        self, entities: Dict, ocr_text: str, log: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Parse OCR text line-by-line looking for key:value patterns.
        For each pair, if the label resolves to a canonical field that is
        still missing in entities, back-fill it.
        """
        result = dict(entities)
        lines = re.split(r"[\n|]", ocr_text)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = _KV_PATTERN.match(line)
            if not match:
                continue

            raw_label = match.group("label").strip()
            raw_value = match.group("value").strip()

            if not raw_label or not raw_value:
                continue

            canonical = self._resolve_label(raw_label)
            if canonical is None:
                continue

            # Only back-fill if the field is missing or empty
            existing = result.get(canonical)
            if existing is not None and str(existing).strip():
                continue

            # Normalise the raw value before storing
            normalised_value = self._coerce_value(canonical, raw_value)
            if normalised_value:
                result[canonical] = normalised_value
                log[f"backfilled_{canonical}"] = (
                    f"Label '{raw_label}' → canonical '{canonical}', "
                    f"value '{raw_value}'"
                    + (f" → '{normalised_value}'" if normalised_value != raw_value else "")
                )

        return result, log

    # ---------------------------------------------------------------------------
    # Step 3 — Vendor/party alias resolution
    # ---------------------------------------------------------------------------

    def _resolve_party_aliases(
        self, entities: Dict, log: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Identify all party-name fields and normalise near-duplicates to the
        longer / higher-quality form using fuzzy similarity.
        """
        party_fields = [
            k for k in entities
            if any(marker in k for marker in ("name", "party", "consignee", "consignor", "receiver"))
            and isinstance(entities.get(k), str)
        ]

        if len(party_fields) < 2:
            return entities, log

        result = dict(entities)
        canonical_names: List[str] = []

        for field in party_fields:
            name = result[field].strip()
            matched = self._find_canonical_name(name, canonical_names)
            if matched:
                if name != matched:
                    log[f"alias_resolved_{field}"] = (
                        f"'{name}' recognised as alias of '{matched}'"
                    )
                    result[field] = matched
            else:
                canonical_names.append(name)

        return result, log

    # ---------------------------------------------------------------------------
    # Label resolution helpers
    # ---------------------------------------------------------------------------

    def _resolve_label(self, raw_label: str) -> Optional[str]:
        """
        Resolve a raw OCR field label to a canonical entity key.

        1. Exact lookup in alias table
        2. Fuzzy similarity against alias table keys
        """
        clean = raw_label.lower().strip().rstrip(".:# ")

        # 1. Exact match
        if clean in _ALIAS_LOOKUP:
            return _ALIAS_LOOKUP[clean]

        # 2. Fuzzy match
        best_score = 0.0
        best_canonical = None
        for alias_label, canonical in _ALIAS_LOOKUP.items():
            score = SequenceMatcher(None, clean, alias_label).ratio()
            if score > best_score:
                best_score = score
                best_canonical = canonical

        if best_score >= self.FUZZY_THRESHOLD:
            return best_canonical

        return None

    # ---------------------------------------------------------------------------
    # Value coercion helpers
    # ---------------------------------------------------------------------------

    def _coerce_value(self, canonical: str, raw_value: str) -> Optional[str]:
        """Coerce a raw value string to the normalised form for a canonical field."""
        if canonical == "amount":
            cleaned = self._clean_amount(raw_value)
            return str(cleaned) if cleaned is not None else None

        if canonical == "weight":
            normalised, _ = self._normalize_weight(raw_value)
            return str(normalised) if normalised is not None else raw_value

        if canonical == "date":
            return self._to_iso_date(raw_value) or raw_value

        # Generic: take up to 80 characters, strip junk
        value = re.sub(r"[^\w\s&.,/-]", "", raw_value).strip()
        return value[:80] if value else None

    def _clean_amount(self, raw: str) -> Optional[float]:
        """Strip currency symbols / commas and return a float."""
        clean = re.sub(r"[₹$€£¥,\s]", "", raw)
        clean = re.sub(r"[^\d.]", "", clean)
        try:
            return float(clean)
        except ValueError:
            return None

    def _normalize_weight(self, raw: str) -> Tuple[Optional[float], str]:
        """
        Parse a weight string like '15 MT' or '1500 kg' and return
        the value converted to kilograms plus the detected source unit.
        """
        match = _WEIGHT_PATTERN.search(raw)
        if not match:
            # Try to parse a bare number; assume kg
            bare = re.sub(r"[^\d.]", "", raw)
            try:
                return float(bare), "kg"
            except ValueError:
                return None, ""

        value_str = match.group(1).replace(",", "")
        unit_str = re.sub(r"\s+", " ", match.group(2).lower().strip())
        multiplier = WEIGHT_UNIT_TO_KG.get(unit_str, 1.0)
        try:
            return float(value_str) * multiplier, unit_str
        except ValueError:
            return None, ""

    def _to_iso_date(self, raw: str) -> Optional[str]:
        """Convert common date formats to ISO 8601 (YYYY-MM-DD)."""
        from datetime import datetime

        formats = [
            "%Y-%m-%d",  # already ISO — fast-path
            "%d-%m-%Y", "%d/%m/%Y",
            "%d-%m-%y", "%d/%m/%y",
            "%d %b %Y", "%d %B %Y",
            "%d %b %y", "%d %B %y",
            "%m/%d/%Y", "%m-%d-%Y",
            "%Y/%m/%d",
        ]
        clean = raw.strip()
        for fmt in formats:
            try:
                return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    # ---------------------------------------------------------------------------
    # Party name fuzzy deduplication helper
    # ---------------------------------------------------------------------------

    def _find_canonical_name(
        self, name: str, known_names: List[str]
    ) -> Optional[str]:
        """
        Return the known canonical name that is similar to *name* (if any),
        preferring the longer form as the canonical.
        """
        name_lc = name.lower()
        for known in known_names:
            score = SequenceMatcher(None, name_lc, known.lower()).ratio()
            if score >= self.FUZZY_THRESHOLD:
                # Return the longer string as the canonical form
                return known if len(known) >= len(name) else name
        return None
