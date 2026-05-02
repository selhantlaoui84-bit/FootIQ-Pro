import { createElement } from 'react';
import type { AppProps } from 'next/app';
import '~/styles/globals.css';

export default function App(props: AppProps) {
  const pageComponent = props.Component;

  return createElement(pageComponent, props.pageProps);
}
