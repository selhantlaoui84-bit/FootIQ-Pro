/** @type {import("next").NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://footiq-pro-production.up.railway.app";

    return [
      {
        source: "/admin/refresh-data",
        destination: `${apiUrl}/admin/refresh-data`,
      },
      {
        source: "/admin/refresh-status",
        destination: `${apiUrl}/admin/refresh-status`,
      },
    ];
  },
};

module.exports = nextConfig;
