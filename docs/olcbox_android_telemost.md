# Olcbox Android + Telemost

Схема: **[OLC_TELEMOST.md](OLC_TELEMOST.md)**.

Токен VP8 = FNV от **полной** ссылки комнаты (universal-carrier).

## Параметры srv (пример)

| Параметр | Значение |
|----------|----------|
| room | `https://telemost.yandex.ru/j/YOUR_MEETING_ID` |
| key | hex из панели (Copy URI / users.json) |
| transport | `vp8channel` |
| vp8-fps / batch | **60** / **64** |

## Patched APK

1. Соберите на Linux: `scripts/build_olcbox_android_patched_server.sh` (артефакт в `backend/data/`).
2. Опубликуйте **`.apk`** и **`.sha256`** в **GitHub Releases** вашего репозитория.
3. На телефоне скачайте APK с GitHub (не с VPS OlcPanel).

Перед установкой удалите старый Olcbox (другая подпись).

## Tunnel VPN (не Proxy)

**Settings → Connection mode → Tunnel / VPN**, не SOCKS-only.

## Room ID на Android

В поле **Room / ID** — **только цифры** ID встречи (без `https://...`).

## URI с панели

```
olcrtc://telemost?vp8channel<vp8-fps=60&vp8-batch=64>@YOUR_MEETING_ID#<key>
```

## Порядок запуска

1. Создать встречу Telemost → скопировать ссылку → **выйти из браузера**.
2. Вставить URL в OlcPanel → **Stop → Start** srv.
3. Дождаться `Link connected` в логах srv (10–20 с).
4. На телефоне **Start** в Olcbox (без других VPN).
5. `KCP started` → `peer first seen` → `session opened` → Relay Active.

## Типичные ошибки

| Симптом | Действие |
|---------|----------|
| `frame token mismatch` | Выйти из Telemost в браузере; проверить room |
| `handshake EOF` | patched olcrtc; Stop→Start srv, затем клиент |
| `got` ≠ `want` | Переимпорт URI с панели |
| Нет трафика | Режим Tunnel VPN, не Proxy |

## Сборка patched lib

`scripts/build_olcrtc_android_server.sh` — `olcrtc-android-arm64` в `backend/data/`.

## Ссылки

- [olcrtc URI format](https://github.com/openlibrecommunity/olcrtc/blob/master/docs/uri.md)
- [olcbox #56](https://github.com/alananisimov/olcbox/issues/56)
