"""QR Code Studio — build colorful, styled QR codes for URL, phone, SMS, email, WiFi, vCard, text.
Supports style variants (square/rounded/circle/gapped/vertical-bars/horizontal-bars),
color masks (solid, radial-gradient, horizontal-gradient, vertical-gradient),
optional center logo overlay, per-QR error correction level.
"""
import io, base64, re, uuid
from typing import Optional
from fastapi import HTTPException, Depends, Response
from pydantic import BaseModel

import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer, RoundedModuleDrawer, CircleModuleDrawer,
    GappedSquareModuleDrawer, VerticalBarsDrawer, HorizontalBarsDrawer,
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask, RadialGradiantColorMask,
    HorizontalGradiantColorMask, VerticalGradiantColorMask,
)
from PIL import Image


CONTENT_TYPES = ["url", "text", "phone", "sms", "email", "wifi", "vcard"]
STYLES = ["square", "rounded", "circle", "gapped", "vertical_bars", "horizontal_bars"]
MASKS = ["solid", "radial", "horizontal", "vertical"]
EC_LEVELS = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}


def _hex_to_rgb(hex_color: str, default=(0, 0, 0)) -> tuple:
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3: h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def _build_payload(content_type: str, data: dict) -> str:
    ct = (content_type or "url").lower()
    if ct == "url":
        v = (data.get("url") or "").strip()
        if not v: raise HTTPException(400, "url is required")
        if not v.startswith(("http://", "https://")): v = "https://" + v
        return v
    if ct == "text":
        return data.get("text") or ""
    if ct == "phone":
        return f"tel:{re.sub(r'[^0-9+]', '', data.get('phone') or '')}"
    if ct == "sms":
        num = re.sub(r"[^0-9+]", "", data.get("phone") or "")
        body = (data.get("message") or "").replace("\n", " ")
        return f"SMSTO:{num}:{body}"
    if ct == "email":
        addr = (data.get("email") or "").strip()
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        parts = []
        if subject: parts.append(f"subject={subject}")
        if body: parts.append(f"body={body}")
        qs = ("?" + "&".join(parts)) if parts else ""
        return f"mailto:{addr}{qs}"
    if ct == "wifi":
        ssid = data.get("ssid") or ""
        pw = data.get("password") or ""
        enc = (data.get("encryption") or "WPA").upper()
        hidden = "true" if data.get("hidden") else "false"
        return f"WIFI:T:{enc};S:{ssid};P:{pw};H:{hidden};;"
    if ct == "vcard":
        name = data.get("name") or ""
        org = data.get("org") or ""
        phone = data.get("phone") or ""
        email = data.get("email") or ""
        url = data.get("url") or ""
        return (
            "BEGIN:VCARD\nVERSION:3.0\n"
            f"FN:{name}\n"
            f"ORG:{org}\n"
            f"TEL:{phone}\n"
            f"EMAIL:{email}\n"
            f"URL:{url}\n"
            "END:VCARD"
        )
    raise HTTPException(400, f"Unknown content_type: {ct}")


def _drawer(style: str):
    return {
        "square": SquareModuleDrawer(),
        "rounded": RoundedModuleDrawer(radius_ratio=1.0),
        "circle": CircleModuleDrawer(),
        "gapped": GappedSquareModuleDrawer(),
        "vertical_bars": VerticalBarsDrawer(),
        "horizontal_bars": HorizontalBarsDrawer(),
    }.get(style, SquareModuleDrawer())


def _color_mask(mask: str, front: tuple, back: tuple, edge: tuple):
    if mask == "radial":
        return RadialGradiantColorMask(back_color=back, center_color=front, edge_color=edge)
    if mask == "horizontal":
        return HorizontalGradiantColorMask(back_color=back, left_color=front, right_color=edge)
    if mask == "vertical":
        return VerticalGradiantColorMask(back_color=back, top_color=front, bottom_color=edge)
    return SolidFillColorMask(back_color=back, front_color=front)


