#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python tests/full_system_test/01_ping.py
python tests/full_system_test/02_description.py
python tests/full_system_test/03_audio_synthesis_and_transcription.py
python tests/full_system_test/04_sql_http.py
python tests/full_system_test/05_chat_from_audio.py
python tests/full_system_test/06_ui_from_audio.py
python tests/full_system_test/07_ws_text_json.py
python tests/full_system_test/08_ws_text_audio.py
python tests/full_system_test/09_ws_audio_json.py
python tests/full_system_test/10_ws_audio_audio.py
python tests/full_system_test/11_ws_audio_both.py

echo "full_system_test ok"
