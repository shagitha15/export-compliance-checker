"""
Government Customs Regulations Compliance Checker.
Audits shipment document data against statutory Indian export regulations
retrieved semantically from the Pinecone vector index.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from server.integrations.embeddings import generate_embedding
from server.integrations.pinecone import query_regulatory_rules
from server.rules.seeder import ensure_regulatory_rules_seeded
from server.schemas.compliance import (
    GovernmentComplianceReport,
    GovernmentComplianceSummary,
    RegulatoryComplianceStatus,
    RegulatoryFinding,
)

CONVERTIBLE_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "SGD",
    "AED", "SAR", "HKD", "SEK", "NOK", "DKK", "NZD", "INR",
}


def extract_shipment_context(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Extracts compliance-relevant statutory attributes from shipment documents."""
    context: dict[str, Any] = {
        "hs_codes": set(),
        "exporter_iec_or_gstin": None,
        "exporter_name": None,
        "consignee_country": None,
        "currency": None,
        "has_declaration": False,
        "declaration_text": "",
        "incoterms": None,
        "invoice_number": None,
        "ad_code": None,
        "lut_arn": None,
        "sb_fob_value": None,
        "ci_total_value": None,
    }

    # Inspect Commercial Invoice
    ci = documents.get("Commercial Invoice") or {}
    if ci:
        context["invoice_number"] = ci.get("invoice_number")
        context["currency"] = ci.get("currency")
        context["incoterms"] = ci.get("incoterms")
        context["ci_total_value"] = ci.get("total_invoice_amount")
        if ci.get("exporter_seller"):
            context["exporter_iec_or_gstin"] = (
                ci["exporter_seller"].get("tax_id_or_gstin")
                or ci["exporter_seller"].get("iec")
            )
            context["exporter_name"] = ci["exporter_seller"].get("name")
        if ci.get("consignee_importer"):
            context["consignee_country"] = ci["consignee_importer"].get("country")
        decl = (ci.get("declaration_and_signatory") or {}).get("declaration_text") or ""
        if decl:
            context["has_declaration"] = True
            context["declaration_text"] = str(decl)
        context["lut_arn"] = ci.get("lut_arn") or (ci.get("tax_details") or {}).get("lut_arn")
        for it in ci.get("line_items") or []:
            hs = it.get("hs_code")
            if hs:
                clean_hs = "".join(filter(str.isdigit, str(hs)))[:6]
                if clean_hs:
                    context["hs_codes"].add(clean_hs)

    # Inspect Shipping Bill
    sb = documents.get("Shipping Bill") or {}
    if sb:
        if not context["exporter_iec_or_gstin"]:
            context["exporter_iec_or_gstin"] = sb.get("iec") or sb.get("gstin")
        if not context["consignee_country"]:
            context["consignee_country"] = sb.get("country_of_destination")
        if not context["currency"]:
            context["currency"] = sb.get("currency")
        context["ad_code"] = sb.get("ad_code") or sb.get("bank_ad_code")
        if not context["lut_arn"]:
            context["lut_arn"] = sb.get("lut_arn")
        context["sb_fob_value"] = sb.get("fob_value")
        for it in sb.get("items") or []:
            hs = it.get("ritc_hs_code") or it.get("hs_code")
            if hs:
                clean_hs = "".join(filter(str.isdigit, str(hs)))[:6]
                if clean_hs:
                    context["hs_codes"].add(clean_hs)

    context["hs_codes"] = sorted(list(context["hs_codes"]))
    return context


