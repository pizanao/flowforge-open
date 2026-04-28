import {
  createElement,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const AuthContext = createContext(null);

const TOKEN_KEY = "flowforge_token";
const REFRESH_KEY = "flowforge_refresh";
const USER_KEY = "flowforge_user";
const OAUTH_PROVIDER_KEY = "flowforge_oauth_provider";
const OAUTH_STATE_KEY = "flowforge_oauth_state";
const OAUTH_REDIRECT_KEY = "flowforge_oauth_redirect_uri";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const GITHUB_CLIENT_ID = import.meta.env.VITE_GITHUB_CLIENT_ID || "";

function parseStoredUser() {
  const rawUser = localStorage.getItem(USER_KEY);
  if (!rawUser) return null;
  try {
    return JSON.parse(rawUser);
  } catch {
    return null;
  }
}

function persistAuth(payload) {
  localStorage.setItem(TOKEN_KEY, payload.access);
  localStorage.setItem(REFRESH_KEY, payload.refresh);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

function clearAuthStorage() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

function authErrorMessage(status, fallback) {
  if (status === 403) return "Email não autorizado.";
  if (status === 401) return "Credenciais inválidas.";
  return fallback || "Falha na autenticação.";
}

async function postAuth(endpoint, body = {}) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    const error = new Error(authErrorMessage(response.status, payload.detail));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function redirectUri() {
  return window.location.origin;
}

function rememberOAuth(provider) {
  const state = `${provider}:${crypto.randomUUID()}`;
  const uri = redirectUri();
  sessionStorage.setItem(OAUTH_PROVIDER_KEY, provider);
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
  sessionStorage.setItem(OAUTH_REDIRECT_KEY, uri);
  return { state, redirectUri: uri };
}

export function getPendingOAuthContext() {
  return {
    provider: sessionStorage.getItem(OAUTH_PROVIDER_KEY) || "",
    state: sessionStorage.getItem(OAUTH_STATE_KEY) || "",
    redirectUri: sessionStorage.getItem(OAUTH_REDIRECT_KEY) || redirectUri(),
  };
}

export function clearPendingOAuthContext() {
  sessionStorage.removeItem(OAUTH_PROVIDER_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
  sessionStorage.removeItem(OAUTH_REDIRECT_KEY);
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [refresh, setRefresh] = useState(() => localStorage.getItem(REFRESH_KEY) || "");
  const [user, setUser] = useState(() => parseStoredUser());

  useEffect(() => {
    const syncAuth = () => {
      setToken(localStorage.getItem(TOKEN_KEY) || "");
      setRefresh(localStorage.getItem(REFRESH_KEY) || "");
      setUser(parseStoredUser());
    };

    window.addEventListener("storage", syncAuth);
    return () => window.removeEventListener("storage", syncAuth);
  }, []);

  const applyAuth = (payload) => {
    persistAuth(payload);
    setToken(payload.access);
    setRefresh(payload.refresh);
    setUser(payload.user);
  };

  const login = async (email, password) => {
    const payload = await postAuth("/api/auth/login/", { email, password });
    applyAuth(payload);
    return payload;
  };

  const loginWithGoogle = async (code, oauthRedirectUri = redirectUri()) => {
    const payload = await postAuth("/api/auth/google/", {
      code,
      redirect_uri: oauthRedirectUri,
    });
    applyAuth(payload);
    return payload;
  };

  const loginWithGitHub = async (code, oauthRedirectUri = redirectUri()) => {
    const payload = await postAuth("/api/auth/github/", {
      code,
      redirect_uri: oauthRedirectUri,
    });
    applyAuth(payload);
    return payload;
  };

  const beginGoogleOAuth = () => {
    if (!GOOGLE_CLIENT_ID) {
      throw new Error("Google OAuth não está configurado.");
    }

    const oauth = rememberOAuth("google");
    const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    url.searchParams.set("client_id", GOOGLE_CLIENT_ID);
    url.searchParams.set("redirect_uri", oauth.redirectUri);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", "openid email profile");
    url.searchParams.set("state", oauth.state);
    url.searchParams.set("access_type", "offline");
    url.searchParams.set("prompt", "consent");
    window.location.assign(url.toString());
  };

  const beginGitHubOAuth = () => {
    if (!GITHUB_CLIENT_ID) {
      throw new Error("GitHub OAuth não está configurado.");
    }

    const oauth = rememberOAuth("github");
    const url = new URL("https://github.com/login/oauth/authorize");
    url.searchParams.set("client_id", GITHUB_CLIENT_ID);
    url.searchParams.set("redirect_uri", oauth.redirectUri);
    url.searchParams.set("scope", "read:user user:email");
    url.searchParams.set("state", oauth.state);
    window.location.assign(url.toString());
  };

  const logout = () => {
    clearPendingOAuthContext();
    clearAuthStorage();
    setToken("");
    setRefresh("");
    setUser(null);
  };

  const value = useMemo(() => ({
    user,
    token,
    refresh,
    login,
    logout,
    loginWithGoogle,
    loginWithGitHub,
    beginGoogleOAuth,
    beginGitHubOAuth,
    isAuthenticated: Boolean(token),
    oauthEnabled: {
      google: Boolean(GOOGLE_CLIENT_ID),
      github: Boolean(GITHUB_CLIENT_ID),
    },
  }), [refresh, token, user]);

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  }
  return context;
}
