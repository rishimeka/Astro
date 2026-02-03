import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  external: ['react', 'react-dom'],
  esbuildOptions(options) {
    options.jsx = 'automatic';
  },
  // Treat SCSS modules as external - let the consuming app handle them
  noExternal: [],
  onSuccess: async () => {
    // Copy all source files to dist for the consuming app to process
    const { execSync } = await import('child_process');
    execSync('mkdir -p dist/styles && cp -r src/styles/* dist/styles/', { stdio: 'inherit' });
    // Copy component SCSS modules to dist/components
    execSync('mkdir -p dist/components', { stdio: 'inherit' });
    execSync('find src/components -name "*.scss" -exec cp {} dist/components/ \\;', { stdio: 'inherit' });
  },
});
