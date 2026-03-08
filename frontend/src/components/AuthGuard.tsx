import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getToken } from "@/lib/api";

interface AuthGuardProps {
  children: ReactNode;
}

const AuthGuard = ({ children }: AuthGuardProps) => {
  const token = getToken();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

export default AuthGuard;
