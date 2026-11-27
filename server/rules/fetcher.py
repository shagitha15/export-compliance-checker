"""
Official Indian Government Regulatory Source Fetchers (DGFT, ICEGATE, CBIC).
Connects strictly with verified TLS, explicit retry/backoff, and polite timeouts.
Extracts only verifiable facts directly present on official portals without inventing metadata.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import ssl
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import fitz  # PyMuPDF
import httpx

from server.config.settings import get_settings
from server.logging.logger import get_logger
from server.schemas.rules_monitoring import GovernmentNotificationRecord, SourceSyncOutcome

logger = get_logger("server.rules.fetcher")

OFFICIAL_SOURCES = {
    "DGFT": {
        "label": "Directorate General of Foreign Trade (DGFT)",
        "portal_url": "https://www.dgft.gov.in/CP/",
    },
    "CBIC": {
        "label": "Central Board of Indirect Taxes & Customs (CBIC)",
        "portal_url": "https://taxinformation.cbic.gov.in/",
        "fallback_url": "https://www.cbic.gov.in/",
    },
    "ICEGATE": {
        "label": "Indian Customs EDI Gateway (ICEGATE)",
        "portal_url": "https://www.icegate.gov.in/archives/guidelines",
        "circulars_url": "https://www.icegate.gov.in/archives/circulars",
        "home_url": "https://www.icegate.gov.in/",
    },
}

USER_AGENT = "ExportCustomsComplianceChecker/2.0 (+official-public-regulatory-sync)"

_EXPORT_KEYWORDS = (
    "export",
    "customs",
    "shipping bill",
    "scmtr",
    "swift",
    "iec",
    "dgft",
    "icegate",
    "cbic",
    "lut",
    "igst",
    "drawback",
    "rodtep",
    "scomet",
    "itc (hs)",
    "itc(hs)",
    "schedule-2",
    "schedule 2",
    "advance authorisation",
    "epcg",
    "eou",
    "certificate of origin",
    "e-brc",
    "foreign trade",
    "ftp",
    "advisory",
    "circular",
    "warehouse",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_date_str(raw: str | None) -> str | None:
    """Normalizes DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD dates into ISO YYYY-MM-DD."""
    if not raw:
        return None
    cleaned = re.sub(r"\s+", " ", raw.strip())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _compute_notification_id(source: str, notif_num: str, source_url: str, title: str) -> str:
    key = f"{source.upper()}|{notif_num.strip().lower()}|{source_url.strip().lower()}|{title.strip().lower()}"
    return f"{source.lower()}_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _compute_content_hash(*parts: str | None) -> str:
    joined = "|".join((p or "").strip() for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _extract_hs_prefixes(text: str) -> list[str]:
    matches = re.findall(r"\b(?:HS|HSN|Exim\s*Code)\s*(?:Code|Heading)?\s*[:\-]?\s*(\d{4,8})\b", text, re.I)
    unique = []
    for m in matches:
        prefix = m[:4]
        if prefix not in unique:
            unique.append(prefix)
    return unique or ["ALL"]


def _detect_export_relevance(title: str, summary: str, category: str) -> bool:
    combined = f"{title} {summary} {category}".lower()
    if "import policy" in combined and "export" not in combined and "customs" not in combined:
        return False
    return any(kw in combined for kw in _EXPORT_KEYWORDS)


def _extract_effective_date_from_text(text: str) -> str | None:
    """Extracts explicit effective date only when explicitly stated in notice text."""
    patterns = [
        r"(?:with\s+effect\s+from|w\.e\.f\.?|effective\s+from|comes\s+into\s+force\s+on)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})",
        r"(?:with\s+effect\s+from|w\.e\.f\.?|effective\s+from|comes\s+into\s+force\s+on)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            norm = normalize_date_str(m.group(1))
            if norm:
                return norm
    return None


def _http_get_with_retry(
    client: httpx.Client,
    url: str,
    max_retries: int = 2,
    backoff_seconds: float = 0.8,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            # Do not retry TLS certificate failures — fail fast & truthfully
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                raise
            if attempt < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
    assert last_exc is not None
    raise last_exc


def _extract_pdf_preview(client: httpx.Client, pdf_url: str, max_bytes: int = 2_000_000) -> str:
    """Downloads a small official PDF attachment (verified TLS) and extracts first 2 pages."""
    parsed = urlparse(pdf_url)
    if parsed.scheme != "https":
        return ""
    try:
        resp = client.get(pdf_url)
        if resp.status_code != 200 or len(resp.content) > max_bytes:
            return ""
        doc = fitz.open(stream=resp.content, filetype="pdf")
        try:
            pages = [doc[i].get_text("text") for i in range(min(2, len(doc)))]
            return re.sub(r"\s+", " ", " ".join(pages)).strip()[:2500]
        finally:
            doc.close()
    except Exception as exc:
        logger.debug("Optional PDF text extraction skipped for %s: %s", pdf_url, exc)
        return ""


class _IcegateTableParser(HTMLParser):
    """Parses Drupal table rows on ICEGATE /archives/guidelines and /archives/circulars."""

    def __init__(self) -> None:
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.current_row: list[dict[str, str]] = []
        self.current_text: list[str] = []
        self.current_href: str | None = None
        self.rows: list[list[dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag_l in ("td", "th") and self.in_tr:
            self.in_td = True
            self.current_text = []
            self.current_href = None
        elif tag_l == "a" and self.in_td:
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self.current_href = v.strip()

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l in ("td", "th") and self.in_td:
            self.in_td = False
            self.current_row.append({
                "text": re.sub(r"\s+", " ", "".join(self.current_text)).strip(),
                "href": self.current_href or "",
            })
        elif tag_l == "tr" and self.in_tr:
            self.in_tr = False
            if self.current_row:
                self.rows.append(self.current_row)

    def handle_data(self, data: str) -> None:
        if self.in_td:
            self.current_text.append(data)


def parse_dgft_cp_html(
    html_text: str,
    base_url: str = "https://www.dgft.gov.in/CP/",
    max_items: int = 25,
    pdf_fetcher: Any = None,
) -> list[GovernmentNotificationRecord]:
    """Parses official DGFT embedded `#plnNewsDtl` JSON records from DGFT portal HTML."""
    match = re.search(
        r'<input[^>]*id=["\']plnNewsDtl["\'][^>]*value=["\'](.*?)["\']',
        html_text,
        re.S | re.I,
    )
    if not match:
        raise ValueError("DGFT `#plnNewsDtl` notification payload not found in portal HTML.")

    raw_val = html_lib.unescape(match.group(1))
    parsed = json.loads(raw_val)
    if isinstance(parsed, str):
        parsed = json.loads(parsed)

    items = parsed.get("allNewsList") or []
    if not isinstance(items, list):
        raise ValueError("DGFT `allNewsList` payload has unexpected structure.")

    now = _utc_now_iso()
    records: list[GovernmentNotificationRecord] = []
    for entry in items[:max_items]:
        category = str(entry.get("title") or "Notification").strip()
        notif_num = str(entry.get("metadata1") or "Unnumbered").strip()
        subject = html_lib.unescape(str(entry.get("metadata3") or "")).strip()
        raw_date = str(entry.get("metadata4") or "").strip()
        published_date = normalize_date_str(raw_date)

        direct_pdf = str(entry.get("path") or "").strip()
        attach_path = str(entry.get("attachPath") or "").strip()
        source_url = direct_pdf if direct_pdf.startswith("https://") else urljoin(base_url, attach_path or base_url)
        attachment_url = direct_pdf if direct_pdf.startswith("https://") else None

        pdf_text = ""
        if pdf_fetcher and attachment_url:
            pdf_text = pdf_fetcher(attachment_url)

        combined_summary = subject
        effective_date = _extract_effective_date_from_text(pdf_text or subject)
        if pdf_text:
            combined_summary = f"{subject} — Excerpt: {pdf_text[:320]}"

        hs_prefixes = _extract_hs_prefixes(f"{subject} {pdf_text}")
        export_relevant = _detect_export_relevance(subject, combined_summary, category)
        notif_id = _compute_notification_id("DGFT", notif_num, source_url, subject)
        c_hash = _compute_content_hash("DGFT", notif_num, subject, published_date, effective_date, source_url)

        records.append(
            GovernmentNotificationRecord(
                notification_id=notif_id,
                source="DGFT",
                category=category,
                notification_number=notif_num,
                title=subject or f"DGFT {category} {notif_num}".strip(),
                summary=combined_summary,
                published_date=published_date,
                effective_date=effective_date,
                source_url=source_url,
                attachment_url=attachment_url,
                fetched_at=now,
                last_verified_at=now,
                content_hash=c_hash,
                validation_status="validated",
                validation_notes=[],
                is_export_relevant=export_relevant,
                hs_prefixes=hs_prefixes,
            )
        )
    return records


def parse_icegate_table_html(
    html_text: str,
    page_url: str,
    default_category: str = "Advisory",
    max_items: int = 25,
) -> list[GovernmentNotificationRecord]:
    """Parses ICEGATE table rows (S No | Name | Category | Date | Download link)."""
    parser = _IcegateTableParser()
    parser.feed(html_text)
    now = _utc_now_iso()
    records: list[GovernmentNotificationRecord] = []

    for row in parser.rows:
        if len(row) < 4:
            continue
        texts = [c["text"] for c in row]
        # Skip header row
        if any(t.lower() in ("name", "s no") for t in texts[:3]):
            continue

        # Support optional leading image td in `/archives/circulars`
        offset = 1 if texts[0] == "" and len(row) >= 6 else 0
        if len(row) - offset < 5:
            continue

        title = row[offset + 1]["text"]
        category = row[offset + 2]["text"] or default_category
        raw_date = row[offset + 3]["text"]
        link_href = row[offset + 4]["href"]

        if not title:
            continue

        source_url = urljoin("https://www.icegate.gov.in/", link_href or page_url)
        published_date = normalize_date_str(raw_date)
        notif_match = re.search(r"(?:Circular\s*No\.?|Advisory\s*(?:No\.?)?)\s*[:\-]?\s*([A-Za-z0-9/.\-]+)", title, re.I)
        notif_num = notif_match.group(1) if notif_match else f"ICEGATE-{published_date or 'UN'}"

        notif_id = _compute_notification_id("ICEGATE", notif_num, source_url, title)
        c_hash = _compute_content_hash("ICEGATE", notif_num, title, category, published_date, source_url)
        records.append(
            GovernmentNotificationRecord(
                notification_id=notif_id,
                source="ICEGATE",
                category=category,
                notification_number=notif_num,
                title=title,
                summary=f"{category}: {title}",
                published_date=published_date,
                effective_date=None,
                source_url=source_url,
                attachment_url=source_url if source_url.lower().endswith(".pdf") else None,
                fetched_at=now,
                last_verified_at=now,
                content_hash=c_hash,
                validation_status="validated",
                validation_notes=[],
                is_export_relevant=_detect_export_relevance(title, category, default_category),
                hs_prefixes=_extract_hs_prefixes(title),
            )
        )
        if len(records) >= max_items:
            break

    return records


def parse_cbic_html(html_text: str, page_url: str, max_items: int = 20) -> list[GovernmentNotificationRecord]:
    """Parses CBIC notifications/circulars anchors when verified TLS HTML is retrieved."""
    now = _utc_now_iso()
    records: list[GovernmentNotificationRecord] = []
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.S | re.I)
    for href, raw_txt in links:
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html_lib.unescape(raw_txt))).strip()
        if len(title) < 12:
            continue
        if not any(k in (title + " " + href).lower() for k in ("notification", "circular", "customs", "gst", "instruction", "tariff")):
            continue
        source_url = urljoin(page_url, href)
        date_match = re.search(r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})", title)
        pub_date = normalize_date_str(date_match.group(1)) if date_match else None
        num_match = re.search(r"(?:No\.?|Circular)\s*[:\-]?\s*([A-Za-z0-9/.\-]+)", title, re.I)
        notif_num = num_match.group(1) if num_match else "CBIC-Notice"

        notif_id = _compute_notification_id("CBIC", notif_num, source_url, title)
        records.append(
            GovernmentNotificationRecord(
                notification_id=notif_id,
                source="CBIC",
                category="CBIC Customs/GST Notice",
                notification_number=notif_num,
                title=title,
                summary=title,
                published_date=pub_date,
                effective_date=_extract_effective_date_from_text(title),
                source_url=source_url,
                attachment_url=source_url if source_url.lower().endswith(".pdf") else None,
                fetched_at=now,
                last_verified_at=now,
                content_hash=_compute_content_hash("CBIC", notif_num, title, pub_date, source_url),
                validation_status="validated",
                validation_notes=[],
                is_export_relevant=_detect_export_relevance(title, title, "CBIC"),
                hs_prefixes=_extract_hs_prefixes(title),
            )
        )
        if len(records) >= max_items:
            break
    return records


class OfficialGovernmentRuleFetcher:
    """Orchestrates verified HTTP fetching across DGFT, ICEGATE, and CBIC."""

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.settings = get_settings()
        self._external_client = http_client

    def _build_client(self, ca_bundle_path: str | None = None) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client

        verify_param: bool | ssl.SSLContext = True
        if ca_bundle_path:
            verify_param = ssl.create_default_context(cafile=ca_bundle_path)

        return httpx.Client(
            timeout=self.settings.RULE_SYNC_TIMEOUT_SECONDS,
            follow_redirects=True,
            verify=verify_param,
            headers={"User-Agent": USER_AGENT},
        )

    def fetch_all_sources(self) -> tuple[list[GovernmentNotificationRecord], list[SourceSyncOutcome]]:
        """Fetches notifications from DGFT, ICEGATE, and CBIC with strict error isolation."""
        all_notifications: list[GovernmentNotificationRecord] = []
        outcomes: list[SourceSyncOutcome] = []

        for source_name in ("DGFT", "ICEGATE", "CBIC"):
            notifs, outcome = self.fetch_source(source_name)
            all_notifications.extend(notifs)
            outcomes.append(outcome)
            time.sleep(0.25)

        return all_notifications, outcomes

    def fetch_source(self, source_name: str) -> tuple[list[GovernmentNotificationRecord], SourceSyncOutcome]:
        checked_at = _utc_now_iso()
        portal_url = OFFICIAL_SOURCES[source_name]["portal_url"]
        max_items = self.settings.RULE_SYNC_MAX_ITEMS_PER_SOURCE

        try:
            ca_bundle = self.settings.CBIC_CA_BUNDLE_PATH if source_name == "CBIC" else None
            client = self._build_client(ca_bundle_path=ca_bundle)
            should_close = self._external_client is None
            try:
                if source_name == "DGFT":
                    resp = _http_get_with_retry(client, portal_url)
                    pdf_fn = (lambda u: _extract_pdf_preview(client, u)) if self.settings.RULE_SYNC_FETCH_PDF_TEXT else None
                    records = parse_dgft_cp_html(resp.text, base_url=portal_url, max_items=max_items, pdf_fetcher=pdf_fn)
                elif source_name == "ICEGATE":
                    records: list[GovernmentNotificationRecord] = []
                    resp_g = _http_get_with_retry(client, portal_url)
                    records.extend(parse_icegate_table_html(resp_g.text, page_url=portal_url, default_category="Advisory", max_items=max_items))
                    time.sleep(0.25)
                    resp_c = _http_get_with_retry(client, OFFICIAL_SOURCES["ICEGATE"]["circulars_url"])
                    records.extend(parse_icegate_table_html(resp_c.text, page_url=OFFICIAL_SOURCES["ICEGATE"]["circulars_url"], default_category="Circular", max_items=max_items))
                    records = records[:max_items]
                elif source_name == "CBIC":
                    resp = _http_get_with_retry(client, portal_url)
                    records = parse_cbic_html(resp.text, page_url=portal_url, max_items=max_items)
                else:
                    raise ValueError(f"Unsupported government source: {source_name}")

                return records, SourceSyncOutcome(
                    source=source_name,  # type: ignore[arg-type]
                    source_url=portal_url,
                    status="success",
                    fetched_count=len(records),
                    checked_at=checked_at,
                )
            finally:
                if should_close:
                    client.close()

        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            if "CERTIFICATE_VERIFY_FAILED" in err_msg or isinstance(exc, ssl.SSLError):
                status = "tls_error"
                err_msg = (
                    f"Verified TLS connection rejected by client trust store ({err_msg}). "
                    "TLS verification was kept strictly enabled; configure CBIC_CA_BUNDLE_PATH with the official CA chain if needed."
                )
            elif isinstance(exc, (httpx.HTTPError, OSError)):
                status = "network_error"
            else:
                status = "parse_error"

            logger.warning("Government rule fetch failed for source=%s url=%s status=%s err=%s", source_name, portal_url, status, err_msg)
            return [], SourceSyncOutcome(
                source=source_name,  # type: ignore[arg-type]
                source_url=portal_url,
                status=status,  # type: ignore[arg-type]
                fetched_count=0,
                error_message=err_msg[:350],
                checked_at=checked_at,
            )
