# BAKAI Robot Audio & Xiaozhi Firmware Integration Guide

This guide explains how to enable hardware audio playback on your AI robot **BAKAI** (running on ESP32 / Xiaozhi firmware) so it can stream live Indian radio stations, music audio, and voice responses through its physical speaker.

---

## 1. Hardware Pinouts (ESP32-S3 & MAX98357A I2S DAC)

For high-quality audio output without analog noise, an I2S digital-to-analog amplifier module (e.g., **MAX98357A**) or audio codec board (**ES8388**) is recommended.

### Recommended Wiring for ESP32-S3:

| MAX98357A Pin | ESP32-S3 Pin | Function |
| :--- | :--- | :--- |
| **VIN** | 5V (or VBUS) | Power supply (up to 3.2W into 4Ω speaker) |
| **GND** | GND | Ground |
| **BCLK** | GPIO 15 | Bit Clock (BCK) |
| **LRC** | GPIO 16 | Word Select / Left-Right Clock (WS) |
| **DIN** | GPIO 7 | Serial Audio Data (DOUT) |
| **SD / EN** | NC (or 3.3V) | Shutdown / Left-Right channel select |
| **GAIN** | GND (9dB) or 3.3V (15dB) | Amplifier Gain setting |

---

## 2. Xiaozhi MCP Action Protocol

When BAKAI calls any radio or music tool (e.g., `radio_play`, `radio_stop`, `music_control`), the MCP server returns both human-friendly text for voice synthesis and a structured **`robot_action`** payload:

### Play Radio Action:
```json
{
  "action": "play_audio",
  "url": "http://192.99.8.192:5032/;stream",
  "format": "mp3",
  "title": "Fnf.Fm Hindi",
  "type": "live_stream"
}
```

### Stop Audio Action:
```json
{
  "action": "stop_audio"
}
```

### Volume Control Action:
```json
{
  "action": "player_volume_up",
  "volume": 80
}
```

---

## 3. Firmware Implementation (ESP-IDF / Xiaozhi Firmware)

In standard Xiaozhi firmware, inbound WebSocket messages are processed in `main/protocol.cc` or `main/application.cc`.

### Step 1: Intercept MCP `robot_action` in WebSocket Event Handler

Add this block in your message dispatcher where JSON messages are received:

```c
#include "cJSON.h"
#include "audio_player.h"

void handle_server_action(const char* json_str) {
    cJSON* root = cJSON_Parse(json_str);
    if (!root) return;

    // Check if robot_action payload exists
    cJSON* robot_action = cJSON_GetObjectItem(root, "robot_action");
    if (!robot_action) {
        cJSON_Delete(root);
        return;
    }

    cJSON* action = cJSON_GetObjectItem(robot_action, "action");
    if (action && cJSON_IsString(action)) {
        if (strcmp(action->valuestring, "play_audio") == 0) {
            cJSON* url = cJSON_GetObjectItem(robot_action, "url");
            if (url && cJSON_IsString(url)) {
                ESP_LOGI("BAKAI_AUDIO", "Starting radio stream: %s", url->valuestring);
                // Pause assistant speech/TTS and switch to streaming radio player
                audio_player_stop();
                audio_player_play_stream(url->valuestring);
            }
        } 
        else if (strcmp(action->valuestring, "stop_audio") == 0) {
            ESP_LOGI("BAKAI_AUDIO", "Stopping audio stream");
            audio_player_stop();
        }
        else if (strcmp(action->valuestring, "player_volume_up") == 0 ||
                 strcmp(action->valuestring, "player_volume_down") == 0) {
            cJSON* vol = cJSON_GetObjectItem(robot_action, "volume");
            if (vol && cJSON_IsNumber(vol)) {
                audio_player_set_volume((int)vol->valuedouble);
            }
        }
    }

    cJSON_Delete(root);
}
```

---

## 4. ESP-ADF Audio Streaming Pipeline

Using the official Espressif Audio Development Framework (**ESP-ADF**), stream playback is handled by connecting an HTTP reader to an MP3 or AAC decoder and feeding the I2S writer:

```c
#include "audio_pipeline.h"
#include "http_stream.h"
#include "mp3_decoder.h"
#include "i2s_stream.h"

static audio_pipeline_handle_t pipeline;
static audio_element_handle_t http_stream_reader, mp3_decoder, i2s_stream_writer;

void audio_player_init(void) {
    audio_pipeline_cfg_t pipeline_cfg = DEFAULT_AUDIO_PIPELINE_CONFIG();
    pipeline = audio_pipeline_init(&pipeline_cfg);

    http_stream_cfg_t http_cfg = HTTP_STREAM_CFG_DEFAULT();
    http_stream_reader = http_stream_init(&http_cfg);

    mp3_decoder_cfg_t mp3_cfg = DEFAULT_MP3_DECODER_CONFIG();
    mp3_decoder = mp3_decoder_init(&mp3_cfg);

    i2s_stream_cfg_t i2s_cfg = I2S_STREAM_CFG_DEFAULT();
    i2s_cfg.type = AUDIO_STREAM_WRITER;
    i2s_stream_writer = i2s_stream_init(&i2s_cfg);

    audio_pipeline_register(pipeline, http_stream_reader, "http");
    audio_pipeline_register(pipeline, mp3_decoder, "mp3");
    audio_pipeline_register(pipeline, i2s_stream_writer, "i2s");

    const char *link_tag[3] = {"http", "mp3", "i2s"};
    audio_pipeline_link(pipeline, &link_tag[0], 3);
}

void audio_player_play_stream(const char *url) {
    audio_pipeline_stop(pipeline);
    audio_pipeline_wait_for_stop(pipeline);
    audio_pipeline_reset_ringbuffer(pipeline);
    audio_pipeline_reset_elements(pipeline);

    audio_element_set_uri(http_stream_reader, url);
    audio_pipeline_run(pipeline);
}

void audio_player_stop(void) {
    if (pipeline) {
        audio_pipeline_stop(pipeline);
        audio_pipeline_wait_for_stop(pipeline);
    }
}
```

---

## 5. Audio Buffer Recommendations for India Networks

- Allocate **64 KB RingBuffer** for the `http_stream_reader` element:
  ```c
  http_cfg.request_size = 1024 * 64;
  ```
- This prevents audio dropouts or stuttering caused by brief 1-2 second Wi-Fi latency spikes.
- For HLS (`.m3u8`) Akashvani streams, ensure `esp-adf` has HLS stream reader enabled (`CONFIG_AUDIO_SUPPORT_HLS=y` in `menuconfig`).
- If your hardware uses simple MP3/AAC decoders, BAKAI server automatically provides MP3 fallback URLs (e.g. Zeno FM / Shoutcast streams) for every station!
