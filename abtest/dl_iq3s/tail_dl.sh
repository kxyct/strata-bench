#!/bin/bash
# 单连接在早高峰太慢，最后一段切 6 路并行。完成后写 DONE，点火 cron 接手。
D=/e/Desktop/aigz/strata-bench/abtest/dl_iq3s
LOG=/c/Users/kxy/AppData/Local/Temp/dl_iq3s.log
URL="https://hf-mirror.com/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF/resolve/main/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf"
NAME="Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf"
PART="$D/$NAME.part"
SIZES=55063448064
N=6
echo "$(date '+%m-%d %H:%M') === tail6 start ===" >> "$LOG"
while :; do
  SZ=$(stat -c %s "$PART")
  [ "$SZ" -ge "$SIZES" ] && break
  PER=$(( (SIZES - SZ + N - 1) / N ))
  declare -a LEN
  for ((i=0;i<N;i++)); do
    OFF=$((SZ + i * PER)); L=$((SIZES - OFF)); (( L > PER )) && L=$PER
    LEN[$i]=$L
    (( L <= 0 )) && continue
    curl -fsL --retry 3 --retry-delay 5 --speed-time 90 --speed-limit 10000 \
      -r ${OFF}-$((OFF + L - 1)) -o "$D/tail_$i.bin" "$URL" >> "$LOG" 2>&1 &
  done
  wait
  for ((i=0;i<N;i++)); do
    (( LEN[i] <= 0 )) && continue
    CS=$(stat -c %s "$D/tail_$i.bin" 2>/dev/null || echo 0)
    if [ "$CS" -eq "${LEN[i]}" ]; then
      cat "$D/tail_$i.bin" >> "$PART" && rm -f "$D/tail_$i.bin"
    else
      rm -f "$D"/tail_*.bin
      break
    fi
  done
done
rm -f "$D"/tail_*.bin
SZ=$(stat -c %s "$PART")
echo "$(date '+%m-%d %H:%M') final size=$SZ" >> "$LOG"
if [ "$SZ" -eq "$SIZES" ]; then
  mv -f "$PART" "$D/$NAME"
  echo "40f369eca301ec6ea318dbb671b3132c26a2f0b89aa5458a7051b33215ee296c  $NAME" > "$D/IQ3S.sha"
  if (cd "$D" && sha256sum -c IQ3S.sha) >> "$LOG" 2>&1; then echo DONE >> "$LOG"; else echo SHA-FAIL >> "$LOG"; fi
else
  echo "$(date '+%m-%d %H:%M') 长度不对 $SZ != $SIZES" >> "$LOG"
fi
