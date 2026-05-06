import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Routes protégées côté serveur.
 * La route /admin est bloquée si aucun cookie de session Supabase n'est présent.
 * Les autres pages protégées conservent leur guard client-side (ProtectedRoute).
 *
 * Note: une protection SSR complète de toutes les routes nécessite
 * la migration vers @supabase/ssr (cookies-based tokens).
 */
const ADMIN_PATHS = ['/admin'];

function hasSupabaseSession(request: NextRequest): boolean {
  const cookies = request.cookies;
  // Supabase stocke la session dans un cookie dont le nom commence par "sb-"
  // et se termine par "-auth-token" (ex: sb-abc123-auth-token)
  for (const [name] of cookies) {
    if (name.startsWith('sb-') && name.endsWith('-auth-token')) {
      return true;
    }
  }
  // Fallback: vérification du cookie générique (clients anciens)
  if (cookies.has('supabase-auth-token') || cookies.has('supabase.auth.token')) {
    return true;
  }
  return false;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protection de /admin côté serveur
  if (ADMIN_PATHS.some((path) => pathname === path || pathname.startsWith(path + '/'))) {
    if (!hasSupabaseSession(request)) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('next', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin', '/admin/:path*'],
};
