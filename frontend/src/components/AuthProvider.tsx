"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getKeycloak } from "@/lib/keycloak";

type AuthState = {
  username: string | null;
  roles: string[]; // for showing or hiding UI only; the backend enforces permissions
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

// keycloak-js may only be initialised once, and React dev mode runs effects twice.
let initPromise: Promise<boolean> | null = null;
function initKeycloak(): Promise<boolean> {
  if (!initPromise) {
    initPromise = getKeycloak().init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    });
  }
  return initPromise;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    initKeycloak()
      .then((authenticated) => (authenticated ? setReady(true) : setFailed(true)))
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return <p className="p-8">Could not reach the sign-in service. Is Keycloak running?</p>;
  }
  if (!ready) {
    return <p className="p-8">Signing in…</p>;
  }

  const keycloak = getKeycloak();
  const value: AuthState = {
    username: keycloak.tokenParsed?.preferred_username ?? null,
    roles: keycloak.tokenParsed?.realm_access?.roles ?? [],
    logout: () => keycloak.logout({ redirectUri: window.location.origin }),
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}