from __future__ import annotations

from analyzer.header_analyzer import analyze_headers
from analyzer.preprocessor import preprocess_email
from analyzer.url_checker import analyze_urls
from utils.schemas import EmailMessage, ScanResult


class PhishGuardPipeline:
    def __init__(self, predictor, threshold: float = 0.75, expand_short_urls: bool = False) -> None:
        self.predictor = predictor
        self.threshold = threshold
        self.expand_short_urls = expand_short_urls

    def scan_email(self, email_obj: EmailMessage) -> ScanResult:
        prepared_text = preprocess_email(email_obj.subject, email_obj.body)
        phishing_probability = float(self.predictor.predict_proba(prepared_text))
        header_info = analyze_headers(email_obj.headers, email_obj.sender)
        url_findings = analyze_urls(email_obj.body, expand=self.expand_short_urls)

        reasons = list(header_info.get("reasons", []))
        suspicious_urls = [item for item in url_findings if item.suspicious]
        for finding in suspicious_urls:
            reasons.append(f"Suspicious URL: {finding.url} ({finding.reason})")

        if phishing_probability >= self.threshold:
            reasons.insert(
                0,
                f"Model score {phishing_probability:.2f} exceeds threshold {self.threshold:.2f}",
            )

        label = "PHISHING" if phishing_probability > self.threshold else "LEGITIMATE"
        risk_level = self._resolve_risk_level(
            phishing_probability=phishing_probability,
            suspicious_url_count=len(suspicious_urls),
            spf_status=str(header_info.get("spf_status", "unknown")),
            dkim_status=str(header_info.get("dkim_status", "unknown")),
        )

        return ScanResult(
            message_id=email_obj.message_id,
            received_at=email_obj.received_at,
            phishing_probability=phishing_probability,
            label=label,
            risk_level=risk_level,
            reasons=reasons,
            urls=url_findings,
            spf_status=str(header_info.get("spf_status", "unknown")),
            dkim_status=str(header_info.get("dkim_status", "unknown")),
        )

    def scan_batch(self, emails: list[EmailMessage]) -> list[ScanResult]:
        return [self.scan_email(item) for item in emails]

    def _resolve_risk_level(
        self,
        phishing_probability: float,
        suspicious_url_count: int,
        spf_status: str,
        dkim_status: str,
    ) -> str:
        if (
            phishing_probability >= 0.9
            or suspicious_url_count >= 2
            or (spf_status == "fail" and dkim_status == "fail")
        ):
            return "HIGH"
        if phishing_probability >= self.threshold or suspicious_url_count == 1:
            return "MEDIUM"
        return "LOW"

