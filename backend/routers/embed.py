"""Embed widget — public JS renderers for coupon embeds on external sites.

Variants: inline (card), popup, bar, wheel, wallet.
Endpoint: GET /api/embed/coupon.js?variant=<name>
"""
import os
from fastapi import Request, Response


# Common bootstrap that hydrates coupon data + brand colors from the public API
_EMBED_BOOTSTRAP = """
var API="__API__";
function poFetch(code, ref, cb){
  fetch(API+'/api/public/coupons/'+encodeURIComponent(code)+(ref?('?ref='+encodeURIComponent(ref)):''))
    .then(function(r){return r.ok?r.json():Promise.reject(r)})
    .then(cb).catch(function(){});
}
function poCopy(text, btn){
  navigator.clipboard.writeText(text).then(function(){
    var t=btn.textContent; btn.textContent='Copied!'; setTimeout(function(){btn.textContent=t;},1500);
  }).catch(function(){});
}
"""

_RENDERERS = {
    # Inline card (default)
    "inline": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase();
  var ref=s.getAttribute('data-ref')||'';
  if(!code) return;
  var host=document.createElement('div'); s.parentNode.insertBefore(host,s);
  poFetch(code, ref, function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code)+(ref?('?ref='+encodeURIComponent(ref)):'');
    host.innerHTML='<div style="font-family:Helvetica,Arial,sans-serif;max-width:420px;padding:20px;border-radius:14px;background:#0A0A0A;color:#fff;border:1px solid #27272A;box-shadow:0 10px 30px rgba(0,0,0,.35)">'
      +'<div style="font-size:11px;letter-spacing:.12em;color:'+accent+';text-transform:uppercase;font-weight:700">'+d.brand.name+'</div>'
      +'<div style="font-size:22px;font-weight:800;line-height:1.15;margin:8px 0 6px">'+d.headline+'</div>'
      +'<div style="font-size:13px;color:#A1A1AA;margin-bottom:14px">'+d.description+'</div>'
      +'<div style="display:flex;gap:10px"><div style="flex:1;padding:12px 14px;border:2px dashed '+primary+';border-radius:10px;font-family:monospace;font-weight:700;font-size:18px;color:'+primary+';letter-spacing:2px;text-align:center">'+d.code+'</div>'
      +'<button data-c style="background:'+accent+';color:#0A0A0A;border:0;padding:12px 14px;border-radius:10px;font-weight:700;cursor:pointer">Copy</button></div>'
      +'<a href="'+landing+'" target="_blank" rel="noopener" style="display:block;text-align:center;margin-top:14px;background:'+primary+';color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700">'+d.cta+'</a></div>';
    host.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
  });
});
""",

    # Full-screen popup
    "popup": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  var delay=parseInt(s.getAttribute('data-delay')||'2500',10);
  if(sessionStorage.getItem('promoos_seen_'+code)) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    setTimeout(function(){
      sessionStorage.setItem('promoos_seen_'+code,'1');
      var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
      var wrap=document.createElement('div');
      wrap.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:2147483647;display:flex;align-items:center;justify-content:center;font-family:Helvetica,Arial,sans-serif;padding:20px;animation:pop-fade .3s ease';
      wrap.innerHTML='<style>@keyframes pop-fade{from{opacity:0}to{opacity:1}}@keyframes pop-in{from{transform:scale(.9);opacity:0}to{transform:scale(1);opacity:1}}</style>'
        +'<div style="background:#0A0A0A;color:#fff;max-width:460px;width:100%;padding:32px;border-radius:20px;position:relative;text-align:center;border:1px solid #27272A;animation:pop-in .3s ease">'
        +'<button data-x style="position:absolute;top:12px;right:14px;background:transparent;border:0;color:#71717A;font-size:22px;cursor:pointer;line-height:1">×</button>'
        +'<div style="font-size:11px;letter-spacing:.12em;color:'+accent+';text-transform:uppercase;font-weight:700;margin-bottom:8px">'+d.brand.name+'</div>'
        +'<div style="font-size:28px;font-weight:900;line-height:1.1;margin-bottom:8px">'+d.headline+'</div>'
        +'<div style="font-size:14px;color:#A1A1AA;margin-bottom:20px">'+d.description+'</div>'
        +'<div style="padding:14px 16px;border:2px dashed '+primary+';border-radius:12px;font-family:monospace;font-weight:700;font-size:22px;color:'+primary+';letter-spacing:3px;margin-bottom:16px">'+d.code+'</div>'
        +'<button data-c style="background:'+primary+';color:#fff;border:0;padding:14px 24px;border-radius:12px;font-weight:700;cursor:pointer;font-size:15px;width:100%">'+d.cta+' — Copy code</button></div>';
      document.body.appendChild(wrap);
      wrap.querySelector('[data-x]').addEventListener('click',function(){wrap.remove()});
      wrap.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
      wrap.addEventListener('click',function(e){if(e.target===wrap)wrap.remove()});
    }, delay);
  });
});
""",

    # Top-bar
    "bar": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code);
    var bar=document.createElement('div');
    bar.style.cssText='position:fixed;top:0;left:0;right:0;background:linear-gradient(90deg,'+primary+','+accent+');color:#0A0A0A;padding:10px 18px;font-family:Helvetica,Arial,sans-serif;font-weight:700;font-size:14px;z-index:2147483646;display:flex;align-items:center;gap:12px;justify-content:center;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,.15)';
    bar.innerHTML='<span>'+d.headline+' — Code <span style="font-family:monospace;background:rgba(0,0,0,.15);padding:2px 8px;border-radius:4px">'+d.code+'</span></span>'
      +'<a href="'+landing+'" target="_blank" style="background:#0A0A0A;color:#fff;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:12px">'+d.cta+'</a>'
      +'<button data-x style="background:transparent;border:0;color:#0A0A0A;font-size:18px;cursor:pointer;padding:0 4px;line-height:1;opacity:.5">×</button>';
    document.body.appendChild(bar);
    bar.querySelector('[data-x]').addEventListener('click',function(){bar.remove()});
  });
});
""",

    # Spin-to-win wheel
    "wheel": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var slices=[d.discount_value+'%',Math.round(d.discount_value/2)+'%','Try again','5%',d.discount_value+'%','Free ship'];
    var wrap=document.createElement('div');
    wrap.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:2147483647;display:flex;align-items:center;justify-content:center;font-family:Helvetica,Arial,sans-serif;padding:20px';
    var W='<style>@keyframes spin{to{transform:rotate(var(--r))}}</style><div style="background:#0A0A0A;color:#fff;padding:32px;border-radius:20px;max-width:420px;width:100%;text-align:center;border:1px solid #27272A">';
    W+='<button data-x style="position:absolute;top:20px;right:20px;background:transparent;border:0;color:#fff;font-size:22px;cursor:pointer">×</button>';
    W+='<div style="font-size:22px;font-weight:900;margin-bottom:16px">Spin to Win</div>';
    W+='<div style="position:relative;width:260px;height:260px;margin:0 auto 20px"><div id="pw-wheel" style="width:100%;height:100%;border-radius:50%;background:conic-gradient('+primary+' 0 60deg,'+accent+' 60deg 120deg,'+primary+' 120deg 180deg,'+accent+' 180deg 240deg,'+primary+' 240deg 300deg,'+accent+' 300deg 360deg);transition:transform 4s cubic-bezier(.22,.9,.28,1);border:4px solid #fff;box-shadow:0 0 40px '+primary+'44"></div><div style="position:absolute;top:-6px;left:50%;transform:translateX(-50%);width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-top:20px solid #fff"></div></div>';
    W+='<button data-spin style="background:'+primary+';color:#fff;border:0;padding:14px 32px;border-radius:12px;font-weight:700;font-size:16px;cursor:pointer">SPIN</button>';
    W+='<div id="pw-out" style="margin-top:20px;min-height:80px"></div></div>';
    wrap.innerHTML=W; document.body.appendChild(wrap);
    var out=wrap.querySelector('#pw-out'), whl=wrap.querySelector('#pw-wheel'), btn=wrap.querySelector('[data-spin]');
    wrap.querySelector('[data-x]').addEventListener('click',function(){wrap.remove()});
    btn.addEventListener('click',function(){
      btn.disabled=true; btn.style.opacity='.5';
      var winSlice=0; var deg=1800+winSlice*60+30;
      whl.style.setProperty('--r',deg+'deg'); whl.style.animation='spin 4s cubic-bezier(.22,.9,.28,1) forwards';
      setTimeout(function(){
        out.innerHTML='<div style="font-size:18px;font-weight:800;color:'+accent+'">You won '+slices[winSlice]+' off!</div>'
          +'<div style="margin-top:8px;padding:10px;border:2px dashed '+primary+';border-radius:8px;font-family:monospace;font-weight:700;font-size:18px;color:'+primary+';letter-spacing:2px">'+d.code+'</div>'
          +'<button data-c style="margin-top:10px;background:'+accent+';color:#0A0A0A;border:0;padding:10px 20px;border-radius:8px;font-weight:700;cursor:pointer">Copy code</button>';
        out.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
      },4200);
    });
  });
});
""",

    # Floating wallet pill (bottom right)
    "wallet": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code);
    var pill=document.createElement('div');
    pill.style.cssText='position:fixed;bottom:20px;right:20px;z-index:2147483645;font-family:Helvetica,Arial,sans-serif;display:flex;flex-direction:column;align-items:flex-end;gap:8px';
    pill.innerHTML='<div id="pw-panel" style="display:none;background:#0A0A0A;color:#fff;padding:20px;border-radius:16px;border:1px solid #27272A;box-shadow:0 20px 40px rgba(0,0,0,.4);max-width:320px">'
      +'<div style="font-size:11px;letter-spacing:.1em;color:'+accent+';text-transform:uppercase;font-weight:700;margin-bottom:6px">'+d.brand.name+'</div>'
      +'<div style="font-size:16px;font-weight:800;line-height:1.15;margin-bottom:4px">'+d.headline+'</div>'
      +'<div style="font-size:12px;color:#A1A1AA;margin-bottom:12px">'+d.description+'</div>'
      +'<div style="padding:10px;border:2px dashed '+primary+';border-radius:8px;font-family:monospace;font-weight:700;color:'+primary+';text-align:center;letter-spacing:2px;margin-bottom:10px">'+d.code+'</div>'
      +'<div style="display:flex;gap:6px"><button data-c style="flex:1;background:'+accent+';color:#0A0A0A;border:0;padding:8px;border-radius:8px;font-weight:700;cursor:pointer;font-size:12px">Copy</button><a href="'+landing+'" target="_blank" style="flex:1;background:'+primary+';color:#fff;text-decoration:none;padding:8px;border-radius:8px;font-weight:700;text-align:center;font-size:12px">'+d.cta+'</a></div></div>'
      +'<button id="pw-toggle" style="background:'+primary+';color:#fff;border:0;padding:12px 18px;border-radius:99px;font-weight:700;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.3);display:flex;align-items:center;gap:8px;font-size:13px">🎁 '+d.discount_value+'% off available</button>';
    document.body.appendChild(pill);
    var panel=pill.querySelector('#pw-panel'), toggle=pill.querySelector('#pw-toggle');
    toggle.addEventListener('click',function(){panel.style.display=panel.style.display==='none'?'block':'none'});
    panel.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
  });
});
""",
}


def register(api):
    """Attach the /embed/coupon.js endpoint to the given APIRouter."""

    @api.get("/embed/coupon.js")
    async def embed_js(request: Request, variant: str = "inline"):
        """Embed script. Variants: inline (default card), popup, bar, wheel, wallet."""
        origin = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
        if not origin:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
            origin = f"{proto}://{host}"
        v = (variant or "inline").lower()
        if v not in _RENDERERS:
            v = "inline"
        js = _RENDERERS[v].replace("__API__", origin)
        return Response(
            content=js,
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=60"},
        )
