from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.config import get_settings

settings = get_settings()

@dataclass
class ValidationResult:
    rule: str
    passed: bool
    expected: str
    actual: str
    message: str

class Validator:
    """Stage 5: Rule-based validation for triplet matches"""
    
    def __init__(self, amount_tolerance: float = 0.02, name_similarity_threshold: float = 0.85):
        self.amount_tolerance = amount_tolerance
        self.name_similarity_threshold = name_similarity_threshold
    
    def validate_triplet(
        self, 
        lr_entities: Dict, 
        pod_entities: Dict, 
        invoice_entities: Dict,
        contract_rate: Dict | None = None,
    ) -> Tuple[List[ValidationResult], float]:
        """
        Run all validation rules on a triplet.
        Returns: (validation_results, pass_score)
        """
        results = []
        
        # Rule 1: Shipment ID must match exactly
        results.append(self._validate_shipment_id(lr_entities, pod_entities, invoice_entities))
        
        # Rule 2: Amount within tolerance
        results.append(self._validate_amount(lr_entities, invoice_entities))
        
        # Rule 3: Date sequence (LR <= POD <= Invoice)
        results.append(self._validate_date_sequence(lr_entities, pod_entities, invoice_entities))
        
        # Rule 4: Party name consistency
        results.append(self._validate_party_names(lr_entities, pod_entities, invoice_entities))
        
        # Rule 5: Route consistency
        results.append(self._validate_route(lr_entities, pod_entities))

        # Rule 6: Partial/split delivery consistency
        results.append(self._validate_weight_consistency(lr_entities, pod_entities, invoice_entities))

        # Rule 7: Contract/rate mismatch check
        results.append(self._validate_contract_rate(invoice_entities, contract_rate))
        
        # Calculate pass score
        passed = sum(1 for r in results if r.passed)
        pass_score = passed / len(results)
        
        return results, pass_score
    
    def _validate_shipment_id(self, lr: Dict, pod: Dict, inv: Dict) -> ValidationResult:
        """Validate shipment ID exact match."""
        lr_id = lr.get('shipment_id', '').strip().upper()
        pod_id = pod.get('shipment_id', '').strip().upper()
        inv_id = inv.get('shipment_id', '').strip().upper()
        
        ids = [i for i in [lr_id, pod_id, inv_id] if i]
        
        if len(ids) < 2:
            return ValidationResult(
                rule="SHIPMENT_ID_MATCH",
                passed=False,
                expected="All documents should have shipment ID",
                actual=f"Found IDs: LR={lr_id}, POD={pod_id}, INV={inv_id}",
                message="Missing shipment ID in one or more documents"
            )
        
        if len(set(ids)) == 1:
            return ValidationResult(
                rule="SHIPMENT_ID_MATCH",
                passed=True,
                expected=ids[0],
                actual=ids[0],
                message="Shipment ID matches across all documents"
            )
        else:
            return ValidationResult(
                rule="SHIPMENT_ID_MATCH",
                passed=False,
                expected="All IDs should match",
                actual=f"LR={lr_id}, POD={pod_id}, INV={inv_id}",
                message="Shipment ID mismatch detected"
            )
    
    def _validate_amount(self, lr: Dict, inv: Dict) -> ValidationResult:
        """Validate invoice amount within tolerance of LR amount."""
        lr_amount = lr.get('amount', 0)
        inv_amount = inv.get('amount', 0)
        
        try:
            lr_amt = float(lr_amount) if lr_amount else 0
            inv_amt = float(inv_amount) if inv_amount else 0
        except:
            return ValidationResult(
                rule="AMOUNT_TOLERANCE",
                passed=False,
                expected="Valid numeric amounts",
                actual=f"LR={lr_amount}, Invoice={inv_amount}",
                message="Could not parse amount values"
            )
        
        if lr_amt == 0 and inv_amt == 0:
            return ValidationResult(
                rule="AMOUNT_TOLERANCE",
                passed=True,
                expected="0",
                actual="0",
                message="Both amounts are zero"
            )
        
        if lr_amt == 0:
            return ValidationResult(
                rule="AMOUNT_TOLERANCE",
                passed=False,
                expected="LR amount > 0",
                actual=f"LR={lr_amt}",
                message="LR amount is missing or zero"
            )
        
        variance = abs(inv_amt - lr_amt) / lr_amt
        
        if variance <= self.amount_tolerance:
            return ValidationResult(
                rule="AMOUNT_TOLERANCE",
                passed=True,
                expected=f"Variance <= {self.amount_tolerance * 100}%",
                actual=f"Variance = {variance * 100:.2f}%",
                message=f"Amount variance ({variance * 100:.2f}%) within tolerance"
            )
        else:
            return ValidationResult(
                rule="AMOUNT_TOLERANCE",
                passed=False,
                expected=f"Variance <= {self.amount_tolerance * 100}%",
                actual=f"LR={lr_amt}, Invoice={inv_amt}, Variance={variance * 100:.2f}%",
                message=f"Amount variance ({variance * 100:.2f}%) exceeds tolerance"
            )
    
    def _validate_date_sequence(self, lr: Dict, pod: Dict, inv: Dict) -> ValidationResult:
        """Validate date sequence: LR <= POD <= Invoice."""
        lr_date = lr.get('date')
        pod_date = pod.get('date')
        inv_date = inv.get('date')
        
        def parse_date(d):
            if not d:
                return None
            try:
                return datetime.strptime(d, '%Y-%m-%d')
            except:
                return None
        
        lr_dt = parse_date(lr_date)
        pod_dt = parse_date(pod_date)
        inv_dt = parse_date(inv_date)
        
        dates = [(lr_dt, 'LR'), (pod_dt, 'POD'), (inv_dt, 'Invoice')]
        valid_dates = [(d, n) for d, n in dates if d]
        
        if len(valid_dates) < 2:
            return ValidationResult(
                rule="DATE_SEQUENCE",
                passed=True,  # Can't validate without dates
                expected="LR_date <= POD_date <= Invoice_date",
                actual=f"Only {len(valid_dates)} valid date(s) found",
                message="Insufficient dates for sequence validation"
            )
        
        # Check sequence
        violations = []
        if lr_dt and pod_dt and lr_dt > pod_dt:
            violations.append("LR date > POD date")
        if pod_dt and inv_dt and pod_dt > inv_dt:
            violations.append("POD date > Invoice date")
        if lr_dt and inv_dt and lr_dt > inv_dt:
            violations.append("LR date > Invoice date")
        
        if not violations:
            return ValidationResult(
                rule="DATE_SEQUENCE",
                passed=True,
                expected="LR_date <= POD_date <= Invoice_date",
                actual=f"LR={lr_date}, POD={pod_date}, Invoice={inv_date}",
                message="Date sequence is valid"
            )
        else:
            return ValidationResult(
                rule="DATE_SEQUENCE",
                passed=False,
                expected="LR_date <= POD_date <= Invoice_date",
                actual="; ".join(violations),
                message=f"Date sequence violation: {', '.join(violations)}"
            )
    
    def _validate_party_names(self, lr: Dict, pod: Dict, inv: Dict) -> ValidationResult:
        """Validate party name consistency."""
        from difflib import SequenceMatcher
        
        lr_party = lr.get('party_name', '').lower().strip()
        pod_party = pod.get('party_name', '').lower().strip()
        inv_party = inv.get('party_name', '').lower().strip()
        
        parties = [p for p in [lr_party, pod_party, inv_party] if p]
        
        if len(parties) < 2:
            return ValidationResult(
                rule="PARTY_NAME_MATCH",
                passed=True,
                expected="Party names should be similar",
                actual="Insufficient party names to compare",
                message="Could not validate party names"
            )
        
        min_similarity = 1.0
        for i in range(len(parties)):
            for j in range(i + 1, len(parties)):
                sim = SequenceMatcher(None, parties[i], parties[j]).ratio()
                min_similarity = min(min_similarity, sim)
        
        if min_similarity >= self.name_similarity_threshold:
            return ValidationResult(
                rule="PARTY_NAME_MATCH",
                passed=True,
                expected=f"Similarity >= {self.name_similarity_threshold * 100}%",
                actual=f"Min similarity = {min_similarity * 100:.1f}%",
                message="Party names are consistent"
            )
        else:
            return ValidationResult(
                rule="PARTY_NAME_MATCH",
                passed=False,
                expected=f"Similarity >= {self.name_similarity_threshold * 100}%",
                actual=f"LR={lr_party}, POD={pod_party}, Invoice={inv_party}",
                message=f"Party name similarity ({min_similarity * 100:.1f}%) below threshold"
            )
    
    def _validate_route(self, lr: Dict, pod: Dict) -> ValidationResult:
        """Validate route consistency between LR and POD."""
        lr_origin = lr.get('origin', '').lower().strip()
        lr_dest = lr.get('destination', '').lower().strip()
        pod_origin = pod.get('origin', '').lower().strip()
        pod_dest = pod.get('destination', '').lower().strip()
        
        if not (lr_origin or lr_dest or pod_origin or pod_dest):
            return ValidationResult(
                rule="ROUTE_CONSISTENCY",
                passed=True,
                expected="Route should match",
                actual="No route information available",
                message="Could not validate route"
            )
        
        origin_match = not (lr_origin and pod_origin) or lr_origin == pod_origin
        dest_match = not (lr_dest and pod_dest) or lr_dest == pod_dest
        
        if origin_match and dest_match:
            return ValidationResult(
                rule="ROUTE_CONSISTENCY",
                passed=True,
                expected="LR route = POD route",
                actual=f"{lr_origin}->{lr_dest}",
                message="Route is consistent"
            )
        else:
            return ValidationResult(
                rule="ROUTE_CONSISTENCY",
                passed=False,
                expected=f"LR: {lr_origin}->{lr_dest}",
                actual=f"POD: {pod_origin}->{pod_dest}",
                message="Route mismatch between LR and POD"
            )

    def _validate_weight_consistency(self, lr: Dict, pod: Dict, inv: Dict) -> ValidationResult:
        """Validate partial/split delivery by comparing LR shipped weight vs POD delivered weight."""
        try:
            lr_weight = float(lr.get("weight", 0) or 0)
            pod_weight = float(pod.get("weight", 0) or 0)
        except (TypeError, ValueError):
            return ValidationResult(
                rule="WEIGHT_CONSISTENCY",
                passed=False,
                expected="Valid numeric weights for LR and POD",
                actual=f"LR={lr.get('weight')}, POD={pod.get('weight')}",
                message="Could not parse weight values",
            )

        if lr_weight <= 0 or pod_weight <= 0:
            return ValidationResult(
                rule="WEIGHT_CONSISTENCY",
                passed=True,
                expected="POD weight should be close to LR weight",
                actual=f"LR={lr_weight}, POD={pod_weight}",
                message="Insufficient weight data for partial delivery check",
            )

        ratio = pod_weight / lr_weight
        if ratio >= settings.partial_delivery_min_ratio:
            return ValidationResult(
                rule="WEIGHT_CONSISTENCY",
                passed=True,
                expected=f"POD/LR ratio >= {settings.partial_delivery_min_ratio:.2f}",
                actual=f"POD/LR ratio={ratio:.3f}",
                message="Delivered weight is consistent with shipped weight",
            )

        try:
            lr_amount = float(lr.get("amount", 0) or 0)
            inv_amount = float(inv.get("amount", 0) or 0)
        except (TypeError, ValueError):
            lr_amount = 0.0
            inv_amount = 0.0

        overcharge_hint = ""
        if lr_amount > 0 and inv_amount > 0:
            full_charge_variance = abs(inv_amount - lr_amount) / lr_amount
            if full_charge_variance <= settings.partial_delivery_full_charge_tolerance:
                overcharge_hint = " and invoice appears to charge full LR amount"

        return ValidationResult(
            rule="WEIGHT_CONSISTENCY",
            passed=False,
            expected=f"POD/LR ratio >= {settings.partial_delivery_min_ratio:.2f}",
            actual=f"LR weight={lr_weight}, POD weight={pod_weight}, ratio={ratio:.3f}",
            message=f"Partial/split delivery detected (shortfall {(1.0 - ratio) * 100:.1f}%){overcharge_hint}",
        )

    def _validate_contract_rate(self, inv: Dict, contract_rate: Dict | None) -> ValidationResult:
        """Validate invoice amount/surcharges against agreed contract rates."""
        if not contract_rate:
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=True,
                expected="Active contract rate for vendor/route",
                actual="No contract rate configured",
                message="Skipped contract-rate validation due to missing contract setup",
            )

        try:
            expected_total = (
                float(contract_rate.get("base_rate", 0) or 0)
                + float(contract_rate.get("fuel_surcharge", 0) or 0)
                + float(contract_rate.get("detention_rate", 0) or 0)
                + float(contract_rate.get("distance_rate", 0) or 0)
            )
            inv_amount = float(inv.get("amount", 0) or 0)
        except (TypeError, ValueError):
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=False,
                expected="Valid numeric contract and invoice values",
                actual=f"contract={contract_rate}, invoice_amount={inv.get('amount')}",
                message="Could not parse contract/invoice amount fields",
            )

        if expected_total <= 0:
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=True,
                expected="Contract total > 0",
                actual=f"expected_total={expected_total}",
                message="Skipped contract mismatch check due to zero contract total",
            )

        variance = abs(inv_amount - expected_total) / expected_total
        if variance > settings.contract_rate_tolerance:
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=False,
                expected=f"Variance <= {settings.contract_rate_tolerance * 100:.1f}%",
                actual=f"invoice={inv_amount}, contract_total={expected_total}, variance={variance * 100:.1f}%",
                message="Invoice amount deviates from agreed contract rate",
            )

        fuel = float(contract_rate.get("fuel_surcharge", 0) or 0)
        base = float(contract_rate.get("base_rate", 0) or 0)
        detention = float(contract_rate.get("detention_rate", 0) or 0)
        if base > 0 and fuel > base * settings.contract_fuel_surcharge_max_pct:
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=False,
                expected=f"Fuel surcharge <= {settings.contract_fuel_surcharge_max_pct * 100:.0f}% of base rate",
                actual=f"fuel={fuel}, base={base}",
                message="Fuel surcharge exceeds policy limit",
            )
        if detention > settings.contract_max_detention_charge:
            return ValidationResult(
                rule="CONTRACT_RATE_MATCH",
                passed=False,
                expected=f"Detention charge <= {settings.contract_max_detention_charge}",
                actual=f"detention={detention}",
                message="Detention charge exceeds policy limit",
            )

        return ValidationResult(
            rule="CONTRACT_RATE_MATCH",
            passed=True,
            expected=f"Variance <= {settings.contract_rate_tolerance * 100:.1f}%",
            actual=f"invoice={inv_amount}, contract_total={expected_total}, variance={variance * 100:.1f}%",
            message="Invoice amount is within agreed contract tolerance",
        )
    
    def results_to_dict(self, results: List[ValidationResult]) -> List[Dict]:
        """Convert validation results to dictionary for JSON storage."""
        return [
            {
                'rule': r.rule,
                'passed': r.passed,
                'expected': r.expected,
                'actual': r.actual,
                'message': r.message
            }
            for r in results
        ]
