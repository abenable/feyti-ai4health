import type { Metadata } from "next";
import { Playfair_Display, Manrope } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Feyti",
  description: "Feyti reads, classifies, and files regulatory documents into CTD dossiers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body className={`${playfair.variable} ${manrope.variable} font-sans antialiased bg-[#fdfbf7] text-[#1c1917]`}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
