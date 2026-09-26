import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext";

type LoginModalProps = {
  isOpen: boolean;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
            login_hint?: string;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: "standard" | "icon";
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "large" | "medium" | "small";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              shape?: "rectangular" | "pill" | "circle" | "square";
              logo_alignment?: "left" | "center";
              width?: number | string;
            }
          ) => void;
          prompt: (momentListener?: (notification: {
            isNotDisplayed: () => boolean;
            isSkippedMoment: () => boolean;
            getNotDisplayedReason: () => string;
            getSkippedReason: () => string;
          }) => void) => void;
          cancel: () => void;
        };
      };
    };
  }
}

let googleScriptPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) {
    return Promise.resolve();
  }

  if (googleScriptPromise) {
    return googleScriptPromise;
  }

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    ) as HTMLScriptElement | null;

    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(), { once: true });
      existingScript.addEventListener(
        "error",
        () => reject(new Error("Failed to load Google Sign-In")),
        { once: true }
      );
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Sign-In"));
    document.head.appendChild(script);
  });

  return googleScriptPromise;
}

export default function LoginModal({ isOpen }: LoginModalProps) {
  const { login, isLoading } = useAuth();

  const googleButtonRef = useRef<HTMLDivElement | null>(null);

  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const rememberedEmail = localStorage.getItem("easylearn_remember_email");

    if (rememberedEmail) {
      setEmail(rememberedEmail);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;

    async function setupGoogleLogin() {
      try {
        setError("");

        const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

        if (!clientId) {
          throw new Error("Google login is not configured. Missing VITE_GOOGLE_CLIENT_ID.");
        }

        await loadGoogleScript();

        if (cancelled) return;

        if (!window.google?.accounts?.id || !googleButtonRef.current) {
          throw new Error("Google login is not ready yet.");
        }

        const cleanEmail = email.trim().toLowerCase();

        window.google.accounts.id.initialize({
          client_id: clientId,
          login_hint: cleanEmail || undefined,
          auto_select: false,
          cancel_on_tap_outside: false,
          callback: async (response: { credential?: string }) => {
            try {
              setError("");

              const credential = response.credential;

              if (!credential) {
                throw new Error("Google did not return a login token.");
              }

              await login(credential);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Login failed");
            }
          },
        });

        googleButtonRef.current.innerHTML = "";

        window.google.accounts.id.renderButton(googleButtonRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
          logo_alignment: "left",
          width: 400,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load Google login");
      }
    }

    setupGoogleLogin();

    return () => {
      cancelled = true;

      if (window.google?.accounts?.id) {
        window.google.accounts.id.cancel();
      }
    };
  }, [isOpen, login]);

  async function handleBlueSignIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    try {
      setError("");

      const cleanEmail = email.trim().toLowerCase();

      if (!cleanEmail) {
        throw new Error("Please enter your email address.");
      }

      localStorage.setItem("easylearn_remember_email", cleanEmail);

      await loadGoogleScript();

      if (!window.google?.accounts?.id) {
        throw new Error("Google login is not ready yet.");
      }

      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

      if (!clientId) {
        throw new Error("Google login is not configured. Missing VITE_GOOGLE_CLIENT_ID.");
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        login_hint: cleanEmail,
        auto_select: false,
        cancel_on_tap_outside: false,
        callback: async (response: { credential?: string }) => {
          try {
            setError("");

            const credential = response.credential;

            if (!credential) {
              throw new Error("Google did not return a login token.");
            }

            await login(credential);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
          }
        },
      });

      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          setError("Google popup was blocked/skipped. Please click the Google button below.");
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  if (!isOpen) return null;

  return (
    <div className="login-page-shell">
      <div className="login-card">
        <div className="login-header">
          <p>Please enter your details</p>
          <h1>Welcome back</h1>
        </div>

        <form className="login-form" onSubmit={handleBlueSignIn}>
          <input
            className="login-input"
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />

          <button
            className="primary-login-button"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="google-button-wrap">
          <div ref={googleButtonRef} className="google-button-slot" />
        </div>

        {error ? <div className="login-modal-error">{error}</div> : null}
      </div>
    </div>
  );
}