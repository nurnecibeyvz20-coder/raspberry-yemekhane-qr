# Yemekhane Saat Kısıtlaması — Tasarım Dokümanı

Tarih: 2026-07-30
Durum: Onaylandı

## Amaç

Check-in yalnız belirlenen servis saatleri içinde kabul edilir. Varsayılan
12:00–13:30; admin panelindeki Ayarlar sayfasından değiştirilebilir.

## Kararlar

| Konu | Karar |
|---|---|
| Varsayılan aralık | 12:00 – 13:30 (kapsayıcı: tam 12:00 ve tam 13:30 kabul) |
| Saklama | settings tablosu: `saat_baslangic`="12:00", `saat_bitis`="13:30" |
| Kontrol sırası | imza → süre → kullanıcı → **saat** → mükerrer → bakiye (kapalıyken hak/bakiye etkilenmez) |
| Yeni durum | `saat_disi`; failed_attempts'a yazılır |
| Kiosk sonuç | Kırmızı "Yemekhane şu an kapalı" + "Servis saatleri: 12:00 – 13:30" |
| Anons | "Yemekhane şu an kapalı. Servis saatleri {okunuş} arasıdır." |
| Kiosk bekleme | Aralık dışında yönerge "Yemekhane kapalı — Servis: 12:00-13:30" olur (dakikalık kontrol) |
| Personel sayfası | Değişmez (YAGNI) |
| Zaman kaynağı | Konteyner yerel saati (TZ=Europe/Istanbul zaten ayarlı) |

## Ayarlar Sayfası

Mevcut Ayarlar formuna "Yemekhane Saatleri" bölümü: iki `<input
type="time">` (başlangıç/bitiş). Doğrulama: ikisi de HH:MM biçiminde
parse edilebilmeli ve bitiş > başlangıç; aksi halde "Geçersiz saat
aralığı" hatası, kayıt yapılmaz. Başarıda flash "Ayarlar güncellendi".

## Check-in Değişikliği

`app/services/checkin.py`:
- `get_service_hours(db) -> tuple[time, time]` — settings'ten okur, yoksa
  varsayılanları yazar ve döner (get_meal_price kalıbı).
- `process_checkin` user-aktif kontrolünden sonra: `now = datetime.now().time()`;
  `if not (baslangic <= now <= bitis): return _fail(..., "saat_disi", user)`
- MESSAGES'a: `"saat_disi": "Yemekhane şu an kapalı"`
- CheckinResult'a ek alan gerekmez; kiosk yanıtına servis saatleri eklenir
  (alt satır için): `/api/checkin` yanıtında `saatler: "12:00 - 13:30"`
  (yalnız saat_disi durumunda dolu, diğerlerinde null).

## Anons

`app/tts.py`:
- `saat_okunusu(t: time) -> str` — "12:00"→"on iki", "13:30"→"on üç
  otuz", "09:15"→"dokuz on beş". Saat kısmı Türkçe sayı okunuşu
  (0-23), dakika 0 ise atlanır, değilse sayı okunuşuyla eklenir.
  Sayı okunuşu 0-59 için yeterli (birler+onlar tablosu).
- `anons_metni`: `saat_disi` → "Yemekhane şu an kapalı. Servis saatleri
  {baslangic_okunus}, {bitis_okunus} arasıdır." — saat bilgisi
  CheckinResult'ta olmadığından anons metni kiosk_routes'ta saatlerle
  üretilir: `anons_metni(result, saatler=(bas, bit))` opsiyonel parametre.

## Kiosk Bekleme Ekranı

- Yeni hafif endpoint: `GET /api/kiosk-durum` (localhost_only) →
  `{"acik": bool, "saatler": "12:00 - 13:30"}`
- kiosk.html JS: açılışta + 60 sn'de bir çağırır; kapalıysa yönerge
  metni "Yemekhane kapalı — Servis: 12:00-13:30", açıksa "QR kodunuzu
  okutun". Hata olursa yönergeye dokunmaz (fail-open görsel).

## Testler

- get_service_hours varsayılan üretimi + settings'ten okuma
- Aralık içi kabul; aralık dışı `saat_disi` + bakiye değişmedi +
  meal_entry yok + failed_attempt yazıldı (zaman freezegun yerine
  monkeypatch ile `checkin.datetime` sabitlenir)
- Sınırlar: tam 12:00 kabul, tam 13:30 kabul, 13:31 red
- saat_okunusu: "12:00"→"on iki", "13:30"→"on üç otuz", "09:15"→"dokuz
  on beş"
- Ayar formu: geçerli kayıt, bitiş≤başlangıç red
- /api/kiosk-durum: localhost-only, açık/kapalı doğru

## Kapsam Dışı

- Öğün bazlı çoklu aralık (kahvaltı/akşam)
- Gün bazlı farklı saatler (hafta sonu vb.)
- Personel sayfasında saat gösterimi
