#!/usr/bin/env node

import { program } from 'commander';
import * as cliProgress from 'cli-progress';
import * as fs from 'fs/promises';
import { existsSync, statSync, readdirSync, readFileSync } from 'fs';
import * as path from 'path';
import { Worker } from 'worker_threads';
import * as os from 'os';

import pc from 'picocolors';

interface ProgramOptions {
  output?: string;
  quality: number;
  recursive: boolean;
  delete: boolean;
  force: boolean;
  parallel: number;
  strip: boolean;
  keepDate: boolean;
}

const VERSION = '1.3.0';
const APP_NAME = 'heic2jpg';
const DESCRIPTION = 'Advanced CLI tool to convert .HEIC images to .JPG';

// Try to get the build timestamp from the build-info.json
function getBuildTimestamp(): string {
  try {
    const buildInfoPath = path.resolve(__dirname, 'build-info.json');
    if (existsSync(buildInfoPath)) {
      const data = JSON.parse(readFileSync(buildInfoPath, 'utf8'));
      return data.timestamp || 'unknown';
    }
  } catch (err) {
    // Fallback if the file isn't there (e.g., during dev)
  }
  return 'not built yet';
}

async function getHeicFilesRecursive(dir: string): Promise<string[]> {
  let files: string[] = [];
  const entries = readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files = files.concat(await getHeicFilesRecursive(fullPath));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.heic')) {
      files.push(fullPath);
    }
  }
  return files;
}

const BANNER = `
  _    _ ______ _____ _____ ___      _ _____   _____ 
 | |  | |  ____|_   _/ ____|__ \\    | |  __ \\ / ____|
 | |__| | |__    | || |       ) |   | | |__) | |  __ 
 |  __  |  __|   | || |      / /_   | |  ___/| | |_ |
 | |  | | |____ _| || |____ / /| |__| | |    | |__| |
 |_|  |_|______|____\\_____|____\\____/|_|     \\_____|
`;

