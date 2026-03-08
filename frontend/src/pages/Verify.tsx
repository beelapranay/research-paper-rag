import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { setToken } from "@/lib/api";

const Verify = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("Verifying your email...");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("Missing verification token.");
      return;
    }

    const run = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/auth/verify?token=${encodeURIComponent(token)}`);
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Verification failed");
        }
        const data = await res.json();
        setToken(data.access_token);
        setStatus("Verified! Redirecting...");
        setTimeout(() => navigate("/"), 800);
      } catch (e: any) {
        setStatus(e.message || "Verification failed.");
      }
    };

    run();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center space-y-3">
        <h1 className="font-display text-2xl font-semibold">Email Verification</h1>
        <p className="text-sm text-muted-foreground">{status}</p>
      </div>
    </div>
  );
};

export default Verify;
