# Kiosk Logo ve Gorsel Tasarim

## Amac

Kiosk ekraninda Raspberry Pi masaustundeki `imagebelediye.png` logosunu yatay
oranini koruyarak kullanmak ve bekleme ekranini daha belirgin, profesyonel bir
gorunume tasimak.

## Varlik

- Pi'deki `~/Desktop/imagebelediye.png`, proje icinde
  `app/static/imagebelediye.png` konumuna kopyalanir.
- Logo CSS ile yatay gorunur; `object-fit: contain` ile dosyanin orijinal
  orani korunur.

## Kiosk Bekleme Ekrani

- Duz yesil zemin, Karatay yesil tonlarini kullanan cok katmanli gradyanla
  degistirilir.
- Arka planda dusuk opaklikli daire ve cizgi desenleri yalniz CSS ile
  olusturulur; harici ikon paketi veya ag bagimliligi eklenmez.
- Logo beyaz daire olmadan yatay kapsayici icinde gorunur.
- Baslik, saat ve QR yonergesi okunurlugu korunur; kiosk tam ekran ve QR
  okuyucu davranisi degismez.

## Sonuc Ekranlari

- Basari, uyari ve hata renkleri korunur.
- Sonuc ekranlari arka plan dokusuyla bekleme ekraniyla ayni gorsel dili
  kullanir.

## Dogrulama

- Kiosk route testi 200 donmeye devam eder.
- Sablon yeni logo yolunu ve kiosk gorsel siniflarini icerir.
- Tum test paketi calisir.
