import type { Metadata } from "next";
import { Libre_Baskerville, Outfit, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import AppLayout from "@/components/Layout/AppLayout";
import { ThemeProvider } from "@/context/ThemeContext";

const libreBaskerville = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-display",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Astro",
  description: "Intelligence meets architecture",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body
        className={`${libreBaskerville.variable} ${outfit.variable} ${jetbrainsMono.variable}`}
      >
        <ThemeProvider>
          <AppLayout>{children}</AppLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
