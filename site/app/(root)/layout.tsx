/** The bare root: only sends readers to the default language. */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr-MA">
      <body>{children}</body>
    </html>
  );
}
