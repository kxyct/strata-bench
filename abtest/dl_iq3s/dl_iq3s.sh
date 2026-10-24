#!/bin/bash
DIR=/e/Desktop/aigz/strata-bench/abtest/dl_iq3s
LOG=/c/Users/kxy/AppData/Local/Temp/dl_iq3s.log
URL="https://hf-mirror.com/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF/resolve/main/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf"
NAME="Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf"
PART="$DIR/$NAME.part"
FIN="$DIR/$NAME"
SIZES=55063448064
echo "$(date '+%m-%d %H:%M') === start ===" >> "$LOG"
while :; do
  curl -sL -C - --retry 5 --retry-delay 5 --speed-time 60 --speed-limit 20000 -o "$PART" "$URL" >> "$LOG" 2>&1 || true
  SZ=$(stat -c %s "$PART" 2>/dev/null || echo 0)
  PCT=$(python -c "print('%.1f%%' % ($SZ/$SIZES*100))")
  echo "$(date '+%m-%d %H:%M') size=$SZ ($PCT)" >> "$LOG"
  [ "$SZ" -ge "$SIZES" ] && break
  sleep 10
done
mv "$PART" "$FIN" 2>/dev/null || true
echo "40f369eca301ec6ea318dbb671b3132c26a2f0b89aa5458a7051b33215ee296c  $NAME" > "$DIR/IQ3S.sha"
if (cd "$DIR" && sha256sum -c IQ3S.sha) >> "$LOG" 2>&1; then echo DONE >> "$LOG"; else echo SHA-FAIL >> "$LOG"; fi