def _render_qr(payload: str, style: str, mask: str, front_color: str, back_color: str,
               edge_color: str, ec: str, box_size: int, border: int,
               logo_bytes: Optional[bytes] = None) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=EC_LEVELS.get(ec.upper(), ERROR_CORRECT_H),
        box_size=max(4, min(40, int(box_size or 16))),
        border=max(1, min(8, int(border or 4))),
    )
    qr.add_data(payload)
    qr.make(fit=True)
    front = _hex_to_rgb(front_color, (10, 10, 10))
    back = _hex_to_rgb(back_color, (255, 255, 255))
    edge = _hex_to_rgb(edge_color, front)
    img_kwargs = {
        "image_factory": StyledPilImage,
        "module_drawer": _drawer(style),
        "color_mask": _color_mask(mask, front, back, edge),
    }
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            img_kwargs["embeded_image"] = logo
        except Exception:
            pass
    img = qr.make_image(**img_kwargs)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def register(api, db, now_iso, get_current_user, require_writer):

    class QRRequest(BaseModel):
        content_type: str = "url"
        data: dict = {}
        style: str = "square"
        color_mask: str = "solid"
        front_color: str = "#0A0A0A"
        back_color: str = "#FFFFFF"
        edge_color: str = "#005CEE"
        error_correction: str = "H"
        box_size: int = 16
        border: int = 4
        logo_upload_id: Optional[str] = None
        save: bool = False
        label: Optional[str] = None

    @api.get("/qr/options")
    async def qr_options():
        return {
            "content_types": CONTENT_TYPES,
            "styles": STYLES,
            "color_masks": MASKS,
            "error_correction": list(EC_LEVELS.keys()),
            "presets": [
                {"id": "neon-lime",   "front_color": "#0A0A0A", "back_color": "#FFFFFF", "edge_color": "#CCFF00", "style": "rounded", "color_mask": "radial"},
                {"id": "electric",    "front_color": "#005CEE", "back_color": "#FFFFFF", "edge_color": "#00F5FF", "style": "circle",  "color_mask": "horizontal"},
                {"id": "sunset",      "front_color": "#FF006E", "back_color": "#FFFFFF", "edge_color": "#FFBE0B", "style": "rounded", "color_mask": "vertical"},
                {"id": "midnight",    "front_color": "#CCFF00", "back_color": "#0A0A0A", "edge_color": "#00F5FF", "style": "rounded", "color_mask": "radial"},
                {"id": "champagne",   "front_color": "#8B6914", "back_color": "#FAF7F0", "edge_color": "#D4AF37", "style": "gapped",  "color_mask": "solid"},
                {"id": "monochrome",  "front_color": "#0A0A0A", "back_color": "#FFFFFF", "edge_color": "#0A0A0A", "style": "square",  "color_mask": "solid"},
                {"id": "forest",      "front_color": "#04231A", "back_color": "#F1FAEE", "edge_color": "#0F5E43", "style": "circle",  "color_mask": "radial"},
                {"id": "royal-blue",  "front_color": "#0F172A", "back_color": "#FFFFFF", "edge_color": "#3A86FF", "style": "vertical_bars", "color_mask": "vertical"},
                {"id": "berry",       "front_color": "#7209B7", "back_color": "#FFFFFF", "edge_color": "#F72585", "style": "rounded", "color_mask": "horizontal"},
                {"id": "print-safe",  "front_color": "#000000", "back_color": "#FFFFFF", "edge_color": "#000000", "style": "square",  "color_mask": "solid"},
            ],
        }

    @api.post("/qr/preview")
    async def qr_preview(body: QRRequest, user: dict = Depends(get_current_user)):
        payload = _build_payload(body.content_type, body.data or {})
        logo_bytes = None
        if body.logo_upload_id:
            up = await db.uploads.find_one(
                {"id": body.logo_upload_id, "workspace_id": user["workspace_id"], "is_deleted": False},
                {"_id": 0})
            if up:
                try:
                    from routers.billing import register_extras  # noqa: F401
                    # Reuse storage helper by fetching via api uploads endpoint would be circular; call storage directly.
                    import os, requests
                    STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "https://integrations.emergentagent.com").rstrip("/")
                    STORAGE_URL = STORAGE_BASE + "/objstore/api/v1/storage"
                    r = requests.post(f"{STORAGE_URL}/init",
                                      json={"emergent_key": os.environ.get("EMERGENT_LLM_KEY")}, timeout=15)
                    if r.ok:
                        sk = r.json().get("storage_key")
                        rr = requests.get(f"{STORAGE_URL}/objects/{up['storage_path']}",
                                          headers={"X-Storage-Key": sk}, timeout=30)
                        if rr.ok: logo_bytes = rr.content
                except Exception:
                    logo_bytes = None
        try:
            png = _render_qr(payload, body.style, body.color_mask, body.front_color,
                             body.back_color, body.edge_color, body.error_correction,
                             body.box_size, body.border, logo_bytes)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"QR render failed: {e}")
        b64 = base64.b64encode(png).decode()
        result = {
            "content_type": body.content_type,
            "payload": payload,
            "image_data_url": f"data:image/png;base64,{b64}",
            "size_bytes": len(png),
        }
        if body.save:
            require_writer(user)
            doc = {
                "id": str(uuid.uuid4()),
                "workspace_id": user["workspace_id"],
                "created_by": user["id"],
                "label": body.label or f"{body.content_type.upper()} · {payload[:40]}",
                "content_type": body.content_type,
                "payload": payload,
                "style": body.style,
                "color_mask": body.color_mask,
                "front_color": body.front_color,
                "back_color": body.back_color,
                "edge_color": body.edge_color,
                "error_correction": body.error_correction,
                "box_size": body.box_size,
                "border": body.border,
                "logo_upload_id": body.logo_upload_id,
                "created_at": now_iso(),
            }
            await db.qr_codes.insert_one({**doc})
            result["saved_id"] = doc["id"]
        return result

    @api.post("/qr/download")
    async def qr_download(body: QRRequest, user: dict = Depends(get_current_user)):
        payload = _build_payload(body.content_type, body.data or {})
        try:
            png = _render_qr(payload, body.style, body.color_mask, body.front_color,
                             body.back_color, body.edge_color, body.error_correction,
                             body.box_size, body.border, None)
        except Exception as e:
            raise HTTPException(500, f"QR render failed: {e}")
        fname = (body.label or body.content_type).replace(" ", "-").lower()[:40] or "qr"
        return Response(content=png, media_type="image/png",
                        headers={"Content-Disposition": f'attachment; filename="{fname}.png"'})

    @api.get("/qr/saved")
    async def qr_list(user: dict = Depends(get_current_user)):
        docs = await db.qr_codes.find(
            {"workspace_id": user["workspace_id"]},
            {"_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.delete("/qr/saved/{qid}")
    async def qr_delete(qid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.qr_codes.delete_one({"id": qid, "workspace_id": user["workspace_id"]})
        if r.deleted_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True}
