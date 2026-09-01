function hexToRgb(hex){let h=hex.replace('#','');if(h.length===3)h=h.split('').map(c=>c+c).join('');const n=parseInt(h,16);return {r:(n>>16)&255,g:(n>>8)&255,b:n&255};}
function lum({r,g,b}){const ch=c=>{const v=c/255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return 0.2126*ch(r)+0.7152*ch(g)+0.0722*ch(b);}
function ratio(a,b){const l1=lum(hexToRgb(a)),l2=lum(hexToRgb(b));const hi=Math.max(l1,l2),lo=Math.min(l1,l2);return (hi+0.05)/(lo+0.05);}
function impl(bg){return lum(hexToRgb(bg))>0.55?'#0A0A0A':'#FFFFFF';}
const colors=['#F97316','#FFFFFF','#0A0A0A','#CCFF00','#6366F1','#22C55E','#EAB308','#FF0000','#888888','#7F7F7F','#00BFA5'];
for(const c of colors){
  const chosen=impl(c);
  const rW=ratio(c,'#FFFFFF'), rB=ratio(c,'#0A0A0A');
  const best=rW>rB?'#FFFFFF':'#0A0A0A';
  console.log(`${c} L=${lum(hexToRgb(c)).toFixed(3)} chosen=${chosen} ratio=${ratio(c,chosen).toFixed(2)} | white=${rW.toFixed(2)} dark=${rB.toFixed(2)} best=${best} ${ratio(c,chosen)<4.5?'*** FAILS 4.5:1':'ok'} ${chosen!==best?'<< SUBOPTIMAL':''}`);
}
