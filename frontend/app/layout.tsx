import type { Metadata } from "next";
import { Archivo_Black, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";

const displayFont = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-archivo-black",
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "Substrata | Supply chain workspace",
  description: "A synthetic supply-chain resilience prototype. Simulated actions only.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${monoFont.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
