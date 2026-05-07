import { NextResponse } from 'next/server';

/**
 * Supabase Auth persiste la session côté navigateur. Sans intégration SSR complète
 * avec @supabase/ssr, un middleware serveur ne peut pas lire l'état localStorage
 * et peut renvoyer à tort un utilisateur déjà connecté vers /login.
 *
 * La protection effective des pages privées reste donc dans ProtectedRoute, qui
 * attend la fin du chargement Supabase avant toute redirection.
 */
export function middleware() {
  return NextResponse.next();
}
