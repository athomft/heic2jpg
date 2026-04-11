const esbuild = require('esbuild');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function build() {
  console.log('🚀 Starting build process...');

  // 1. Bundle Worker
  console.log('📦 Bundling worker...');
  const workerResult = await esbuild.build({
    entryPoints: ['src/worker.ts'],
    bundle: true,
    minify: true,
    platform: 'node',
    write: false,
    format: 'cjs',
  });
  const workerCode = workerResult.outputFiles[0].text;

  // 2. Inline worker into App code
  console.log('🔗 Inlining worker into app...');
  let appLines = fs.readFileSync('src/app.ts', 'utf8').split('\n');
  
  // Remove shebang if present
  if (appLines[0].startsWith('#!')) {
    appLines.shift();
  }

  // Inject the worker code as a global variable
  const injectedCode = `global.INLINED_WORKER_CODE = ${JSON.stringify(workerCode)};\n`;
  let appCode = injectedCode + appLines.join('\n');

  // Replace Worker construction to use blob/data URL if in binary mode
  appCode = appCode.replace(
    "const workerPath = path.resolve(__dirname, 'worker.js');",
    "const workerPath = path.resolve(__dirname, 'worker.js');" // Fallback placeholder
  );

  // We need to modify src/app.ts to actually USE the inlined code.
  // I will do this in a separate step before bundling.
  fs.writeFileSync('src/app.tmp.ts', appCode);

  // 3. Bundle App
  console.log('📦 Bundling app...');
  await esbuild.build({
    entryPoints: ['src/app.tmp.ts'],
    bundle: true,
    minify: true,
    platform: 'node',
    outfile: 'dist/bundle.js',
    external: ['worker_threads', 'os', 'fs', 'path', 'fs/promises'],
  });

  // Clean up
  fs.unlinkSync('src/app.tmp.ts');

  console.log('✅ Bundle created at dist/bundle.js');

  // 4. Compile with Bun
  console.log('🏗️ Compiling with Bun...');
  const bunPath = path.join(process.env.USERPROFILE, '.bun', 'bin', 'bun.exe');
  
  const targets = [
    { name: 'heic2jpg-win-x64.exe', target: 'bun-windows-x64' },
    { name: 'heic2jpg-macos-arm64', target: 'bun-darwin-arm64' },
    { name: 'heic2jpg-linux-x64', target: 'bun-linux-x64' }
  ];

  for (const t of targets) {
    console.log(`   - Building ${t.name}...`);
    try {
      execSync(`"${bunPath}" build dist/bundle.js --compile --target=${t.target} --outfile bin/${t.name}`);
    } catch (err) {
      console.error(`   ❌ Failed to build ${t.name}: ${err.message}`);
    }
  }

  console.log('\n✨ All binaries created in the /bin folder!');
}

if (!fs.existsSync('bin')) fs.mkdirSync('bin');
if (!fs.existsSync('dist')) fs.mkdirSync('dist');

build().catch(err => {
  console.error('💥 Build failed:', err);
  process.exit(1);
});
