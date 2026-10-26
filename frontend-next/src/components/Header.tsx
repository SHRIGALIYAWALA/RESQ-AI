"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface HeaderProps {
  wsConnected: boolean;
}

export function Header({ wsConnected }: HeaderProps) {
  const [loginOpen, setLoginOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/auth/session`, { credentials: "include" })
      .then((response) => response.json())
      .then((session) => setLoggedIn(Boolean(session.authenticated)))
      .catch(() => setLoggedIn(false));
  }, []);

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/token`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await response.json();
      if (!response.ok) {
        setAuthError(body.detail || "Sign in failed.");
        return;
      }
      setLoggedIn(true);
      setLoginOpen(false);
      window.location.reload();
    } catch {
      setAuthError("Unable to reach the authentication service.");
    }
  };

  const logout = () => {
    fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" })
      .then(() => {
        setLoggedIn(false);
        window.location.reload();
      })
      .catch(() => setAuthError("Unable to sign out."));
  };

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between border-b border-cyan-500/30 bg-panel/95 px-6 py-3.5 shadow-lg backdrop-blur-md">
      <Link href="/" className="text-xl font-extrabold tracking-widest text-cyan-300 drop-shadow-[0_0_15px_rgba(0,243,255,0.35)]">
        RESQ-AI
      </Link>
      <nav className="flex gap-4">
        <Link href="/" className="rounded-md border border-cyan-400/40 bg-cyan-400/10 px-3.5 py-1.5 text-sm font-semibold text-cyan-400">
          Command Center
        </Link>
        <Link href="/buildings" className="rounded-md px-3.5 py-1.5 text-sm font-semibold text-muted hover:text-cyan-400">
          Digital Twin
        </Link>
        <Link href="/incident" className="rounded-md px-3.5 py-1.5 text-sm font-semibold text-muted hover:text-cyan-400">
          Report Emergency
        </Link>
      </nav>
      <div className="flex items-center gap-3">
        <div className={`h-2.5 w-2.5 rounded-full ${wsConnected ? "animate-pulse bg-safe" : "bg-warning"}`} />
        <span className={`font-mono text-xs ${wsConnected ? "text-safe" : "text-warning"}`}>
          {wsConnected ? "LIVE WS ONLINE" : "WS RECONNECTING"}
        </span>
        {loggedIn ? (
          <button type="button" onClick={logout} className="rounded border border-white/20 px-2 py-1 text-xs text-muted">Sign out</button>
        ) : (
          <button type="button" onClick={() => setLoginOpen((open) => !open)} className="rounded border border-cyan-400/40 px-2 py-1 text-xs text-cyan-300">Sign in</button>
        )}
      </div>
      {loginOpen && (
        <form onSubmit={login} className="absolute right-4 top-full mt-2 grid w-72 gap-2 rounded border border-cyan-500/30 bg-panel p-3 shadow-xl">
          <label className="grid gap-1 text-xs text-muted">
            Username
            <input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} className="rounded border border-white/20 bg-black px-2 py-1 text-white" />
          </label>
          <label className="grid gap-1 text-xs text-muted">
            Password
            <input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="rounded border border-white/20 bg-black px-2 py-1 text-white" />
          </label>
          {authError && <p role="alert" className="text-xs text-danger">{authError}</p>}
          <button type="submit" className="rounded border border-cyan-400/40 px-2 py-1 text-xs text-cyan-300">Sign in</button>
        </form>
      )}
    </header>
  );
}
