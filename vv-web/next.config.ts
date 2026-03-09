import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.metmuseum.org" },
      { protocol: "https", hostname: "ids.si.edu" },
      { protocol: "https", hostname: "*.etsy.com" },
      { protocol: "https", hostname: "i.etsystatic.com" },
      { protocol: "https", hostname: "tusswxlrdoamintvswjs.supabase.co" },
    ]
  }
};

export default nextConfig;