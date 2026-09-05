"""Analytics exports — CSV + PDF performance reports.

Endpoint: GET /api/analytics/export?format=csv|pdf&period=<days>
"""
import csv as _csv
import io
from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi import HTTPException, Depends, Response


async def _period_start(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _export_report_rows(db, workspace_id: str, days: int, now_iso) -> dict:
    since = await _period_start(days)
    reds = await db.redemptions.find(
        {"workspace_id": workspace_id, "created_at": {"$gt": since}},
        {"_id": 0}).to_list(20000)
    coupons = await db.coupons.find(
        {"workspace_id": workspace_id}, {"_id": 0, "qr_code": 0}).to_list(500)
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0}) or {}
    per_coupon: Dict[str, Dict[str, float]] = {}
    for r in reds:
        cid = r.get("coupon_id"); c = per_coupon.setdefault(cid, {
            "code": r.get("code"), "redemptions": 0, "revenue": 0.0, "discount": 0.0})
        c["redemptions"] += 1
        c["revenue"] += r.get("revenue", 0)
        c["discount"] += r.get("discount", 0)
    total_reds = len(reds)
    total_rev = sum(r.get("revenue", 0) for r in reds)
    total_disc = sum(r.get("discount", 0) for r in reds)
    return {
        "workspace_name": ws.get("name", ""),
        "period_days": days, "since": since,
        "total_redemptions": total_reds,
        "total_revenue": round(total_rev, 2),
        "total_discount": round(total_disc, 2),
        "avg_order_value": round(total_rev / total_reds, 2) if total_reds else 0.0,
        "top_coupons": sorted(per_coupon.values(),
                              key=lambda x: x["revenue"], reverse=True)[:20],
        "coupons": coupons,
        "generated_at": now_iso(),
    }


def _render_csv(rpt: dict, fname: str) -> Response:
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["PromoOS Performance Report"])
    w.writerow(["Workspace", rpt["workspace_name"]])
    w.writerow(["Period", f"Last {rpt['period_days']} days"])
    w.writerow(["Generated", rpt["generated_at"]])
    w.writerow([])
    w.writerow(["Total redemptions", rpt["total_redemptions"]])
    w.writerow(["Total revenue", rpt["total_revenue"]])
    w.writerow(["Total discount given", rpt["total_discount"]])
    w.writerow(["Avg order value", rpt["avg_order_value"]])
    w.writerow([])
    w.writerow(["--- Top coupons ---"])
    w.writerow(["Code", "Redemptions", "Revenue", "Discount"])
    for c in rpt["top_coupons"]:
        w.writerow([c["code"], c["redemptions"], round(c["revenue"], 2), round(c["discount"], 2)])
    w.writerow([])
    w.writerow(["--- All coupons ---"])
    w.writerow(["Code", "Name", "Type", "Discount", "State",
                "Impressions", "Redemptions", "Revenue"])
    for c in rpt["coupons"]:
        stats = c.get("stats") or {}
        w.writerow([c.get("code"), c.get("name"), c.get("type"),
                    c.get("discount_value"), c.get("state"),
                    stats.get("impressions", 0),
                    stats.get("redemptions", 0),
                    round(stats.get("revenue", 0), 2)])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{fname}.csv"'})


def _render_pdf(rpt: dict, period: int, fname: str) -> Response:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#0A0A0A"), spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#005CEE"), spaceBefore=12, spaceAfter=6)
    small = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#71717A"))
    body = []
    body.append(Paragraph("PromoOS Performance Report", title))
    body.append(Paragraph(f"{rpt['workspace_name']} · Last {period} days", small))
    body.append(Paragraph(rpt["generated_at"][:19].replace("T", " ") + " UTC", small))
    body.append(Spacer(1, 12))
    kpi_data = [
        ["Total Redemptions", "Total Revenue", "Total Discount", "AOV"],
        [str(rpt["total_redemptions"]),
         f"${rpt['total_revenue']:,.2f}",
         f"${rpt['total_discount']:,.2f}",
         f"${rpt['avg_order_value']:,.2f}"],
    ]
    kt = Table(kpi_data, colWidths=[120, 120, 120, 120])
    kt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A0A0A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
    ]))
    body.append(kt)
    body.append(Paragraph("Top coupons by revenue", h2))
    tbl = [["Code", "Redemptions", "Revenue", "Discount"]] + [
        [c["code"], str(c["redemptions"]),
         f"${round(c['revenue'], 2):,.2f}",
         f"${round(c['discount'], 2):,.2f}"] for c in rpt["top_coupons"][:15]]
    t = Table(tbl, colWidths=[120, 100, 140, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#005CEE")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E4E4E7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    body.append(t)
    body.append(Spacer(1, 12))
    body.append(Paragraph("Generated by PromoOS · promoos.com", small))
    doc.build(body)
    pdf = buf.getvalue()
    buf.close()
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


def register(api, db, now_iso, get_current_user):
    @api.get("/analytics/export")
    async def export_report(format: str = "csv", period: int = 30,
                            user: dict = Depends(get_current_user)):
        if format not in ("csv", "pdf"):
            raise HTTPException(400, "format must be csv or pdf")
        if period not in (7, 14, 30, 60, 90, 180, 365):
            period = 30
        rpt = await _export_report_rows(db, user["workspace_id"], period, now_iso)
        fname = f"promoos-report-{(rpt['workspace_name'] or 'workspace').lower().replace(' ','-')}-{period}d"
        if format == "csv":
            return _render_csv(rpt, fname)
        return _render_pdf(rpt, period, fname)