def verify_government_rules(
    documents: dict[str, dict[str, Any]],
) -> GovernmentComplianceReport:
    """
    Retrieves matching statutory provisions from Pinecone and verifies
    the shipment against official Indian export regulations.

    Args:
        documents: Map of document type to extracted JSON data.

    Returns:
        GovernmentComplianceReport: Detailed statutory findings with source citations.
    """
    # Seed rules once per worker lifecycle instead of on every API request
    ensure_regulatory_rules_seeded()

    context = extract_shipment_context(documents)
    audit_id = f"gov_aud_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat()
    findings: list[RegulatoryFinding] = []

    # 1. Semantic Retrieval: Universal Export Mandates
    univ_query = "Mandatory exporter IEC, AD code and truthfulness declaration on shipping bill"
    univ_vector = generate_embedding(univ_query, task_type="RETRIEVAL_QUERY")
    universal_rules = query_regulatory_rules(univ_vector, top_k=4)

    # 2. Semantic Retrieval: Commodity & HS Policy Restrictions
    hs_code = context["hs_codes"][0] if context["hs_codes"] else "ALL"
    hs_query = f"ITC HS Schedule 2 export policy conditions, SCOMET dual-use restrictions, and licensing for {hs_code}"
    hs_vector = generate_embedding(hs_query, task_type="RETRIEVAL_QUERY")
    hs_rules = query_regulatory_rules(hs_vector, top_k=4, hs_prefix=hs_code[:4] if hs_code != "ALL" else None)

    # Combine unique matched rules by rule_id
    seen_rule_ids = set()
    all_matched_rules = []
    for r in universal_rules + hs_rules:
        rid = r["rule_id"]
        if rid not in seen_rule_ids:
            seen_rule_ids.add(rid)
            all_matched_rules.append(r)

    # Also include active approved non-seed rules synced from live government sources when HS matches
    try:
        from server.repositories.rules_repository import RuleRegistryRepository

        hs_prefixes_in_shipment = [str(code)[:4] for code in context.get("hs_codes", []) if code]
        for active_rule in RuleRegistryRepository().list_active_verified_rules():
            if active_rule.is_seed_rule or active_rule.rule_id in seen_rule_ids:
                continue
            rule_hs = active_rule.applicable_hs_prefixes or ["ALL"]
            hs_matches = "ALL" in rule_hs or any(
                hp.startswith(p) for hp in hs_prefixes_in_shipment for p in rule_hs
            )
            if hs_matches:
                seen_rule_ids.add(active_rule.rule_id)
                all_matched_rules.append(
                    {
                        "rule_id": active_rule.rule_id,
                        "score": 1.0,
                        "metadata": {
                            "rule_id": active_rule.rule_id,
                            "authority": active_rule.authority,
                            "policy_document": active_rule.policy_document,
                            "section_or_para": active_rule.para_ref,
                            "rule_title": active_rule.rule_title,
                            "applicable_hs_prefixes": active_rule.applicable_hs_prefixes,
                            "mandatory_documents": active_rule.mandatory_documents,
                            "source_url": active_rule.source_url,
                            "published_date": active_rule.published_date or "",
                            "effective_date": active_rule.effective_date or "",
                            "text": active_rule.rule_text,
                        },
                    }
                )
    except Exception:
        pass

    # 3. Evaluate each statutory rule against shipment context
    for match in all_matched_rules:
        meta = match.get("metadata", {})
        rid = meta.get("rule_id", match.get("rule_id"))
        title = meta.get("rule_title", "")
        authority = meta.get("authority", "")
        doc = meta.get("policy_document", "")
        para = meta.get("section_or_para", "")
        url = meta.get("source_url", "")

        # Rule evaluation logic:
        if rid == "DGFT_FTP2023_P2_05":  # Mandatory IEC
            iec = context["exporter_iec_or_gstin"]
            if iec:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Exporter must possess and cite a valid Importer Exporter Code (IEC).",
                        observed_evidence=f"Valid Exporter Tax ID / IEC cited: '{iec}'.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.NON_COMPLIANT,
                        requirement_summary="Exporter must possess and cite a valid Importer Exporter Code (IEC).",
                        observed_evidence="No IEC or Exporter Tax ID found on Commercial Invoice or Shipping Bill.",
                        action_required="Provide the 10-digit DGFT-issued IEC number on all export documents.",
                    )
                )

        elif rid == "CBIC_CA1962_SEC50":  # Truthfulness Declaration
            if context["has_declaration"]:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Statutory declaration of truthfulness required under Section 50 Customs Act.",
                        observed_evidence="Authorized declaration of truthfulness identified on Commercial Invoice.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.NON_COMPLIANT,
                        requirement_summary="Statutory declaration of truthfulness required under Section 50 Customs Act.",
                        observed_evidence="Missing authorized declaration / signatory clause on invoice.",
                        action_required="Include the standard Customs Section 50 declaration endorsement and signatory.",
                    )
                )

        elif rid == "RBI_FEMA_EXP_09M":  # FEMA 9-month realization
            raw_curr = str(context.get("currency") or "").strip().upper()
            if not raw_curr:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.NON_COMPLIANT,
                        requirement_summary="Full export proceeds must be realized within 9 months in approved convertible currency.",
                        observed_evidence="Invoice/Shipping Bill currency could not be detected for FEMA export realization audit.",
                        action_required="Declare a valid ISO billing currency (e.g., USD, EUR, GBP) on the Commercial Invoice and Shipping Bill.",
                    )
                )
            elif raw_curr in CONVERTIBLE_CURRENCIES:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Full export proceeds must be realized within 9 months in approved convertible currency.",
                        observed_evidence=f"Shipment is invoiced in permissible currency '{raw_curr}'.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.ADVISORY,
                        requirement_summary="Full export proceeds must be realized within 9 months in approved convertible currency.",
                        observed_evidence=f"Currency '{raw_curr}' requires Authorised Dealer bank verification under RBI FEMA guidelines.",
                        action_required="Confirm convertible FX or permitted Vostro settlement with your AD bank.",
                    )
                )

        elif rid == "ITCHS_SCH2_8483":  # HS 8483 Policy (only when HS 8483 is actually shipped)
            has_hs_8483 = any(code.startswith("8483") for code in context["hs_codes"])
            if not has_hs_8483:
                continue
            findings.append(
                RegulatoryFinding(
                    rule_id=rid,
                    rule_title=title,
                    authority=authority,
                    policy_document=doc,
                    para_ref=para,
                    source_url=url,
                    status=RegulatoryComplianceStatus.COMPLIANT,
                    requirement_summary="Export of transmission shafts and mechanical components (HS 8483) is 'Free'.",
                    observed_evidence="Commodity classified under HS 8483 is permitted without specific DGFT export license (subject to SCOMET screening).",
                )
            )

        elif rid == "DGFT_FTP2023_P2_06":  # AD Code
            ad_code = context.get("ad_code")
            if ad_code:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Authorised Dealer (AD) code must be pre-registered on ICEGATE for loading port.",
                        observed_evidence=f"Authorised Dealer (AD) code '{ad_code}' detected on Shipping Bill.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.ADVISORY,
                        requirement_summary="Authorised Dealer (AD) code must be pre-registered on ICEGATE for loading port.",
                        observed_evidence="Bank AD code was not detected on uploaded documents. Ensure active ICEGATE port registration.",
                        action_required="Verify 14-digit bank AD code registration on ICEGATE before customs assessment.",
                    )
                )

        elif rid == "CBIC_GST_LUT_CIRC08":  # GST LUT
            lut_arn = context.get("lut_arn")
            decl_lower = (context.get("declaration_text") or "").lower()
            has_lut_endorsement = bool(lut_arn) or "letter of undertaking" in decl_lower or "igst" in decl_lower or "lut" in decl_lower
            if has_lut_endorsement:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Invoice must endorse supply under LUT without payment of IGST or on payment of IGST.",
                        observed_evidence=f"GST LUT / IGST export endorsement identified{f' (ARN: {lut_arn})' if lut_arn else ''}.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.ADVISORY,
                        requirement_summary="Invoice must endorse supply under LUT without payment of IGST or on payment of IGST.",
                        observed_evidence="No explicit GST LUT ARN or IGST payment endorsement was detected on the invoice.",
                        action_required="Add Rule 96A LUT ARN or IGST payment endorsement on the Commercial Invoice.",
                    )
                )

        elif rid == "CBIC_CA1962_VAL14":  # Valuation
            inco = str(context.get("incoterms") or "").strip().upper()
            if not inco:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.ADVISORY,
                        requirement_summary="Assessable export value must reflect Free on Board (FOB) transaction value.",
                        observed_evidence="Incoterms not detected on Commercial Invoice; unable to confirm FOB vs CIF/CFR valuation.",
                        action_required="Declare Incoterms 2020 (e.g. FOB, CIF) and Shipping Bill FOB assessable value.",
                    )
                )
            elif inco.startswith(("CIF", "CFR")):
                sb_fob = context.get("sb_fob_value")
                ci_val = context.get("ci_total_value")
                if sb_fob is not None and ci_val is not None and float(sb_fob) <= float(ci_val):
                    findings.append(
                        RegulatoryFinding(
                            rule_id=rid,
                            rule_title=title,
                            authority=authority,
                            policy_document=doc,
                            para_ref=para,
                            source_url=url,
                            status=RegulatoryComplianceStatus.COMPLIANT,
                            requirement_summary="Assessable export value must reflect Free on Board (FOB) transaction value.",
                            observed_evidence=f"Invoice billed under '{inco}' ({ci_val}); Shipping Bill declares assessable FOB value ({sb_fob}).",
                        )
                    )
                else:
                    findings.append(
                        RegulatoryFinding(
                            rule_id=rid,
                            rule_title=title,
                            authority=authority,
                            policy_document=doc,
                            para_ref=para,
                            source_url=url,
                            status=RegulatoryComplianceStatus.ADVISORY,
                            requirement_summary="Assessable export value must reflect Free on Board (FOB) transaction value.",
                            observed_evidence=f"Invoice uses '{inco}' terms; verify freight/insurance deductions for Shipping Bill FOB value.",
                            action_required="Ensure freight and insurance charges are broken out so FOB assessable value is declared on the Shipping Bill.",
                        )
                    )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Assessable export value must reflect Free on Board (FOB) transaction value.",
                        observed_evidence=f"Incoterms declared as '{inco}'; consistent with customs FOB valuation principles.",
                    )
                )

        elif rid == "DGFT_SCOMET_GEN":  # SCOMET Dual-Use Controls
            line_items = (
                documents.get("Commercial Invoice", {}).get("line_items")
                or documents.get("Shipping Bill", {}).get("items")
                or []
            )
            has_license = (
                bool(documents.get("Shipping Bill", {}).get("scheme_code"))
                or any("license" in str(it).lower() or "authorization" in str(it).lower() for it in line_items)
            )
            is_restricted_item = any(
                any(kw in str(it.get("description", "")).lower() for kw in ["dual-use", "military", "nuclear", "gyroscope", "scomet", "restricted", "chemical weapon", "defense"])
                or str(it.get("hs_code", "")).startswith(("8401", "8802", "9014", "9301"))
                or str(it.get("ritc_hs_code", "")).startswith(("8401", "8802", "9014", "9301"))
                for it in line_items
            )
            if is_restricted_item and not has_license:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.NON_COMPLIANT,
                        requirement_summary="Export of SCOMET dual-use items requires DGFT export authorization and End-User Certificate.",
                        observed_evidence="Shipment contains restricted dual-use/SCOMET goods without required DGFT export license or buyer End-User Certificate (EUC).",
                        action_required="Obtain SCOMET export authorization license from DGFT and file End-User Certificate.",
                    )
                )
            elif is_restricted_item and has_license:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="Export of SCOMET dual-use items requires DGFT export authorization and End-User Certificate.",
                        observed_evidence="SCOMET dual-use item identified with valid export authorization license.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.COMPLIANT,
                        requirement_summary="SCOMET dual-use export control screening.",
                        observed_evidence="Commercial item screening confirmed not subject to SCOMET dual-use licensing.",
                    )
                )

        else:  # Dynamically synced active government notifications / advisories
            req_docs = [str(d) for d in (meta.get("mandatory_documents") or []) if d]
            missing_req_docs = [
                d for d in req_docs
                if d not in documents and not any(d.lower() in k.lower() for k in documents)
            ]
            rule_desc = str(meta.get("text") or title or "Active official government notification.").strip()
            pub_date = str(meta.get("published_date") or "").strip()
            eff_date = str(meta.get("effective_date") or "").strip()
            date_info = " • ".join(
                part for part in (
                    f"Published: {pub_date}" if pub_date else "",
                    f"Effective: {eff_date}" if eff_date else "",
                ) if part
            )
            if missing_req_docs:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.NON_COMPLIANT,
                        requirement_summary=rule_desc[:280],
                        observed_evidence=(
                            f"Active synced notice ({date_info or 'verified official source'}) references mandatory document(s) "
                            f"{', '.join(missing_req_docs)} not detected in uploaded batch."
                        ),
                        action_required=f"Upload or verify: {', '.join(missing_req_docs)}.",
                    )
                )
            else:
                findings.append(
                    RegulatoryFinding(
                        rule_id=rid,
                        rule_title=title,
                        authority=authority,
                        policy_document=doc,
                        para_ref=para,
                        source_url=url,
                        status=RegulatoryComplianceStatus.ADVISORY,
                        requirement_summary=rule_desc[:280],
                        observed_evidence=(
                            f"Synced from official {authority} notice"
                            + (f" ({date_info})" if date_info else "")
                            + ". Applicable active export regulation surfaced for exporter verification."
                        ),
                    )
                )

    # 4. Compute Summary & Overall Status
    compliant_cnt = sum(1 for f in findings if f.status == RegulatoryComplianceStatus.COMPLIANT)
    non_compliant_cnt = sum(1 for f in findings if f.status == RegulatoryComplianceStatus.NON_COMPLIANT)
    advisory_cnt = sum(1 for f in findings if f.status == RegulatoryComplianceStatus.ADVISORY)

    overall = (
        RegulatoryComplianceStatus.NON_COMPLIANT
        if non_compliant_cnt > 0
        else RegulatoryComplianceStatus.COMPLIANT
    )

    summary = GovernmentComplianceSummary(
        total_rules_evaluated=len(findings),
        compliant_count=compliant_cnt,
        non_compliant_count=non_compliant_cnt,
        advisory_count=advisory_cnt,
    )

    return GovernmentComplianceReport(
        audit_id=audit_id,
        audit_timestamp=timestamp,
        hs_codes_evaluated=context["hs_codes"],
        destination_country=context.get("consignee_country"),
        overall_government_compliance=overall,
        summary=summary,
        findings=findings,
    )
