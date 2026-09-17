import "@/App.css";
import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Coupons from "@/pages/Coupons";
import CouponEditor from "@/pages/CouponEditor";
import CouponDetail from "@/pages/CouponDetail";
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";
import Placeholder from "@/pages/Placeholder";
import PublicCoupon from "@/pages/PublicCoupon";
import Rewards from "@/pages/Rewards";
import Calendar from "@/pages/Calendar";
import GiftCards from "@/pages/GiftCards";
import Wallet from "@/pages/Wallet";
import Campaigns from "@/pages/Campaigns";
import Customers from "@/pages/Customers";
import DesignStudio from "@/pages/DesignStudio";
import Integrations from "@/pages/Integrations";
import Admin from "@/pages/Admin";
import CouponLibrary from "@/pages/CouponLibrary";
import Reviews from "@/pages/Reviews";
import Products from "@/pages/Products";
import Sequences from "@/pages/Sequences";
import { PrivacyPolicy, TermsOfUse } from "@/pages/Legal";
import Pricing from "@/pages/Pricing";
import { BillingSuccess, BillingCancel } from "@/pages/BillingResult";
import GiftCardStudio from "@/pages/GiftCardStudio";
import { Funnels, FunnelEditor } from "@/pages/Funnels";
import PublicFunnel from "@/pages/PublicFunnel";
import QRStudio from "@/pages/QRStudio";
import Landing from "@/pages/Landing";
import { ForgotPassword, ResetPassword } from "@/pages/ResetPassword";
import Newsletters from "@/pages/Newsletters";
import NewsletterDashboard from "@/pages/NewsletterDashboard";
import NewsletterPostEditor from "@/pages/NewsletterPostEditor";
import PublicNewsletter from "@/pages/PublicNewsletter";
import PublicNewsletterPost from "@/pages/PublicNewsletterPost";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-[#0A0A0A]">
        <div className="w-8 h-8 rounded-full border-2 border-[#27272A] border-t-[#CCFF00] spin" />
      </div>
    );
  return user ? children : <Navigate to="/login" replace />;
}

function Home() {
  // Public homepage for visitors, protected app shell for logged-in users.
  const { user, loading } = useAuth();
  const path = typeof window !== "undefined" ? window.location.pathname : "/";
  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-[#0A0A0A]">
        <div className="w-8 h-8 rounded-full border-2 border-[#27272A] border-t-[#CCFF00] spin" />
      </div>
    );
  if (user) return <Layout />;
  // Logged-out — show Landing only at exact "/"; otherwise route through Protected to force login.
  if (path === "/" || path === "") return <Landing />;
  return <Navigate to="/login" replace />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster theme="dark" position="top-right" />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/c/:code" element={<PublicCoupon />} />
          <Route path="/f/:slug" element={<PublicFunnel />} />
          <Route path="/n/:slug" element={<PublicNewsletter />} />
          <Route path="/n/:slug/p/:postSlug" element={<PublicNewsletterPost />} />
          <Route path="/wallet/:token" element={<Wallet />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfUse />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/billing/success" element={<BillingSuccess />} />
          <Route path="/billing/cancel" element={<BillingCancel />} />
          <Route path="/" element={<Home />}>
            <Route index element={<Dashboard />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="coupons" element={<Coupons />} />
            <Route path="coupons/new" element={<CouponEditor />} />
            <Route path="coupons/:id/edit" element={<CouponEditor />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="gift-cards" element={<GiftCards />} />
            <Route path="gift-cards/studio" element={<GiftCardStudio />} />
            <Route path="funnels" element={<Funnels />} />
            <Route path="funnels/:id/edit" element={<FunnelEditor />} />
            <Route path="qr" element={<QRStudio />} />
            <Route path="coupons/:id" element={<CouponDetail />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
            <Route path="campaigns" element={<Campaigns />} />
            <Route path="customers" element={<Customers />} />
            <Route path="rewards" element={<Rewards />} />
            <Route path="design" element={<DesignStudio />} />
            <Route path="integrations" element={<Integrations />} />
            <Route path="admin" element={<Admin />} />
            <Route path="library" element={<CouponLibrary />} />
            <Route path="reviews" element={<Reviews />} />
            <Route path="products" element={<Products />} />
            <Route path="sequences" element={<Sequences />} />
            <Route path="newsletters" element={<Newsletters />} />
            <Route path="newsletters/:pubId" element={<NewsletterDashboard />} />
            <Route path="newsletters/:pubId/posts/:postId" element={<NewsletterPostEditor />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
