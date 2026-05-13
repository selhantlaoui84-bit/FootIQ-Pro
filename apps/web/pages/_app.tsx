import { createElement } from 'react';
import type { AppProps } from 'next/app';
import { OnboardingModal } from '~/components/OnboardingModal';
import { AuthProvider } from '~/lib/auth';
import '~/styles/globals.css';

export default function App(props: AppProps) {
  const pageComponent = props.Component;

  return (
    <AuthProvider>
      {createElement(pageComponent, props.pageProps)}
      <OnboardingModal />
    </AuthProvider>
  );
}
