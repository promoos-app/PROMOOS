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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster theme="dark" position="top-right" />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/c/:code" element={<PublicCoupon />} />
          <Route path="/" element={<Protected><Layout /></Protected>}>
            <Route index element={<Dashboard />} />
            <Route path="coupons" element={<Coupons />} />
            <Route path="coupons/new" element={<CouponEditor />} />
            <Route path="coupons/:id/edit" element={<CouponEditor />} />
            <Route path="coupons/:id" element={<CouponDetail />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
            <Route path="campaigns" element={<Placeholder title="Campaigns" />} />
            <Route path="customers" element={<Placeholder title="Customers" />} />
            <Route path="rewards" element={<Placeholder title="Rewards" />} />
            <Route path="design" element={<Placeholder title="Design Studio" />} />
            <Route path="integrations" element={<Placeholder title="Integrations" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
