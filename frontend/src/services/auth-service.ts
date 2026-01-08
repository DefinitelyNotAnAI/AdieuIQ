/**
 * MSAL authentication service for Azure AD integration.
 * Constitutional Principle II: Security & Identity
 */

import {
  PublicClientApplication,
  Configuration,
  AuthenticationResult,
  AccountInfo,
  InteractionRequiredAuthError,
} from '@azure/msal-browser';

// MSAL configuration
const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_AD_CLIENT_ID || '',
    authority: `https://login.microsoftonline.com/${
      import.meta.env.VITE_AZURE_AD_TENANT_ID || 'common'
    }`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
};

// Initialize MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

// Login scopes
const loginRequest = {
  scopes: ['api://adieuiq/Customers.Read', 'api://adieuiq/Recommendations.Generate'],
};

/**
 * Initialize MSAL - call before rendering app
 */
export async function initializeMsal(): Promise<void> {
  await msalInstance.initialize();
  await msalInstance.handleRedirectPromise();
}

/**
 * Sign in user with redirect
 */
export async function signIn(): Promise<void> {
  try {
    await msalInstance.loginRedirect(loginRequest);
  } catch (error) {
    console.error('Sign in failed:', error);
    throw error;
  }
}

/**
 * Sign in user with popup
 */
export async function signInPopup(): Promise<AuthenticationResult> {
  try {
    return await msalInstance.loginPopup(loginRequest);
  } catch (error) {
    console.error('Sign in popup failed:', error);
    throw error;
  }
}

/**
 * Sign out user
 */
export async function signOut(): Promise<void> {
  const account = msalInstance.getActiveAccount();
  if (account) {
    await msalInstance.logoutRedirect({
      account,
    });
  }
}

/**
 * Get current authenticated account
 */
export function getCurrentAccount(): AccountInfo | null {
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) {
    return null;
  }
  return msalInstance.getActiveAccount() || accounts[0];
}

/**
 * Acquire access token silently (with fallback to interactive)
 */
export async function acquireToken(): Promise<string> {
  const account = getCurrentAccount();
  
  if (!account) {
    throw new Error('No active account. Please sign in.');
  }

  try {
    // Try silent token acquisition
    const response = await msalInstance.acquireTokenSilent({
      ...loginRequest,
      account,
    });
    return response.accessToken;
  } catch (error) {
    // If silent acquisition fails, fallback to interactive
    if (error instanceof InteractionRequiredAuthError) {
      const response = await msalInstance.acquireTokenPopup(loginRequest);
      return response.accessToken;
    }
    throw error;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getCurrentAccount() !== null;
}

/**
 * Get user roles from token claims
 */
export function getUserRoles(): string[] {
  const account = getCurrentAccount();
  if (!account || !account.idTokenClaims) {
    return [];
  }
  return (account.idTokenClaims as any).roles || [];
}

/**
 * Check if user has specific role
 */
export function hasRole(role: string): boolean {
  return getUserRoles().includes(role);
}
