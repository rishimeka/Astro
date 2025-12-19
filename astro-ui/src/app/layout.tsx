import type { Metadata } from "next";
import "./globals.scss";
import { Outfit, Libre_Baskerville, JetBrains_Mono } from "next/font/google";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const libreBaskervilllle = Libre_Baskerville({
  weight: ["400", "700"],
  variable: "--font-baskervville",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});


export const metadata: Metadata = {
  title: "Astrix Labs",
  description:
    "Astrix Labs builds infrastructure for reliable, composable AI systems. We help teams design, orchestrate, and operate intelligent agents with deterministic workflows, structured context, and production-grade control.",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`m-0 ${outfit.className} ${libreBaskervilllle.className} ${jetBrainsMono.className}`}>
        {children}
      </body>
    </html>
  );
}
