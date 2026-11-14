# 🔥 Labirentten Kaçış: Ateş Fırtınası (Flame Maze Escape)

Python ile geliştirilmiş, prosedürel labirent üretimi, dinamik alev tuzakları, seken ateş topları ve kilit-anahtar mekaniklerine sahip aksiyon dolu bir 2D labirentten kaçış oyunu.

---

## 🎮 Özellikler

* **Algoritmik Labirent Üretimi:** *Recursive Backtracker* algoritması kullanılarak her seviyede sıfırdan oluşturulan çözülebilir ve alternatif rotalı labirentler.
* **Gelişen Seviyeler:** Seviye ilerledikçe labirent büyür, koridorlar karmaşıklaşır ve tehlikeler artar.
* **🔥 Alev Tuzakları (Fire Pits):** Zeminde uyarı verip ardından şiddetle alev püskürten tehlikeli tuzaklar.
* **☄️ Uçan Ateş Topları (Fireballs):** Koridorlarda süzülen, duvarlardan seken ve arkasında alev izleri bırakan ateş topları.
* **🔑 Kilitli Kapılar & Altın Anahtar:** Çıkış portalına ulaşmak için labirentteki gizli anahtarı bulun.
* **💎 Puan Sistemi & Canlar:** 3 can hakkı, toplanabilir altınlar, hız bonusu ve seviye çarpanları.
* **Hızlı & Akıcı Kontroller:** 60 FPS, kaygan köşe çarpışma fiziği ve yüksek hareket duyarlılığı.

---

## 🕹️ Nasıl Oynanır?

### Kontroller
| Tuş | İşlev |
| :--- | :--- |
| `W`, `A`, `S`, `D` veya `Yön Tuşları` | Karakteri hareket ettir |
| `BOŞLUK (Space)` veya `ENTER` | Oyunu başlat / Sonraki seviyeye geç |
| `ESC` | Oyundan çık |

---

## 🚀 Çalıştırma

### Seçenek 1: Tkinter Versiyonu (Sıfır Kurulum)
Hiçbir harici paket yüklemeden doğrudan standart Python ile çalıştırın:
```bash
python maze_escape_tk.py
```

### Seçenek 2: Pygame Versiyonu
Pygame kütüphanesi ile neon ışıklandırmalı versiyon:
```bash
pip install pygame
python maze_escape.py
```

---

## 📁 Proje Yapısı

```
.
├── .agents/                    # Antigravity agent yetenek yapılandırması
│   └── skills/python-game-dev/ # Python oyun geliştirme skill ve şablonları
├── maze_escape_tk.py           # Tkinter tabanlı alev labirent oyunu
├── maze_escape.py              # Pygame tabanlı gelişmiş versiyon
├── .gitignore                  # Git dışlama kuralları
└── README.md                   # Proje dokümantasyonu
```
