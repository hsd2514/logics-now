from typing import Dict, List, Optional
from google import genai
from google.genai import types
from app.config import get_settings

settings = get_settings()

class AuditGenerator:
    """Novel Feature: AI-generated audit trail for compliance"""
    
    SYSTEM_INSTRUCTION = (
        "You are an audit documentation AI for logistics invoice reconciliation. "
        "Generate clear, professional audit explanations for document matching decisions. "
        "Include specific values and percentages. Be factual and compliance-focused. "
        "Keep explanations concise (2-3 sentences) but complete."
    )

    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None

    def generate_match_explanation(
        self, 
        lr_entities: Dict,
        pod_entities: Dict,
        invoice_entities: Dict,
        match_score: float,
        validation_results: List[Dict],
        decision: str
    ) -> str:
        """Generate AI explanation for a triplet match decision."""
        if not self.client:
            return self._generate_fallback(
                lr_entities, pod_entities, invoice_entities,
                match_score, validation_results, decision
            )

        context = f"""Match Details:
- LR Shipment ID: {lr_entities.get('shipment_id', 'N/A')}
- POD Shipment ID: {pod_entities.get('shipment_id', 'N/A')}
- Invoice Shipment ID: {invoice_entities.get('shipment_id', 'N/A')}
- LR Amount: {lr_entities.get('amount', 'N/A')}
- Invoice Amount: {invoice_entities.get('amount', 'N/A')}
- LR Date: {lr_entities.get('date', 'N/A')}
- POD Date: {pod_entities.get('date', 'N/A')}
- Invoice Date: {invoice_entities.get('date', 'N/A')}
- Match Score: {match_score * 100:.1f}%
- Decision: {decision}

Validation Results:
{self._format_validations(validation_results)}

Generate a professional audit explanation for this {decision} decision."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=context,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    max_output_tokens=200,
                )
            )
            return response.text
        except Exception:
            return self._generate_fallback(
                lr_entities, pod_entities, invoice_entities,
                match_score, validation_results, decision
            )

    def generate_fraud_explanation(
        self,
        alert_type: str,
        risk_score: float,
        details: Dict
    ) -> str:
        """Generate AI explanation for a fraud alert."""
        if not self.client:
            return self._generate_fraud_fallback(alert_type, risk_score, details)

        context = f"""Fraud Alert:
- Type: {alert_type}
- Risk Score: {risk_score * 100:.1f}%
- Details: {details}

Generate a clear explanation of this fraud alert for the compliance team."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=context,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    max_output_tokens=150,
                )
            )
            return response.text
        except Exception:
            return self._generate_fraud_fallback(alert_type, risk_score, details)

    def _format_validations(self, validations: List[Dict]) -> str:
        """Format validation results for prompt."""
        if not validations:
            return "No validation results available"
        lines = []
        for v in validations:
            status = "PASS" if v.get('passed') else "FAIL"
            lines.append(f"- {v.get('rule', 'Unknown')}: {status} - {v.get('message', '')}")
        return "\n".join(lines)

    def _generate_fallback(
        self,
        lr_entities: Dict,
        pod_entities: Dict,
        invoice_entities: Dict,
        match_score: float,
        validation_results: List[Dict],
        decision: str
    ) -> str:
        """Generate explanation without AI."""
        lr_id  = lr_entities.get('shipment_id', 'N/A')
        pod_id = pod_entities.get('shipment_id', 'N/A')
        inv_id = invoice_entities.get('shipment_id', 'N/A')
        lr_amt  = lr_entities.get('amount', 0)
        inv_amt = invoice_entities.get('amount', 0)

        variance_text = ""
        try:
            if float(lr_amt) > 0:
                variance = abs(float(inv_amt) - float(lr_amt)) / float(lr_amt) * 100
                variance_text = f"Amount variance: {variance:.1f}%. "
        except Exception:
            pass

        passed = sum(1 for v in validation_results if v.get('passed'))
        total  = len(validation_results)

        if decision == "AUTO_APPROVED":
            return (
                f"Triplet auto-approved with {match_score * 100:.1f}% confidence. "
                f"LR #{lr_id} matched with POD #{pod_id} and Invoice #{inv_id}. "
                f"{variance_text}Validation: {passed}/{total} rules passed. "
                f"Auto-approved per policy threshold."
            )
        elif decision == "APPROVED":
            return (
                f"Triplet manually approved. "
                f"LR #{lr_id}, POD #{pod_id}, Invoice #{inv_id}. "
                f"Match score: {match_score * 100:.1f}%. {variance_text}"
                f"Human reviewer confirmed the match."
            )
        elif decision == "REJECTED":
            failed = [v.get('rule') for v in validation_results if not v.get('passed')]
            return (
                f"Triplet rejected. Match score: {match_score * 100:.1f}%. "
                f"Failed validations: {', '.join(failed) if failed else 'None'}. "
                f"Human reviewer rejected this match."
            )
        else:
            return (
                f"Triplet pending review. Match score: {match_score * 100:.1f}%. "
                f"LR #{lr_id}, POD #{pod_id}, Invoice #{inv_id}. "
                f"{variance_text}Validation: {passed}/{total} rules passed."
            )

    def _generate_fraud_fallback(self, alert_type: str, risk_score: float, details: Dict) -> str:
        """Generate fraud explanation without AI."""
        explanations = {
            "DUPLICATE":      f"Potential duplicate invoice detected with {risk_score * 100:.0f}% risk score. "
                              f"Invoice matches previously processed document.",
            "AMOUNT_ANOMALY": f"Amount anomaly detected with {risk_score * 100:.0f}% risk score. "
                              f"Invoice amount deviates significantly from expected range.",
            "VENDOR_ANOMALY": f"Vendor behavior anomaly with {risk_score * 100:.0f}% risk score. "
                              f"Unusual invoice pattern from this vendor.",
            "PREDICTED":      f"Predictive fraud alert with {risk_score * 100:.0f}% risk score. "
                              f"Pattern analysis indicates potential issue.",
            "DATE_MISMATCH":  f"Date sequence violation with {risk_score * 100:.0f}% risk score. "
                              f"Document dates are in incorrect order.",
        }
        return explanations.get(alert_type, f"Fraud alert: {alert_type} with {risk_score * 100:.0f}% risk.")
