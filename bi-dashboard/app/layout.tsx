import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;

  return {
    title: "Commerce Pulse｜电商用户行为 BI",
    description: "浏览、收藏、加购、购买与商品流量的一体化业务洞察看板。",
    openGraph: {
      title: "Commerce Pulse｜用户行为分析 BI 看板",
      description: "流量、转化与商品洞察的一体化经营驾驶舱。",
      images: [`${origin}/og.png`],
    },
    twitter: {
      card: "summary_large_image",
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
