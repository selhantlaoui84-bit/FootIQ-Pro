import { createElement } from 'react';
import type { AppProps } from 'next/app';
import { AuthProvider } from '~/lib/auth';
import '~/styles/globals.css';

export default function App(props: AppProps) {
  const pageComponent = props.Component;

  return <AuthProvider>{createElement(pageComponent, props.pageProps)}</AuthProvider>;
}
