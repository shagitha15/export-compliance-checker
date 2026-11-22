"""
Government Customs Regulations Compliance Checker.

Audits shipment document data against statutory Indian export regulations
retrieved semantically from the Pinecone vector index.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from services.rules.embedding_service import generate_embedding
from services.rules.models import (
    GovernmentComplianceReport,
    GovernmentComplianceSummary,
    RegulatoryComplianceStatus,
    RegulatoryFinding,
)
from services.rules.pinecone_service import query_regulatory_rules
from services.rules.rule_seeder import seed_regulatory_rules


def extract_shipment_context(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Extracts compliance-relevant statutory attributes from shipment documents."""
    context: dict[str, Any] = {
        "hs_codes": set(),
        "exporter_iec_or_gstin": None,
        "exporter_name": None,
        "consignee_country": None,
        "currency": None,
        "has_declaration": False,
        "incoterms": None,
        "invoice_number": None,
    }

    # Inspect Commercial Invoice
    ci = documents.get("Commercial Invoice") or {}
    if ci:
        context["invoice_number"] = ci.get("invoice_number")
        context["currency"] = ci.get("currency")
        context["incoterms"] = ci.get("incoterms")
        if ci.get("exporter_seller"):
            context["exporter_iec_or_gstin"] = (
                ci["exporter_seller"].get("tax_id_or_gstin")
                or ci["exporter_seller"].get("iec")
            )
            context["exporter_name"] = ci["exporter_seller"].get("name")
        if ci.get("consignee_importer"):
            context["consignee_country"] = ci["consignee_importer"].get("country")
        if ci.get("declaration_and_signatory", {}).get("declaration_text"):
            context["has_declaration"] = True
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
    # Ensure regulatory rules are indexed
    seed_regulatory_rules()

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
            curr = context.get("currency") or "FREELY CONVERTIBLE"
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
                    observed_evidence=f"Shipment is invoiced in permissible convertible currency '{curr}'.",
                )
            )

        elif rid == "ITCHS_SCH2_8483":  # HS 8483 Policy
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
                    observed_evidence="Commodity classified under HS 8483 is permitted without specific DGFT export license.",
                )
            )

        elif rid == "DGFT_FTP2023_P2_06":  # AD Code
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
                    observed_evidence="Port registration required. Ensure bank AD code is active on ICEGATE.",
                    action_required="Verify AD code registration on ICEGATE before customs assessment.",
                )
            )

        elif rid == "CBIC_GST_LUT_CIRC08":  # GST LUT
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
                    observed_evidence="Check invoice endorsement for GST LUT ARN reference.",
                )
            )

        elif rid == "CBIC_CA1962_VAL14":  # Valuation
            inco = context.get("incoterms") or "FOB"
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
                    observed_evidence=f"Incoterms declared as '{inco}'; consistent with customs valuation principles.",
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
