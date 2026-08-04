import { defineConfig } from "vite";

// GitHub Pages のサブパスに置く。日本版ビューアが root を占めるため /semarang/ 配下。
export default defineConfig({
  base: "/food-store-master/semarang/",
  define: {
    __BUILD_TIME__: JSON.stringify(
      new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC",
    ),
  },
});