async function convertHeic() {
  const isBinary = (process as any).isBun || (process as any).pkg || (process as any).sea;
  const runtimeStr = isBinary ? 'Standalone Binary' : `Node.js ${process.version}`;
  const versionString = `${pc.green(APP_NAME)} version ${VERSION} ${getBuildTimestamp()} (${runtimeStr})`;

  program
    .name(APP_NAME)

    .version(VERSION, '-v, --version')
    .usage('[options] [inputs...]')
    .helpOption('-h, --help', 'Display help for command')
    .configureHelp({
      showGlobalOptions: false,
      styleTitle: (str: string) => pc.yellow(str),
      styleUsage: (str: string) => pc.yellow(str),
      styleDescriptionText: (str: string) => str,
      styleOptionText: (str: string) => pc.green(str),
      styleArgumentText: (str: string) => pc.green(str),
      formatHelp: (cmd, helper) => {
        const usage = helper.commandUsage(cmd);
        const visibleArgs = helper.visibleArguments(cmd);
        const argTerms = visibleArgs.map(arg => helper.argumentTerm(arg));
        const visibleOpts = helper.visibleOptions(cmd);
        const optTerms = visibleOpts.map(opt => helper.optionTerm(opt));

        const maxTermLength = Math.max(...argTerms.map(t => t.length), ...optTerms.map(t => t.length), 0);
        const pad = 2;

        const args = visibleArgs.map((arg, i) => `  ${pc.green((argTerms[i] || '').padEnd(maxTermLength + pad))} ${pc.white(helper.argumentDescription(arg))}`).join('\n');
        const options = visibleOpts.map((opt, i) => `  ${pc.green((optTerms[i] || '').padEnd(maxTermLength + pad))} ${pc.white(helper.optionDescription(opt))}`).join('\n');

        return [
          BANNER,
          versionString,
          '',
          pc.white(DESCRIPTION),
          '',
          pc.yellow('Usage:'),
          `  ${pc.white(usage)}`,
          '',
          pc.yellow('Arguments:'),
          args,
          '',
          pc.yellow('Options:'),
          options,
          ''
        ].join('\n');
      }
    })
    .argument('[inputs...]', 'Path to the input .HEIC file(s) or directories')
    .option('-o, --output <path>', 'Path to the output .JPG file or output directory')
    .option('-q, --quality <number>', 'JPG quality (0 to 100)', (val) => parseInt(val, 10), 100)
    .option('-r, --recursive', 'Recursively search for .HEIC files in directories', false)
    .option('-d, --delete', 'Delete the original .HEIC file after successful conversion', false)
    .option('-f, --force', 'Force overwrite if output file already exists', false)
    .option('-p, --parallel <number>', 'Number of parallel threads to use', (val) => parseInt(val, 10), require('os').cpus().length)
    .option('--strip', 'Strip all metadata (EXIF) from the image', false)
    .option('--keep-date', 'Preserve original file modification date', false)
    .action(async (inputs: string[], options: ProgramOptions) => {
      if (!inputs || inputs.length === 0) {
        program.help();
        return;
      }

      let filesToProcess: string[] = [];
      for (const input of inputs) {
        const inputPath = path.resolve(input);
        if (!existsSync(inputPath)) {
          console.error(`Error: File or directory not found: ${inputPath}`);
          continue;
        }

        const stat = statSync(inputPath);
        if (stat.isDirectory()) {
          if (options.recursive) {
            filesToProcess = filesToProcess.concat(await getHeicFilesRecursive(inputPath));
          } else {
            const entries = readdirSync(inputPath, { withFileTypes: true });
            filesToProcess = filesToProcess.concat(
              entries
                .filter(e => e.isFile() && e.name.toLowerCase().endsWith('.heic'))
                .map(e => path.join(inputPath, e.name))
            );
          }
        } else if (stat.isFile() && inputPath.toLowerCase().endsWith('.heic')) {
          filesToProcess.push(inputPath);
        }
      }

      if (filesToProcess.length === 0) {
        console.log('No .HEIC files found to process.');
        return;
      }

      const outputBase = options.output ? path.resolve(options.output) : null;
      const isMultiFile = filesToProcess.length > 1;
      const treatAsDirectory = isMultiFile || (outputBase && (options.output?.endsWith('/') || options.output?.endsWith('\\') || (existsSync(outputBase) && statSync(outputBase).isDirectory())));

      if (treatAsDirectory && outputBase && !existsSync(outputBase)) {
        await fs.mkdir(outputBase, { recursive: true });
      }

      console.log(`Processing ${filesToProcess.length} file(s) using ${options.parallel} thread(s)...`);

      const progressBar = new cliProgress.SingleBar({
        format: 'Progress |{bar}| {percentage}% | {value}/{total} Files | {file}',
        barCompleteChar: '\u2588',
        barIncompleteChar: '\u2591',
        hideCursor: true
      }, cliProgress.Presets.shades_classic);

      progressBar.start(filesToProcess.length, 0, { file: '' });

      let activeWorkers = 0;
      let currentIndex = 0;

      // Logic to handle inlined worker for standalone binary
      const isStandalone = (process as any).isBun || (process as any).pkg || (process as any).sea;
      let workerSource: string | URL;

      if (typeof (global as any).INLINED_WORKER_CODE !== 'undefined') {
        // Use Data URL to load the worker from the bundled string
        workerSource = new URL(`data:text/javascript;base64,${Buffer.from((global as any).INLINED_WORKER_CODE).toString('base64')}`);
      } else {
        // Fallback to local file for development
        workerSource = path.resolve(__dirname, 'worker.js');
      }

      return new Promise<void>((resolve) => {
        const startWorker = () => {
          if (currentIndex >= filesToProcess.length || activeWorkers >= options.parallel) {
            if (activeWorkers === 0 && currentIndex >= filesToProcess.length) {
              progressBar.stop();
              console.log('\n--- Summary ---');
              console.log(`Converted: ${convertedCount}`);
              console.log(`Skipped:   ${skippedCount} (Use -f to overwrite)`);
              console.log(`Errors:    ${errorCount}`);
              resolve();
            }
            return;
          }

          const inputPath = filesToProcess[currentIndex++]!;
          const parsedInput = path.parse(inputPath);
          
          let outputPath: string;
          if (treatAsDirectory) {
            outputPath = outputBase ? path.join(outputBase, `${parsedInput.name}.jpg`) : path.join(parsedInput.dir, `${parsedInput.name}.jpg`);
          } else {
            outputPath = outputBase || path.join(parsedInput.dir, `${parsedInput.name}.jpg`);
          }

          if (existsSync(outputPath) && !options.force) {
            skippedCount++;
            progressBar.increment();
            startWorker();
            return;
          }

          activeWorkers++;
          const worker = new Worker(workerSource, { eval: workerSource instanceof URL ? false : false });
          
          worker.postMessage({
            inputPath,
            outputPath,
            quality: options.quality,
            strip: options.strip,
            keepDate: options.keepDate
          });

          worker.on('message', async (msg) => {
            if (msg.status === 'success') {
              convertedCount++;
              if (options.delete) await fs.unlink(inputPath);
            } else {
              errorCount++;
            }
            progressBar.increment(1, { file: parsedInput.base });
            activeWorkers--;
            worker.terminate();
            startWorker();
          });

          worker.on('error', (err) => {
            errorCount++;
            progressBar.increment(1, { file: parsedInput.base });
            activeWorkers--;
            worker.terminate();
            startWorker();
          });

          // Start more workers if possible
          startWorker();
        };

        startWorker();
      });
    });

  await program.parseAsync(process.argv);
}

convertHeic();
