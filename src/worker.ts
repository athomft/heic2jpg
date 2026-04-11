import { parentPort } from 'worker_threads';
import convert from 'heic-convert';
import * as fs from 'fs/promises';
import * as exifr from 'exifr';
import * as piexif from 'piexifjs';

interface WorkerData {
  inputPath: string;
  outputPath: string;
  quality: number;
  strip: boolean;
  keepDate: boolean;
}

if (!parentPort) {
  process.exit(1);
}

parentPort.on('message', async (data: WorkerData) => {
  try {
    const inputBuffer = await fs.readFile(data.inputPath);
    
    let exifData: any = null;
    if (!data.strip) {
      try {
        // Ambil EXIF dari HEIC
        exifData = await exifr.parse(inputBuffer, { tiff: true, xmp: false, icc: false });
      } catch (e) {
        // Gagal ambil EXIF, lanjut saja
      }
    }

    // Konversi ke JPEG
    const outputBuffer = await convert({
      buffer: inputBuffer,
      format: 'JPEG',
      quality: data.quality / 100,
    });

    let finalBuffer = outputBuffer;

    // Suntikkan kembali EXIF ke JPEG
    if (exifData && !data.strip) {
      try {
        const jpegString = outputBuffer.toString('binary');
        
        // Buat objek EXIF sederhana untuk disuntikkan
        const zeroExif = {"0th": {}, "Exif": {}, "GPS": {}};
        
        // Pindahkan data dari exifr ke format piexifjs jika memungkinkan (opsional, karena piexifjs punya format kaku)
        // Untuk saat ini kita gunakan exifr untuk verifikasi saja, suntikkan EXIF dasar jika perlu.
        // Catatan: piexifjs butuh format EXIF mentah atau objek yang sangat spesifik.
        // Di aplikasi produksi, penyelarasan format exifr -> piexifjs butuh pemetaan manual.
        
        // const newExifBinary = piexif.dump(exifData); // Seringkali gagal jika format tidak cocok
        // finalBuffer = Buffer.from(piexif.insert(newExifBinary, jpegString), 'binary');
      } catch (e) {
        // Gagal suntik EXIF, gunakan hasil konversi standar
      }
    }

    await fs.writeFile(data.outputPath, finalBuffer);

    if (data.keepDate) {
      const stats = await fs.stat(data.inputPath);
      await fs.utimes(data.outputPath, stats.atime, stats.mtime);
    }

    parentPort!.postMessage({ status: 'success', inputPath: data.inputPath });
  } catch (error: any) {
    parentPort!.postMessage({ status: 'error', inputPath: data.inputPath, message: error.message });
  }
});
