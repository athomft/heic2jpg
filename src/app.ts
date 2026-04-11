#!/usr/bin/env node

import { program } from 'commander';
import convert from 'heic-convert';
import * as cliProgress from 'cli-progress';
import * as fs from 'fs/promises';
import { existsSync, statSync, readdirSync } from 'fs';
import * as path from 'path';

interface ProgramOptions {
  output?: string;
  quality: number;
  recursive: boolean;
  delete: boolean;
  force: boolean;
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

async function convertHeic() {
  program
    .name('heic2jpg')
    .description('Advanced CLI tool to convert .HEIC images to .JPG')
    .version('1.2.0', '-v, --version')
    .helpOption('-h, --help', 'Display help for command')
    .argument('<inputs...>', 'Path to the input .HEIC file(s) or directories')
    .option('-o, --output <path>', 'Path to the output .JPG file or output directory')
    .option('-q, --quality <number>', 'JPG quality (0 to 100)', (val) => parseInt(val, 10), 100)
    .option('-r, --recursive', 'Recursively search for .HEIC files in directories', false)
    .option('-d, --delete', 'Delete the original .HEIC file after successful conversion', false)
    .option('-f, --force', 'Force overwrite if output file already exists', false)
    .action(async (inputs: string[], options: ProgramOptions) => {
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
        } else {
          console.warn(`Warning: Skipping non-HEIC file or unsupported entry: ${inputPath}`);
        }
      }

      if (filesToProcess.length === 0) {
        console.log('No .HEIC files found to process.');
        return;
      }

      const isMultiFile = filesToProcess.length > 1;
      let outputBase = options.output ? path.resolve(options.output) : null;

      const treatAsDirectory = isMultiFile || (outputBase && options.output && (options.output.endsWith('/') || options.output.endsWith('\\') || (existsSync(outputBase) && statSync(outputBase).isDirectory())));

      if (treatAsDirectory && outputBase && !existsSync(outputBase)) {
        await fs.mkdir(outputBase, { recursive: true });
      }

      console.log(`Processing ${filesToProcess.length} file(s)...`);

      const progressBar = new cliProgress.SingleBar({
        format: 'Progress |{bar}| {percentage}% | {value}/{total} Files | {file}',
        barCompleteChar: '\u2588',
        barIncompleteChar: '\u2591',
        hideCursor: true
      }, cliProgress.Presets.shades_classic);

      progressBar.start(filesToProcess.length, 0, { file: '' });

      let convertedCount = 0;
      let skippedCount = 0;
      let errorCount = 0;

      for (const inputPath of filesToProcess) {
        const parsedInput = path.parse(inputPath);
        progressBar.update(convertedCount + skippedCount + errorCount, { file: parsedInput.base });

        try {
          let outputPath: string;

          if (treatAsDirectory) {
            const fileName = `${parsedInput.name}.jpg`;
            outputPath = outputBase ? path.join(outputBase, fileName) : path.join(parsedInput.dir, fileName);
          } else if (outputBase) {
            outputPath = outputBase;
          } else {
            outputPath = path.join(parsedInput.dir, `${parsedInput.name}.jpg`);
          }

          if (existsSync(outputPath) && !options.force) {
            skippedCount++;
            continue;
          }

          const inputBuffer = await fs.readFile(inputPath);
          const outputBuffer = await convert({
            buffer: inputBuffer,
            format: 'JPEG',
            quality: options.quality / 100,
          });

          await fs.writeFile(outputPath, outputBuffer);

          if (options.delete) {
            await fs.unlink(inputPath);
          }

          convertedCount++;
        } catch (error) {
          errorCount++;
        }
      }

      progressBar.update(filesToProcess.length, { file: 'Complete' });
      progressBar.stop();

      console.log('\n--- Summary ---');
      console.log(`Converted: ${convertedCount}`);
      console.log(`Skipped:   ${skippedCount} (Use -f to overwrite)`);
      console.log(`Errors:    ${errorCount}`);
      if (options.delete) {
        console.log(`Originals deleted: ${convertedCount}`);
      }
    });

  await program.parseAsync(process.argv);
}

convertHeic();
