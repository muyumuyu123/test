# Panduan Jualan: Starlight Dreams Overlay Pack

Folder ini **bukan untuk pembeli**. Isinya tool dan catatan untuk kamu sebagai penjual.
Yang dikirim ke pembeli hanya folder `vtuber-overlay-pack/` (dalam bentuk zip).

## 1. Setup sekali saja

```bash
cd overlay-tools
npm install
npx playwright install chromium   # hanya perlu di komputer kamu sendiri
```

Untuk render video alert kamu juga butuh **ffmpeg** yang mendukung `libvpx-vp9`. Build resmi dari ffmpeg.org / gyan.dev (Windows) atau `brew install ffmpeg` (Mac) sudah mendukungnya.

## 2. Perintah

| Perintah | Hasil |
|---|---|
| `node previews.mjs` | Screenshot produk untuk listing → `previews/` |
| `node render.mjs` | 18 video alert WebM transparan → `vtuber-overlay-pack/alerts-video/` |
| `node render.mjs sub sakura` | Render satu video saja |
| `node build-se.mjs` | Rebuild widget StreamElements setelah kamu mengubah alert |

Kalau kamu mengubah `widgets/alerts.css` atau `alerts.js`, jalankan lagi `render.mjs` **dan** `build-se.mjs` supaya semua versi alert tetap sama.

## 3. Bungkus jadi zip

Sebelum di-zip, **kembalikan `config.js` ke contoh netral** (nama "Nova Moonpetal" dan handle contoh), supaya pembeli langsung paham apa yang harus diganti.

```bash
cd ..            # ke root repo
python3 -m zipfile -c starlight-dreams-v1.zip vtuber-overlay-pack/
```

## 4. Tempat jualan

| Platform | Catatan |
|---|---|
| **Etsy** | Pasar overlay terbesar. Cari "vtuber overlay". Ada biaya listing kecil per produk |
| **Ko-fi Shop** | Tanpa biaya bulanan, audiensnya kreator. Cocok kalau kamu juga aktif di sosmed |
| **Gumroad / Lemon Squeezy** | Simpel untuk produk digital, bisa pakai sistem "pay what you want" |
| **Booth.pm** | Pasar VTuber Jepang yang besar. Siapkan deskripsi bahasa Jepang |
| **Karyakarsa / Trakteer** | Untuk pasar lokal Indonesia |

Cek dulu aturan payout tiap platform untuk akun Indonesia (PayPal atau rekening bank) sebelum mulai.

## 5. Harga (patokan kasar, cek lagi di pasar)

Pack overlay animasi lengkap di Etsy umumnya dijual sekitar **$10–$35**. Strategi yang umum dipakai:

- **Harga peluncuran** lebih murah untuk mengumpulkan review pertama
- Jual **per tema ($12)** dan **bundle 3 tema ($25)**
- Tawarkan **custom** (ganti warna, tambah nama) sebagai upsell berbayar

## 6. Isi listing

1. **Video preview itu wajib.** Rekam `index.html` atau tiap scene dengan OBS (15–30 detik), karena bintang jatuh dan animasinya adalah nilai jual utama.
2. **Gambar pertama:** `previews/starting-soon-midnight.jpg`. Gambar kedua sampai kelima: frame, alert, chat, lalu perbandingan 3 tema.
3. **Kata kunci:** vtuber overlay, animated stream overlay, twitch overlay, starting soon screen, celestial, moon, stars, cozy, pastel, OBS.
4. **Tulis dengan jelas** apa yang didapat pembeli: OBS Browser Source, bisa diedit, 3 tema, alert WebM, dan widget StreamElements.
5. **Tulis juga batasannya:** chat widget hanya untuk Twitch, dan alert live membutuhkan StreamElements.

## 7. Ide pengembangan

- **Tema baru** hanya perlu menambah satu blok warna di `theme.css`, lalu render ulang. Satu kode bisa jadi banyak produk.
- **Aset gambar dari kamu** (ilustrasi chibi, maskot) bisa diselipkan ke scene sebagai `<img>`, jadi produknya lebih unik.
- Widget tambahan yang bisa dibuat berikutnya: jam atau "now playing" musik, subathon timer, dan panel profil Twitch.
- Scene **"Just Chatting"** (frame kamera besar tanpa area game).
