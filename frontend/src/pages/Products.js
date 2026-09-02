import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Package, Plus, Trash2, Upload, Loader2, Image as ImageIcon } from "lucide-react";

const EMPTY = { name: "", description: "", price: 29, currency: "USD", image_url: "", stripe_price_id: "" };

function ProductForm({ open, onOpenChange, initial, onSubmit }) {
  const [f, setF] = useState(initial || EMPTY);
  const [uploading, setUploading] = useState(false);
  useEffect(() => { setF(initial || EMPTY); }, [initial, open]);

  const upload = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error("Max 5MB — please compress your image."); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const backend = process.env.REACT_APP_BACKEND_URL || "";
      setF((x) => ({ ...x, image_url: `${backend}${data.url}` }));
      toast.success("Image uploaded");
    } catch (e) { toast.error(apiError(e, "Upload failed")); }
    finally { setUploading(false); }
  };

  const submit = async () => {
    if (!f.name.trim()) { toast.error("Give the product a name"); return; }
    if (!f.price || f.price <= 0) { toast.error("Set a price"); return; }
    await onSubmit({ ...f, price: Number(f.price) });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-lg" data-testid="product-form-dialog">
        <DialogHeader><DialogTitle>{initial?.id ? "Edit product" : "New product"}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="rounded-lg border border-dashed border-[#27272A] p-4 flex items-center gap-4">
            <div className="w-24 h-24 rounded-md bg-[#0A0A0A] border border-[#27272A] flex items-center justify-center overflow-hidden flex-shrink-0">
              {f.image_url ? (
                <img src={f.image_url} alt="preview" className="w-full h-full object-cover" data-testid="product-image-preview" />
              ) : (
                <ImageIcon className="w-8 h-8 text-[#3F3F46]" />
              )}
            </div>
            <div className="flex-1">
              <Label className="text-xs text-[#A1A1AA]">Product image</Label>
              <div className="mt-1 flex items-center gap-2">
                <label className="btn-ghost rounded-md text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer"
                  data-testid="product-upload-btn">
                  {uploading ? <Loader2 className="w-3 h-3 spin" /> : <Upload className="w-3 h-3" />}
                  Upload
                  <input type="file" accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => upload(e.target.files?.[0])}
                    className="hidden" data-testid="product-upload-input" />
                </label>
                {f.image_url ? (
                  <button onClick={() => setF({ ...f, image_url: "" })}
                    className="text-[10px] text-[#71717A] hover:text-red-400">clear</button>
                ) : null}
              </div>
              <Input value={f.image_url || ""} onChange={(e) => setF({ ...f, image_url: e.target.value })}
                placeholder="or paste image URL"
                data-testid="product-image-url"
                className="mt-2 h-8 bg-[#0A0A0A] border-[#27272A] text-white text-xs font-mono" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Name</Label>
            <Input data-testid="product-name-input" value={f.name}
              onChange={(e) => setF({ ...f, name: e.target.value })}
              className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="Signature Hoodie" />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Description</Label>
            <Textarea rows={2} data-testid="product-description-input" value={f.description || ""}
              onChange={(e) => setF({ ...f, description: e.target.value })}
              className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="A short description shown on the storefront" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Price</Label>
              <Input type="number" step="0.01" data-testid="product-price-input" value={f.price}
                onChange={(e) => setF({ ...f, price: e.target.value })}
                className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Currency</Label>
              <Input value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })}
                className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="USD" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Stripe Price ID (optional)</Label>
            <Input value={f.stripe_price_id || ""}
              onChange={(e) => setF({ ...f, stripe_price_id: e.target.value })}
              placeholder="price_..." data-testid="product-stripe-price-id"
              className="mt-1 bg-[#0A0A0A] border-[#27272A] font-mono text-xs" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button data-testid="product-save-btn" className="btn-primary" onClick={submit}>Save product</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Products() {
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try { const { data } = await api.get("/products"); setProducts(data); }
    catch (e) { toast.error(apiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async (f) => {
    try {
      if (editing?.id) await api.put(`/products/${editing.id}`, f);
      else await api.post("/products", f);
      toast.success("Saved"); setOpen(false); setEditing(null); load();
    } catch (e) { toast.error(apiError(e)); }
  };
  const del = async (p) => {
    if (!window.confirm(`Delete "${p.name}"?`)) return;
    try { await api.delete(`/products/${p.id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="space-y-6" data-testid="products-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-3">
            <Package className="w-7 h-7 text-[#CCFF00]" /> Products
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Upload product images and set prices. Attach these to Funnel product blocks and coupons.
          </p>
        </div>
        <Button data-testid="products-new-btn" className="btn-primary gap-2 rounded-md"
          onClick={() => { setEditing(null); setOpen(true); }}>
          <Plus className="w-4 h-4" /> Add product
        </Button>
      </div>

      {products.length === 0 ? (
        <div className="text-center py-16 rounded-lg border border-dashed border-[#27272A]">
          <Package className="w-10 h-10 mx-auto text-[#3F3F46] mb-3" />
          <div className="font-bold">No products yet</div>
          <div className="text-sm text-[#71717A] mt-1">Upload your first product to start selling through funnels.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((p) => (
            <div key={p.id} className="rounded-lg overflow-hidden bg-[#141414] border border-[#27272A]"
              data-testid={`product-card-${p.id}`}>
              <div className="aspect-square bg-[#0A0A0A] flex items-center justify-center">
                {p.image_url ? (
                  <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                ) : (
                  <ImageIcon className="w-10 h-10 text-[#3F3F46]" />
                )}
              </div>
              <div className="p-3">
                <div className="font-bold text-sm truncate">{p.name}</div>
                <div className="text-xs text-[#71717A] mt-0.5">${p.price} {p.currency}</div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#27272A]">
                  <button onClick={() => { setEditing(p); setOpen(true); }}
                    className="text-xs text-[#A1A1AA] hover:text-white">Edit</button>
                  <button data-testid={`product-delete-${p.id}`} onClick={() => del(p)}
                    className="text-xs text-red-400 hover:text-red-300 p-1"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ProductForm open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditing(null); }}
        initial={editing} onSubmit={save} />
    </div>
  );
}
